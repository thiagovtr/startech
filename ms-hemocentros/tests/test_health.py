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


def _subir(monkeypatch, pg_url, mongo_url, mongo_db="hemocentros"):
    from hemocentros.config import get_settings

    monkeypatch.setenv("HEMOCENTROS_POSTGRES_URL", pg_url)
    monkeypatch.setenv("HEMOCENTROS_MONGO_URL", mongo_url)
    monkeypatch.setenv("HEMOCENTROS_MONGO_DB", mongo_db)
    monkeypatch.setenv("HEMOCENTROS_DB_CHECK_TIMEOUT", "0.5")
    get_settings.cache_clear()
    return get_settings


def test_ready_503_sem_bancos_mas_health_continua_200(monkeypatch):
    get_settings = _subir(monkeypatch, "postgresql+asyncpg://u:p@127.0.0.1:1/x", "mongodb://127.0.0.1:1")
    try:
        with TestClient(app) as client:
            ready, health = client.get("/ready"), client.get("/health")
    finally:
        get_settings.cache_clear()
    assert ready.status_code == 503
    assert ready.json() == {"status": "degradado", "bancos": {"postgres": "indisponivel", "mongo": "indisponivel"}}
    assert health.status_code == 200  # liveness não depende dos bancos


def test_ready_503_com_so_um_banco_fora(pg_engine, monkeypatch):
    from tests.conftest import TEST_PG_URL

    get_settings = _subir(monkeypatch, TEST_PG_URL, "mongodb://127.0.0.1:1")
    try:
        with TestClient(app) as client:
            r = client.get("/ready")
    finally:
        get_settings.cache_clear()
    assert r.status_code == 503
    assert r.json()["bancos"] == {"postgres": "ok", "mongo": "indisponivel"}


def test_ready_200_com_os_dois_bancos(pg_engine, mongo_view, monkeypatch):
    from tests.conftest import TEST_MONGO_DB, TEST_MONGO_URL, TEST_PG_URL

    get_settings = _subir(monkeypatch, TEST_PG_URL, TEST_MONGO_URL, TEST_MONGO_DB)
    try:
        with TestClient(app) as client:
            r = client.get("/ready")
    finally:
        get_settings.cache_clear()
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "bancos": {"postgres": "ok", "mongo": "ok"}}
