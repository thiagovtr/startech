import pytest
from fastapi.testclient import TestClient

from bff_mobile.config import get_settings
from bff_mobile.main import app

ROTA = "/bff-mobile/home"
PAPEL_CERTO = "doador"
PAPEL_ERRADO = "operador"


@pytest.fixture
def exigindo(monkeypatch):
    monkeypatch.setenv("BFF_MOBILE_EXIGIR_PAPEL", "true")
    get_settings.cache_clear()
    with TestClient(app) as c:  # lifespan cria os clientes reais (serviços internos inalcançáveis)
        yield c
    get_settings.cache_clear()


@pytest.mark.parametrize("papeis", [None, "", PAPEL_ERRADO, "admin, outro"])
def test_sem_o_papel_da_superficie_retorna_403(exigindo, papeis):
    headers = {"X-User-Id": "u1"} | ({"X-User-Roles": papeis} if papeis is not None else {})
    r = exigindo.get(ROTA, headers=headers)
    assert r.status_code == 403
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["type"] == "urn:startech:error:papel-insuficiente"


def test_com_o_papel_passa_pela_autorizacao(exigindo):
    # passa da autorização; o serviço interno inexistente gera degradação/erro, mas nunca 403
    r = exigindo.get(ROTA, headers={"X-User-Id": "u1", "X-User-Roles": f"offline_access, {PAPEL_CERTO.upper()}"})
    assert r.status_code != 403


def test_probes_nao_exigem_papel(exigindo):
    assert exigindo.get("/health").status_code == 200 and exigindo.get("/ready").status_code == 200


def test_desligado_por_padrao_nao_exige_papel():
    get_settings.cache_clear()
    with TestClient(app) as c:
        r = c.get(ROTA, headers={"X-User-Id": "u1"})
    assert r.status_code != 403
