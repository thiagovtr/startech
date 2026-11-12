import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from hemocentros.config import get_settings
from hemocentros.db.postgres import create_session_factory
from hemocentros.main import app
from hemocentros.models.orm import CampanhaModel, OutboxEvent
from tests.conftest import TEST_PG_URL

VALIDO = {
    "titulo": "Doação Urgente O-", "hemocentro": "Hemocentro Lavras", "tipo_sanguineo": "O-",
    "urgencia": "CRITICO", "data_inicio": "2026-11-10", "data_fim": "2026-11-30",
}


@pytest.fixture
def client(pg_engine, monkeypatch):
    monkeypatch.setenv("HEMOCENTROS_POSTGRES_URL", TEST_PG_URL)
    monkeypatch.setenv("HEMOCENTROS_MONGO_URL", "mongodb://127.0.0.1:1")
    get_settings.cache_clear()
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


def _contagens(engine):
    factory = create_session_factory(engine)

    async def go():
        async with factory() as s:
            return (await s.scalars(select(CampanhaModel))).all(), (await s.scalars(select(OutboxEvent))).all()

    return asyncio.run(go())


def test_cria_campanha_e_evento_outbox(client, pg_engine):
    r = client.post("/api/v1/campanhas", json=VALIDO)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "ATIVA" and body["urgencia"] == "CRITICO" and body["id"]

    camps, evs = _contagens(pg_engine)
    assert len(camps) == 1 and len(evs) == 1
    ev = evs[0]
    assert ev.routing_key == "hemocentros.campanha.criada"
    assert ev.aggregate_type == "Campanha" and ev.aggregate_id == body["id"]
    assert ev.published is False
    assert ev.payload["tipo_sanguineo"] == "O-" and ev.payload["id"] == body["id"]


@pytest.mark.parametrize(
    "mudanca",
    [
        {"tipo_sanguineo": "X+"},
        {"titulo": ""},
        {"data_fim": "2026-11-01"},  # anterior ao início
        {"data_inicio": "nao-e-data"},
    ],
)
def test_payload_invalido_retorna_400_problem_json(client, pg_engine, mudanca):
    r = client.post("/api/v1/campanhas", json={**VALIDO, **mudanca})
    assert r.status_code == 400
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["type"] == "urn:startech:error:payload-invalido" and body["status"] == 400
    assert body["invalidParams"]
    assert _contagens(pg_engine) == ([], [])  # nada gravado


def test_campo_ausente_retorna_400(client):
    r = client.post("/api/v1/campanhas", json={"titulo": "Só título"})
    assert r.status_code == 400
    nomes = {p["name"] for p in r.json()["invalidParams"]}
    assert {"hemocentro", "tipo_sanguineo", "data_inicio", "data_fim"} <= nomes


def test_banco_indisponivel_retorna_503(monkeypatch):
    monkeypatch.setenv("HEMOCENTROS_POSTGRES_URL", "postgresql+asyncpg://u:p@127.0.0.1:1/x")
    monkeypatch.setenv("HEMOCENTROS_MONGO_URL", "mongodb://127.0.0.1:1")
    monkeypatch.setenv("HEMOCENTROS_DB_CHECK_TIMEOUT", "0.5")
    get_settings.cache_clear()
    try:
        with TestClient(app) as c:
            r = c.post("/api/v1/campanhas", json=VALIDO)
    finally:
        get_settings.cache_clear()
    assert r.status_code == 503
    assert r.json()["type"] == "urn:startech:error:banco-indisponivel"
