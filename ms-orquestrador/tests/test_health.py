from fastapi.testclient import TestClient

from orquestrador.config import get_settings
from orquestrador.main import app

SEM_BANCO = "postgresql+asyncpg://u:p@127.0.0.1:1/x"


def _cliente(monkeypatch, pg_url: str) -> TestClient:
    monkeypatch.setenv("ORQUESTRADOR_POSTGRES_URL", pg_url)
    monkeypatch.setenv("ORQUESTRADOR_DB_CHECK_TIMEOUT", "0.5")
    get_settings.cache_clear()
    return TestClient(app)


def test_sem_banco_health_200_degradado_e_ready_503(monkeypatch):
    try:
        with _cliente(monkeypatch, SEM_BANCO) as client:
            health, ready = client.get("/health"), client.get("/ready")
    finally:
        get_settings.cache_clear()
    esperado = {"status": "degradado", "bancos": {"postgres": "indisponivel"}}
    assert health.status_code == 200 and health.json() == esperado  # liveness não depende do banco
    assert ready.status_code == 503 and ready.json() == esperado


def test_com_banco_health_e_ready_ok(pg_engine, monkeypatch):
    from tests.conftest import TEST_PG_URL

    try:
        with _cliente(monkeypatch, TEST_PG_URL) as client:
            health, ready = client.get("/health"), client.get("/ready")
    finally:
        get_settings.cache_clear()
    esperado = {"status": "ok", "bancos": {"postgres": "ok"}}
    assert health.json() == esperado
    assert ready.status_code == 200 and ready.json() == esperado


def test_request_id_e_devolvido(monkeypatch):
    try:
        with _cliente(monkeypatch, SEM_BANCO) as client:
            r = client.get("/health", headers={"X-Request-Id": "abc-123"})
    finally:
        get_settings.cache_clear()
    assert r.headers["X-Request-Id"] == "abc-123"
