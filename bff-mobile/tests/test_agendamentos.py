import json

import httpx
import pytest
from fastapi.testclient import TestClient

from bff_mobile.api.agendamentos import get_orquestrador
from bff_mobile.clients.servicos import OrquestradorClient
from bff_mobile.main import app
from bff_mobile.observabilidade import propagar_request_id

SAGA_ID = "0b6a6c9e-5f7a-4d0e-9b8b-1f2e3d4c5b6a"
CRIADA = {"sagaId": SAGA_ID, "agendamentoId": "ag-1", "status": "STARTED",
          "_links": {"self": {"href": f"/api/v1/sagas/{SAGA_ID}", "method": "GET"}}}
USUARIO = {"X-User-Id": "doador-1"}


def _saga(status="STARTED", doador="doador-1", recusa=None, finalizada=False):
    return {"sagaId": SAGA_ID, "agendamentoId": "ag-1", "doadorId": doador, "slotId": "slot-1", "status": status,
            "finalizada": finalizada, "passoAtual": "STEP1", "tentativas": 0,
            "dataHoraInicio": "2026-11-25T14:00:00Z", "recusa": recusa, "erro": None,
            "criadaEm": "2026-11-17T10:00:00Z", "atualizadaEm": "2026-11-17T10:00:01Z", "passos": []}


class Orquestrador:
    """ms-orquestrador simulado: registra as requisições recebidas."""

    def __init__(self, handler):
        self.requisicoes: list[httpx.Request] = []
        self._handler = handler

    def client(self) -> TestClient:
        def registrar(req):
            self.requisicoes.append(req)
            return self._handler(req)

        http = httpx.AsyncClient(transport=httpx.MockTransport(registrar), base_url="http://o",
                                 event_hooks={"request": [propagar_request_id]})  # como em main.py
        orq = OrquestradorClient(http)
        app.dependency_overrides[get_orquestrador] = lambda: orq
        return TestClient(app)


@pytest.fixture(autouse=True)
def _limpar():
    yield
    app.dependency_overrides.clear()


def _resp(status, corpo):
    return lambda _req: httpx.Response(status, json=corpo)


# ------------------------------------------------------------------ POST /bff-mobile/agendamentos


def test_solicitar_agendamento_inicia_a_saga_com_o_usuario_autenticado():
    o = Orquestrador(_resp(202, CRIADA))
    with o.client() as c:
        r = c.post("/bff-mobile/agendamentos", json={"slotId": "slot-1"},
                   headers={**USUARIO, "Idempotency-Key": "app-1", "X-Request-Id": "req-9"})
    assert r.status_code == 202
    assert r.json() == {"sagaId": SAGA_ID, "agendamentoId": "ag-1", "situacao": "EM_ANDAMENTO",
                        "_links": {"acompanhar": {"href": f"/api/mobile/sagas/{SAGA_ID}", "method": "GET"}}}
    assert r.headers["Location"] == f"/api/mobile/sagas/{SAGA_ID}"
    (req,) = o.requisicoes
    assert (req.method, req.url.path) == ("POST", "/api/v1/sagas/agendamento")
    assert json.loads(req.content) == {"doadorId": "doador-1", "slotId": "slot-1"}  # doador = X-User-Id
    assert req.headers["Idempotency-Key"] == "app-1"
    assert req.headers["X-Request-Id"] == "req-9"  # correlation id propagado


def test_doador_no_corpo_e_ignorado():
    o = Orquestrador(_resp(202, CRIADA))
    with o.client() as c:
        c.post("/bff-mobile/agendamentos", json={"slotId": "slot-1", "doadorId": "outro"}, headers=USUARIO)
    assert json.loads(o.requisicoes[0].content)["doadorId"] == "doador-1"


@pytest.mark.parametrize("status,tipo", [(409, "agendamento-ativo"), (422, "idempotency-key-reutilizada")])
def test_recusas_do_orquestrador_sao_repassadas(status, tipo):
    problema = {"type": f"urn:startech:error:{tipo}", "title": "x", "status": status, "detail": "y"}
    with Orquestrador(_resp(status, problema)).client() as c:
        r = c.post("/bff-mobile/agendamentos", json={"slotId": "slot-1"}, headers=USUARIO)
    assert r.status_code == status and r.json() == problema
    assert r.headers["content-type"] == "application/problem+json"


@pytest.mark.parametrize("handler", [
    _resp(503, {"title": "fora"}),
    lambda req: (_ for _ in ()).throw(httpx.ConnectError("recusado", request=req)),
    lambda req: (_ for _ in ()).throw(httpx.ReadTimeout("lento", request=req)),
    lambda _req: httpx.Response(202, content=b"nao-json"),
])
def test_orquestrador_fora_e_503_problem_json(handler):
    with Orquestrador(handler).client() as c:
        r = c.post("/bff-mobile/agendamentos", json={"slotId": "slot-1"}, headers=USUARIO)
    assert r.status_code == 503 and r.json()["type"] == "urn:startech:error:servico-indisponivel"


def test_sem_usuario_e_401():
    o = Orquestrador(_resp(202, CRIADA))
    with o.client() as c:
        r = c.post("/bff-mobile/agendamentos", json={"slotId": "slot-1"})
    assert r.status_code == 401 and o.requisicoes == []


def test_sem_slot_nao_chama_o_orquestrador():
    o = Orquestrador(_resp(202, CRIADA))
    with o.client() as c:
        r = c.post("/bff-mobile/agendamentos", json={}, headers=USUARIO)
    assert r.status_code == 422 and o.requisicoes == []


# ------------------------------------------------------------------ GET /bff-mobile/sagas/{id}


@pytest.mark.parametrize("status,situacao,finalizada", [
    ("STARTED", "EM_ANDAMENTO", False),
    ("AWAITING_COMUNICACAO", "EM_ANDAMENTO", False),
    ("COMPENSATING", "EM_ANDAMENTO", False),
    ("CONFIRMED", "CONFIRMADO", True),
    ("REJECTED", "RECUSADO", True),
    ("COMPENSATED", "CANCELADO", True),
    ("COMPENSATION_FAILED", "ERRO", True),
])
def test_acompanhar_traduz_o_status_para_o_app(status, situacao, finalizada):
    o = Orquestrador(_resp(200, _saga(status, finalizada=finalizada)))
    with o.client() as c:
        r = c.get(f"/bff-mobile/sagas/{SAGA_ID}", headers=USUARIO)
    assert r.status_code == 200
    corpo = r.json()
    assert (corpo["situacao"], corpo["finalizada"]) == (situacao, finalizada)
    assert corpo["dataHoraInicio"] == "2026-11-25T14:00:00Z"
    assert ("novo-agendamento" in corpo["_links"]) == (status in ("REJECTED", "COMPENSATED"))
    assert o.requisicoes[0].url.path == f"/api/v1/sagas/{SAGA_ID}"


def test_motivo_da_recusa_rn01_aparece_para_o_doador():
    recusa = {"type": "urn:startech:error:intervalo-minimo", "status": 422,
              "detail": "Doação há 10 dias; a próxima é permitida a partir de 2026-12-27."}
    with Orquestrador(_resp(200, _saga("COMPENSATED", recusa=recusa, finalizada=True))).client() as c:
        corpo = c.get(f"/bff-mobile/sagas/{SAGA_ID}", headers=USUARIO).json()
    assert corpo["situacao"] == "CANCELADO" and corpo["motivo"] == recusa["detail"]


@pytest.mark.parametrize("handler", [
    _resp(200, _saga(doador="outro-doador")),  # SAGA de outra pessoa: não revela que existe
    _resp(404, {"type": "urn:startech:error:saga-nao-encontrada"}),
    _resp(400, {"type": "urn:startech:error:payload-invalido"}),
])
def test_saga_inexistente_ou_de_outro_doador_e_404(handler):
    with Orquestrador(handler).client() as c:
        r = c.get(f"/bff-mobile/sagas/{SAGA_ID}", headers=USUARIO)
    assert r.status_code == 404 and r.json()["type"] == "urn:startech:error:agendamento-nao-encontrado"


def test_acompanhar_com_orquestrador_fora_e_503():
    with Orquestrador(_resp(500, {})).client() as c:
        r = c.get(f"/bff-mobile/sagas/{SAGA_ID}", headers=USUARIO)
    assert r.status_code == 503


def test_acompanhar_sem_usuario_e_401():
    with Orquestrador(_resp(200, _saga())).client() as c:
        assert c.get(f"/bff-mobile/sagas/{SAGA_ID}").status_code == 401


def test_rotas_de_agendamento_exigem_o_papel_doador(monkeypatch):
    from bff_mobile.config import get_settings

    monkeypatch.setenv("BFF_MOBILE_EXIGIR_PAPEL", "true")
    get_settings.cache_clear()
    try:
        with Orquestrador(_resp(202, CRIADA)).client() as c:
            negado = c.post("/bff-mobile/agendamentos", json={"slotId": "s"}, headers={**USUARIO, "X-User-Roles": "operador"})
            aceito = c.post("/bff-mobile/agendamentos", json={"slotId": "s"}, headers={**USUARIO, "X-User-Roles": "doador"})
            negado_get = c.get(f"/bff-mobile/sagas/{SAGA_ID}", headers={**USUARIO, "X-User-Roles": "operador"})
    finally:
        get_settings.cache_clear()
    assert (negado.status_code, aceito.status_code, negado_get.status_code) == (403, 202, 403)
