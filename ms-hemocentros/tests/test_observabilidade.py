import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select

from hemocentros.config import get_settings
from hemocentros.db.postgres import create_session_factory
from hemocentros.main import app
from hemocentros.models.orm import OutboxEvent
from hemocentros.observabilidade import request_id_var
from hemocentros.services import projecao
from tests.conftest import TEST_PG_URL

PAYLOAD = {"titulo": "Alerta O-", "hemocentro": "Lavras", "tipo_sanguineo": "O-",
           "data_inicio": "2026-11-10", "data_fim": "2026-11-30"}


def test_post_grava_o_correlation_id_no_outbox(pg_engine, monkeypatch):
    monkeypatch.setenv("HEMOCENTROS_POSTGRES_URL", TEST_PG_URL)
    get_settings.cache_clear()
    try:
        with TestClient(app) as c:
            r = c.post("/api/v1/campanhas", json=PAYLOAD, headers={"X-Request-Id": "req-77"})
    finally:
        get_settings.cache_clear()
    assert r.status_code == 201 and r.headers["x-request-id"] == "req-77"

    async def ler():
        async with create_session_factory(pg_engine)() as s:
            return (await s.scalars(select(OutboxEvent.correlation_id))).all()

    assert asyncio.run(ler()) == ["req-77"]


def test_projecao_usa_o_correlation_id_da_mensagem(monkeypatch):
    vistos = []

    async def upsert(mongo, db, payload):
        vistos.append(request_id_var.get())

    monkeypatch.setattr(projecao.campanhas_view_escrita, "upsert", upsert)

    class Msg:
        body = b'{"id": "c1"}'
        correlation_id = "req-77"

        async def ack(self):
            pass

    asyncio.run(projecao.tratar_mensagem(Msg(), None, "db"))
    assert vistos == ["req-77"] and request_id_var.get() is None  # restaurado depois
