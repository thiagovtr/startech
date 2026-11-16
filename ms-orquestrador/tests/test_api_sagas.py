"""API da SAGA (PostgreSQL real): início (202/409/422/400), idempotência e consulta (200/404)."""

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from orquestrador.config import get_settings
from orquestrador.main import app
from orquestrador.repositories import sagas as repo
from orquestrador.saga.estados import Passo, PassoConcluido, PassoRecusado, Politica
from orquestrador.saga.maquina import transicionar
from tests.conftest import TEST_PG_URL

URL = "/api/v1/sagas/agendamento"
CORPO = {"doadorId": "doador-1", "slotId": "slot-1"}


class _ExecutorParado:
    def __init__(self):
        self.disparadas = []

    async def avancar(self, saga_id, reivindicada=False):
        self.disparadas.append(saga_id)


@pytest.fixture
def client(pg_engine, monkeypatch):
    monkeypatch.setenv("ORQUESTRADOR_POSTGRES_URL", TEST_PG_URL)
    get_settings.cache_clear()
    try:
        with TestClient(app) as c:
            app.state.executor = _ExecutorParado()  # aqui só a API; o executor é testado em test_executor.py
            yield c
    finally:
        get_settings.cache_clear()


# ------------------------------------------------------------------ POST


def test_inicia_a_saga_com_202_location_e_link(client):
    r = client.post(URL, json=CORPO, headers={"X-Request-Id": "req-42"})
    assert r.status_code == 202
    corpo = r.json()
    saga_id = corpo["sagaId"]
    uuid.UUID(saga_id), uuid.UUID(corpo["agendamentoId"])
    assert corpo["status"] == "STARTED"
    assert r.headers["Location"] == f"/api/v1/sagas/{saga_id}"
    assert corpo["_links"] == {"self": {"href": f"/api/v1/sagas/{saga_id}", "method": "GET"}}

    g = client.get(r.headers["Location"]).json()
    assert (g["doadorId"], g["slotId"], g["status"], g["passoAtual"]) == ("doador-1", "slot-1", "STARTED", "STEP1")
    assert g["finalizada"] is False and g["passos"] == [] and g["tentativas"] == 0


def test_correlation_id_da_requisicao_fica_na_saga(client, pg_engine):
    r = client.post(URL, json=CORPO, headers={"X-Request-Id": "req-rastreio"})
    saga = asyncio.run(repo.obter(async_sessionmaker(pg_engine), uuid.UUID(r.json()["sagaId"])))
    assert saga.correlation_id == "req-rastreio"


def test_segunda_solicitacao_do_mesmo_doador_e_409_rn09(client):
    assert client.post(URL, json=CORPO).status_code == 202
    r = client.post(URL, json={**CORPO, "slotId": "slot-2"})
    assert r.status_code == 409
    assert r.headers["content-type"] == "application/problem+json"
    assert r.json()["type"] == "urn:startech:error:agendamento-ativo"


def test_mesma_idempotency_key_devolve_a_mesma_saga_e_dispara_uma_vez(client):
    a = client.post(URL, json=CORPO, headers={"Idempotency-Key": "app-123"})
    b = client.post(URL, json=CORPO, headers={"Idempotency-Key": "app-123"})
    assert a.status_code == b.status_code == 202
    assert a.json() == b.json()
    assert app.state.executor.disparadas == [uuid.UUID(a.json()["sagaId"])]


def test_idempotency_key_reutilizada_com_outro_slot_e_422(client):
    client.post(URL, json=CORPO, headers={"Idempotency-Key": "app-123"})
    r = client.post(URL, json={**CORPO, "slotId": "outro"}, headers={"Idempotency-Key": "app-123"})
    assert r.status_code == 422
    assert r.json()["type"] == "urn:startech:error:idempotency-key-reutilizada"


@pytest.mark.parametrize("corpo", [{}, {"doadorId": "d"}, {"doadorId": "", "slotId": "s"}, {"doadorId": "d", "slotId": "x" * 65}])
def test_payload_invalido_e_400_problem_json(client, corpo):
    r = client.post(URL, json=corpo)
    assert r.status_code == 400
    assert r.json()["type"] == "urn:startech:error:payload-invalido"


def test_aceita_snake_case_tambem(client):
    assert client.post(URL, json={"doador_id": "d9", "slot_id": "s9"}).status_code == 202


# ------------------------------------------------------------------ GET


def test_saga_inexistente_e_404(client):
    r = client.get(f"/api/v1/sagas/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["type"] == "urn:startech:error:saga-nao-encontrada"


def test_id_que_nao_e_uuid_e_400(client):
    assert client.get("/api/v1/sagas/nao-e-uuid").status_code == 400


def test_consulta_mostra_passos_recusa_e_data_do_slot(client, pg_engine):
    saga_id = uuid.UUID(client.post(URL, json=CORPO).json()["sagaId"])
    problema = {"status": 422, "type": "urn:startech:error:intervalo-minimo", "detail": "doou há 10 dias"}
    sessoes = async_sessionmaker(pg_engine, expire_on_commit=False)

    async def avancar():
        saga = await repo.obter(sessoes, saga_id)
        for ev in (PassoConcluido(Passo.STEP1, {"dataHoraInicio": "2026-11-25T14:00:00Z"}),
                   PassoRecusado(Passo.STEP2, problema)):
            t = transicionar(repo.estado_de(saga), ev, Politica())
            saga = await repo.aplicar_transicao(sessoes, saga, t, agora=datetime.now(UTC))

    asyncio.run(avancar())
    g = client.get(f"/api/v1/sagas/{saga_id}").json()
    assert (g["status"], g["passoAtual"], g["finalizada"]) == ("COMPENSATING", "STEP1", False)
    assert g["dataHoraInicio"] == "2026-11-25T14:00:00Z"
    assert g["recusa"] == problema
    assert [(p["passo"], p["direcao"], p["resultado"]) for p in g["passos"]] == [
        ("STEP1", "FORWARD", "OK"), ("STEP2", "FORWARD", "RECUSADO"),
    ]
