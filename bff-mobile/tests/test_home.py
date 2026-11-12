import httpx
import pytest
from fastapi.testclient import TestClient

from bff_mobile.api.home import get_doadores, get_hemocentros
from bff_mobile.clients.servicos import DoadoresClient, HemocentrosClient
from bff_mobile.main import app

DOADOR = {"id": "123", "nome": "Maria", "tipoSanguineo": "A+"}
CAMPANHAS_A = [{"id": "c2", "tipo_sanguineo": "A+"}]
CAMPANHAS_O = [{"id": "c1", "tipo_sanguineo": "O-"}]


class Servicos:
    """Serviços internos simulados que registram as chamadas recebidas."""

    def __init__(self, doadores, hemocentros):
        self.chamadas = []
        self._doadores, self._hemocentros = doadores, hemocentros

    def _wrap(self, fn):
        def handler(req: httpx.Request):
            self.chamadas.append((req.url.path, dict(req.url.params), req.headers.get("x-user-id")))
            return fn(req)
        return handler

    def client(self) -> TestClient:
        d = DoadoresClient(httpx.AsyncClient(transport=httpx.MockTransport(self._wrap(self._doadores)), base_url="http://d"))
        h = HemocentrosClient(httpx.AsyncClient(transport=httpx.MockTransport(self._wrap(self._hemocentros)), base_url="http://h"))
        app.dependency_overrides[get_doadores] = lambda: d
        app.dependency_overrides[get_hemocentros] = lambda: h
        return TestClient(app)


def _campanhas_por_tipo(req: httpx.Request):
    tipo = req.url.params.get("tipo_sanguineo")
    return httpx.Response(200, json=CAMPANHAS_A if tipo == "A+" else CAMPANHAS_O if tipo == "O-" else CAMPANHAS_A + CAMPANHAS_O)


def _erro(exc: Exception):
    def f(req):
        raise exc
    return f


@pytest.fixture(autouse=True)
def _limpa():
    yield
    app.dependency_overrides.clear()


def test_home_ok_filtra_campanhas_pelo_tipo_do_doador():
    s = Servicos(lambda r: httpx.Response(200, json=DOADOR), _campanhas_por_tipo)
    r = s.client().get("/bff-mobile/home", headers={"X-User-Id": "123"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["servicosIndisponiveis"] == []
    assert body["doador"]["nome"] == "Maria" and body["campanhas"] == CAMPANHAS_A
    assert s.chamadas == [("/api/v1/doadores/123", {}, "123"), ("/api/v1/campanhas", {"tipo_sanguineo": "A+"}, "123")]


@pytest.mark.parametrize(
    "falha",
    [
        _erro(httpx.ConnectError("recusada")),
        _erro(httpx.ReadTimeout("lento")),
        lambda r: httpx.Response(500, text="boom"),
        lambda r: httpx.Response(404, json={"title": "não encontrado"}),
        lambda r: httpx.Response(200, text="<html>não é json</html>"),
    ],
    ids=["conexao", "timeout", "http-500", "http-404", "resposta-invalida"],
)
def test_doadores_fora_nao_gera_500_e_entrega_campanhas_degradado(falha):
    s = Servicos(falha, _campanhas_por_tipo)
    r = s.client().get("/bff-mobile/home", headers={"X-User-Id": "123"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degradado" and body["servicosIndisponiveis"] == ["ms-doadores"]
    assert body["doador"] == {"id": "123", "statusDegradado": True}
    assert body["campanhas"] == CAMPANHAS_O  # fallback O- do ADR
    assert s.chamadas[-1][1] == {"tipo_sanguineo": "O-"}


def test_hemocentros_fora_mantem_perfil_e_degrada():
    s = Servicos(lambda r: httpx.Response(200, json=DOADOR), _erro(httpx.ConnectError("x")))
    r = s.client().get("/bff-mobile/home", headers={"X-User-Id": "123"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degradado" and body["servicosIndisponiveis"] == ["ms-hemocentros"]
    assert body["doador"]["nome"] == "Maria" and body["campanhas"] == []


def test_ambos_fora_ainda_responde_200_degradado():
    s = Servicos(_erro(httpx.ConnectError("x")), _erro(httpx.ConnectError("y")))
    r = s.client().get("/bff-mobile/home", headers={"X-User-Id": "123"})
    assert r.status_code == 200 and r.json()["servicosIndisponiveis"] == ["ms-doadores", "ms-hemocentros"]


def test_perfil_sem_tipo_sanguineo_usa_fallback():
    s = Servicos(lambda r: httpx.Response(200, json={"id": "123"}), _campanhas_por_tipo)
    r = s.client().get("/bff-mobile/home", headers={"X-User-Id": "123"})
    assert r.json()["status"] == "ok" and s.chamadas[-1][1] == {"tipo_sanguineo": "O-"}


def test_aceita_tipo_sanguineo_em_snake_case():
    s = Servicos(lambda r: httpx.Response(200, json={"id": "1", "tipo_sanguineo": "A+"}), _campanhas_por_tipo)
    assert s.client().get("/bff-mobile/home", headers={"X-User-Id": "1"}).json()["campanhas"] == CAMPANHAS_A


def test_sem_x_user_id_retorna_401_problem_json():
    s = Servicos(lambda r: httpx.Response(200, json=DOADOR), _campanhas_por_tipo)
    r = s.client().get("/bff-mobile/home")
    assert r.status_code == 401 and r.headers["content-type"].startswith("application/problem+json")
    assert s.chamadas == []


def test_clientes_reais_do_lifespan_degradam_com_servicos_inalcancaveis(monkeypatch):
    """Sem overrides: exercita o `lifespan` e os clientes httpx reais contra portas sem serviço."""
    from bff_mobile.config import get_settings

    monkeypatch.setenv("BFF_MOBILE_DOADORES_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("BFF_MOBILE_HEMOCENTROS_URL", "http://127.0.0.1:1")
    get_settings.cache_clear()
    try:
        with TestClient(app) as c:
            r = c.get("/bff-mobile/home", headers={"X-User-Id": "123"})
    finally:
        get_settings.cache_clear()
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degradado" and body["servicosIndisponiveis"] == ["ms-doadores", "ms-hemocentros"]


def test_resposta_invalida_do_hemocentros_degrada():
    s = Servicos(lambda r: httpx.Response(200, json=DOADOR), lambda r: httpx.Response(200, text="<html>"))
    body = s.client().get("/bff-mobile/home", headers={"X-User-Id": "123"}).json()
    assert body["servicosIndisponiveis"] == ["ms-hemocentros"] and body["campanhas"] == []
