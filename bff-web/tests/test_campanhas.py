import httpx
import pytest
from fastapi.testclient import TestClient

from bff_web.clients.hemocentros import HemocentrosClient, get_hemocentros_client
from bff_web.main import app

CAMPANHA = {"id": "c1", "titulo": "Alerta O-", "hemocentro": "Lavras", "tipo_sanguineo": "O-",
            "urgencia": "CRITICO", "status": "ATIVA", "data_inicio": "2026-11-10", "data_fim": "2026-11-30"}
PAYLOAD = {k: v for k, v in CAMPANHA.items() if k not in ("id", "status")}


def _client(handler):
    cliente = HemocentrosClient(httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://hemo"))
    app.dependency_overrides[get_hemocentros_client] = lambda: cliente
    return TestClient(app)


@pytest.fixture(autouse=True)
def _limpa():
    yield
    app.dependency_overrides.clear()


def test_criar_e_listar_campanha_repassa_user_id():
    vistos = []

    def handler(req: httpx.Request):
        vistos.append((req.method, req.url.path, req.headers.get("x-user-id")))
        if req.method == "POST":
            return httpx.Response(201, json=CAMPANHA)
        return httpx.Response(200, json=[CAMPANHA])

    c = _client(handler)
    r = c.post("/bff-web/campanhas", json=PAYLOAD, headers={"X-User-Id": "op-7"})
    assert r.status_code == 201 and r.json()["id"] == "c1"
    r = c.get("/bff-web/campanhas", params={"tipo_sanguineo": "O-"}, headers={"X-User-Id": "op-7"})
    assert r.status_code == 200 and r.json()[0]["id"] == "c1"
    assert vistos == [("POST", "/api/v1/campanhas", "op-7"), ("GET", "/api/v1/campanhas", "op-7")]


def test_repassa_filtro_tipo_sanguineo():
    def handler(req: httpx.Request):
        assert req.url.params["tipo_sanguineo"] == "O-"
        return httpx.Response(200, json=[])

    assert _client(handler).get("/bff-web/campanhas", params={"tipo_sanguineo": "O-"}).json() == []


def test_erro_400_do_servico_e_repassado():
    problema = {"type": "urn:startech:error:payload-invalido", "title": "Payload inválido", "status": 400,
                "invalidParams": [{"name": "tipo_sanguineo", "reason": "inválido"}]}
    c = _client(lambda req: httpx.Response(400, json=problema, headers={"content-type": "application/problem+json"}))
    r = c.post("/bff-web/campanhas", json={})
    assert r.status_code == 400
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json() == problema


def test_servico_fora_do_ar_retorna_503():
    def handler(req):
        raise httpx.ConnectError("recusada")

    r = _client(handler).get("/bff-web/campanhas")
    assert r.status_code == 503 and r.json()["type"] == "urn:startech:error:servico-indisponivel"


def test_timeout_retorna_504():
    def handler(req):
        raise httpx.ReadTimeout("lento")

    r = _client(handler).get("/bff-web/campanhas")
    assert r.status_code == 504 and r.json()["type"] == "urn:startech:error:servico-timeout"


def test_erro_500_do_servico_vira_502():
    r = _client(lambda req: httpx.Response(500, text="boom")).get("/bff-web/campanhas")
    assert r.status_code == 502


def test_erro_4xx_sem_corpo_json_e_repassado_com_corpo_minimo():
    r = _client(lambda req: httpx.Response(404, text="não achei")).get("/bff-web/campanhas")
    assert r.status_code == 404 and r.json()["status"] == 404


def test_clientes_reais_do_lifespan_retornam_503_sem_servico(monkeypatch):
    """Sem overrides: exercita o `lifespan` e o cliente httpx real contra uma porta sem serviço."""
    from bff_web.config import get_settings

    monkeypatch.setenv("BFF_WEB_HEMOCENTROS_URL", "http://127.0.0.1:1")
    get_settings.cache_clear()
    try:
        with TestClient(app) as c:
            r = c.get("/bff-web/campanhas")
    finally:
        get_settings.cache_clear()
    assert r.status_code == 503
