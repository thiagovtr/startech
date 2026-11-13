from fastapi.testclient import TestClient

from bff_web.config import Settings
from bff_web.main import app


def test_health_ok():
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_urls_configuraveis_por_env(monkeypatch):
    monkeypatch.setenv("BFF_WEB_HEMOCENTROS_URL", "http://localhost:9999")
    assert Settings().hemocentros_url == "http://localhost:9999"


def test_ready_ok_sem_depender_de_servicos_internos():
    r = TestClient(app).get("/ready")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
