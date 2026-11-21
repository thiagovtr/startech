"""Recurso Agendamento no BFF Mobile: consulta, listagem e cancelamento com HATEOAS (contratos §3)."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from bff_mobile.api.agendamentos import get_agendamentos
from bff_mobile.clients.servicos import AgendamentosClient
from bff_mobile.main import app
from bff_mobile.observabilidade import propagar_request_id

USUARIO = {"X-User-Id": "doador-1"}


def _agendamento(status="CONFIRMADO", doador="doador-1", ag_id="ag-1"):
    base = f"/api/v1/agendamentos/{ag_id}"
    links = {"self": {"href": base, "method": "GET", "title": "Consultar dados do agendamento"}}
    if status == "CONFIRMADO":
        links["cancelar"] = {"href": f"{base}/cancelamento", "method": "POST", "title": "Cancelar",
                             "conditions": "Permitido até 2 horas antes do horário agendado"}
    if status.startswith("CANCELADO"):
        links["novo-agendamento"] = {"href": "/api/v1/sagas/agendamento", "method": "POST"}
    links["interno-sem-rota"] = {"href": "/api/v1/slots/slot-1", "method": "GET"}  # deve ser descartado
    return {"id": ag_id, "status": status, "concluido": False, "doadorId": doador,
            "slot": {"slotId": "slot-1", "postoId": "posto-1", "dataHoraInicio": "2026-12-01T14:00:00Z",
                     "dataHoraFim": "2026-12-01T14:20:00Z"},
            "_links": links}


class Agendamentos:
    """ms-agendamentos simulado: registra as requisições recebidas."""

    def __init__(self, handler):
        self.requisicoes: list[httpx.Request] = []
        self._handler = handler

    def client(self) -> TestClient:
        def registrar(req):
            self.requisicoes.append(req)
            return self._handler(req)

        http = httpx.AsyncClient(transport=httpx.MockTransport(registrar), base_url="http://a",
                                 event_hooks={"request": [propagar_request_id]})
        cliente = AgendamentosClient(http)
        app.dependency_overrides[get_agendamentos] = lambda: cliente
        return TestClient(app)


@pytest.fixture(autouse=True)
def _limpar():
    yield
    app.dependency_overrides.clear()


def _resp(status, corpo):
    return lambda _req: httpx.Response(status, json=corpo)


# ------------------------------------------------------------------ GET /bff-mobile/agendamentos/{id}


def test_confirmado_tem_links_publicos_de_consulta_e_cancelamento():
    a = Agendamentos(_resp(200, _agendamento()))
    with a.client() as c:
        r = c.get("/bff-mobile/agendamentos/ag-1", headers={**USUARIO, "X-Request-Id": "req-1"})
    assert r.status_code == 200
    links = r.json()["_links"]
    assert links["self"] == {"href": "/api/mobile/agendamentos/ag-1", "method": "GET",
                             "title": "Consultar dados do agendamento"}
    assert links["cancelar"]["href"] == "/api/mobile/agendamentos/ag-1/cancelamento"
    assert links["cancelar"]["method"] == "POST"
    assert "interno-sem-rota" not in links  # link interno sem rota pública não vaza
    (req,) = a.requisicoes
    assert (req.method, req.url.path) == ("GET", "/api/v1/agendamentos/ag-1")
    assert req.headers["X-Request-Id"] == "req-1"


def test_cancelado_tem_novo_agendamento_e_nao_tem_cancelar():
    a = Agendamentos(_resp(200, _agendamento("CANCELADO_DOADOR")))
    with a.client() as c:
        links = c.get("/bff-mobile/agendamentos/ag-1", headers=USUARIO).json()["_links"]
    assert "cancelar" not in links
    assert links["novo-agendamento"] == {"href": "/api/mobile/agendamentos", "method": "POST"}


@pytest.mark.parametrize("resposta", [_resp(404, {"type": "urn:startech:error:agendamento-nao-encontrado"}),
                                      _resp(200, _agendamento(doador="outro"))])
def test_inexistente_ou_de_outro_doador_responde_404(resposta):
    with Agendamentos(resposta).client() as c:
        r = c.get("/bff-mobile/agendamentos/ag-1", headers=USUARIO)
    assert r.status_code == 404
    assert r.json()["type"] == "urn:startech:error:agendamento-nao-encontrado"


def test_sem_usuario_responde_401():
    with Agendamentos(_resp(200, _agendamento())).client() as c:
        assert c.get("/bff-mobile/agendamentos/ag-1").status_code == 401


def test_ms_agendamentos_fora_responde_503():
    def erro(_req):
        raise httpx.ConnectError("recusada")

    with Agendamentos(erro).client() as c:
        r = c.get("/bff-mobile/agendamentos/ag-1", headers=USUARIO)
    assert r.status_code == 503
    assert r.headers["content-type"].startswith("application/problem+json")


# ------------------------------------------------------------------ GET /bff-mobile/agendamentos


def test_listagem_usa_o_doador_autenticado_e_reescreve_os_links():
    corpo = {"itens": [_agendamento(), _agendamento("CANCELADO_DOADOR", ag_id="ag-0")],
             "_links": {"self": {"href": "/api/v1/agendamentos?doadorId=doador-1", "method": "GET"}}}
    a = Agendamentos(_resp(200, corpo))
    with a.client() as c:
        r = c.get("/bff-mobile/agendamentos", params={"doadorId": "outro"}, headers=USUARIO)
    assert r.status_code == 200
    itens = r.json()["itens"]
    assert [i["id"] for i in itens] == ["ag-1", "ag-0"]
    assert itens[0]["_links"]["cancelar"]["href"] == "/api/mobile/agendamentos/ag-1/cancelamento"
    assert r.json()["_links"]["self"] == {"href": "/api/mobile/agendamentos", "method": "GET"}
    assert a.requisicoes[0].url.params["doadorId"] == "doador-1"  # o parâmetro do cliente é ignorado


# ------------------------------------------------------------------ POST .../cancelamento


def test_cancelar_confere_o_dono_e_devolve_o_estado_novo():
    def handler(req):
        if req.method == "GET":
            return httpx.Response(200, json=_agendamento())
        return httpx.Response(200, json=_agendamento("CANCELADO_DOADOR"))

    a = Agendamentos(handler)
    with a.client() as c:
        r = c.post("/bff-mobile/agendamentos/ag-1/cancelamento", json={"motivo": "Imprevisto"}, headers=USUARIO)
    assert r.status_code == 200
    assert r.json()["status"] == "CANCELADO_DOADOR"
    assert set(r.json()["_links"]) == {"self", "novo-agendamento"}
    consulta, cancelamento = a.requisicoes
    assert (consulta.method, consulta.url.path) == ("GET", "/api/v1/agendamentos/ag-1")
    assert (cancelamento.method, cancelamento.url.path) == ("POST", "/api/v1/agendamentos/ag-1/cancelamento")
    assert json.loads(cancelamento.content) == {"motivo": "Imprevisto"}


def test_cancelar_sem_corpo():
    a = Agendamentos(lambda req: httpx.Response(
        200, json=_agendamento() if req.method == "GET" else _agendamento("CANCELADO_DOADOR")))
    with a.client() as c:
        assert c.post("/bff-mobile/agendamentos/ag-1/cancelamento", headers=USUARIO).status_code == 200
    assert json.loads(a.requisicoes[1].content) == {}


def test_cancelar_de_outro_doador_responde_404_sem_cancelar():
    a = Agendamentos(_resp(200, _agendamento(doador="outro")))
    with a.client() as c:
        r = c.post("/bff-mobile/agendamentos/ag-1/cancelamento", headers=USUARIO)
    assert r.status_code == 404
    assert [req.method for req in a.requisicoes] == ["GET"]


def test_cancelar_ja_cancelado_repassa_409():
    problema = {"type": "urn:startech:error:agendamento-ja-cancelado", "title": "Agendamento já cancelado",
                "status": 409, "detail": "O agendamento ag-1 já está CANCELADO_DOADOR."}
    a = Agendamentos(lambda req: httpx.Response(200, json=_agendamento("CANCELADO_DOADOR"))
                     if req.method == "GET" else httpx.Response(409, json=problema))
    with a.client() as c:
        r = c.post("/bff-mobile/agendamentos/ag-1/cancelamento", headers=USUARIO)
    assert r.status_code == 409
    assert r.json() == problema
    assert r.headers["content-type"].startswith("application/problem+json")
