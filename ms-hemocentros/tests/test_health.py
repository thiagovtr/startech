from fastapi.testclient import TestClient

from hemocentros.main import app


def test_sobe_e_reporta_degradado_sem_bancos(monkeypatch):
    # Portas sem serviço: o app deve subir e informar o estado de cada banco.
    monkeypatch.setenv("HEMOCENTROS_POSTGRES_URL", "postgresql+asyncpg://u:p@127.0.0.1:1/x")
    monkeypatch.setenv("HEMOCENTROS_MONGO_URL", "mongodb://127.0.0.1:1")
    monkeypatch.setenv("HEMOCENTROS_DB_CHECK_TIMEOUT", "0.5")
    from hemocentros.config import get_settings

    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            r = client.get("/health")
    finally:
        get_settings.cache_clear()
    assert r.status_code == 200
    assert r.json() == {"status": "degradado", "bancos": {"postgres": "indisponivel", "mongo": "indisponivel"}}


def test_health_ok_com_os_dois_bancos(pg_engine, mongo_view, monkeypatch):
    from tests.conftest import TEST_MONGO_DB, TEST_MONGO_URL, TEST_PG_URL

    monkeypatch.setenv("HEMOCENTROS_POSTGRES_URL", TEST_PG_URL)
    monkeypatch.setenv("HEMOCENTROS_MONGO_URL", TEST_MONGO_URL)
    monkeypatch.setenv("HEMOCENTROS_MONGO_DB", TEST_MONGO_DB)
    from hemocentros.config import get_settings

    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            r = client.get("/health")
    finally:
        get_settings.cache_clear()
    assert r.json() == {"status": "ok", "bancos": {"postgres": "ok", "mongo": "ok"}}
