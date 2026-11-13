import pytest
from fastapi.testclient import TestClient

from hemocentros.config import get_settings
from hemocentros.main import app
from tests.conftest import TEST_MONGO_DB, TEST_MONGO_URL

DOCS = [
    {"_id": "c1", "titulo": "Alerta O-", "hemocentro": "Lavras", "tipo_sanguineo": "O-", "urgencia": "CRITICO",
     "status": "ATIVA", "data_inicio": "2026-11-10", "data_fim": "2026-11-30"},
    {"_id": "c2", "titulo": "Fim de ano", "hemocentro": "Lavras", "tipo_sanguineo": "A+", "urgencia": "NORMAL",
     "status": "ATIVA", "data_inicio": "2026-11-15", "data_fim": "2026-12-20"},
    {"_id": "c3", "titulo": "Reposição O-", "hemocentro": "BH", "tipo_sanguineo": "O-", "urgencia": "NORMAL",
     "status": "ATIVA", "data_inicio": "2026-11-12", "data_fim": "2026-12-05"},
]


@pytest.fixture
def client(mongo_view, monkeypatch):
    mongo_view.insert_many([dict(d) for d in DOCS])
    monkeypatch.setenv("HEMOCENTROS_MONGO_URL", TEST_MONGO_URL)
    monkeypatch.setenv("HEMOCENTROS_MONGO_DB", TEST_MONGO_DB)
    # PostgreSQL inalcançável de propósito: a leitura não pode depender dele.
    monkeypatch.setenv("HEMOCENTROS_POSTGRES_URL", "postgresql+asyncpg://u:p@127.0.0.1:1/x")
    get_settings.cache_clear()
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


def test_lista_todas(client):
    r = client.get("/api/v1/campanhas")
    assert r.status_code == 200
    assert {c["id"] for c in r.json()} == {"c1", "c2", "c3"}


def test_filtra_por_tipo_sanguineo_sem_usar_postgres(client):
    r = client.get("/api/v1/campanhas", params={"tipo_sanguineo": "O-"})
    assert r.status_code == 200
    assert [c["id"] for c in r.json()] == ["c1", "c3"]  # ordenadas por data_inicio
    assert all(c["tipo_sanguineo"] == "O-" for c in r.json())


def test_tipo_sem_campanhas_retorna_lista_vazia(client):
    assert client.get("/api/v1/campanhas", params={"tipo_sanguineo": "AB-"}).json() == []


def test_paginacao_limit_offset_e_total(client):
    r = client.get("/api/v1/campanhas", params={"limit": 2})
    assert [c["id"] for c in r.json()] == ["c1", "c3"]  # ordem por data_inicio
    assert r.headers["X-Total-Count"] == "3"
    r = client.get("/api/v1/campanhas", params={"limit": 2, "offset": 2})
    assert [c["id"] for c in r.json()] == ["c2"]
    assert r.headers["X-Total-Count"] == "3"


def test_total_respeita_o_filtro_de_tipo(client):
    r = client.get("/api/v1/campanhas", params={"tipo_sanguineo": "O-", "limit": 1})
    assert [c["id"] for c in r.json()] == ["c1"]
    assert r.headers["X-Total-Count"] == "2"


def test_limites_invalidos_retornam_400(client):
    assert client.get("/api/v1/campanhas", params={"limit": 0}).status_code == 400
    assert client.get("/api/v1/campanhas", params={"limit": 201}).status_code == 400
    assert client.get("/api/v1/campanhas", params={"offset": -1}).status_code == 400


def test_filtro_por_status(client, mongo_view):
    mongo_view.update_one({"_id": "c2"}, {"$set": {"status": "ENCERRADA"}})
    assert [c["id"] for c in client.get("/api/v1/campanhas", params={"status": "ENCERRADA"}).json()] == ["c2"]
    assert {c["id"] for c in client.get("/api/v1/campanhas", params={"status": "ATIVA"}).json()} == {"c1", "c3"}


def test_vigentes_exclui_encerradas_e_mantem_as_que_terminam_hoje(client, mongo_view, monkeypatch):
    from datetime import date

    from hemocentros.api import campanhas as api

    class _Hoje(date):
        @classmethod
        def today(cls):
            return date(2026, 12, 5)

    monkeypatch.setattr(api, "date", _Hoje)
    r = client.get("/api/v1/campanhas", params={"vigentes": "true"})
    assert {c["id"] for c in r.json()} == {"c2", "c3"}  # c1 terminou em 30/11; c3 termina hoje
    assert r.headers["X-Total-Count"] == "2"
    # sem o filtro, as encerradas continuam aparecendo
    assert len(client.get("/api/v1/campanhas").json()) == 3


def test_mongo_indisponivel_retorna_503(monkeypatch):
    monkeypatch.setenv("HEMOCENTROS_MONGO_URL", "mongodb://127.0.0.1:1")
    monkeypatch.setenv("HEMOCENTROS_DB_CHECK_TIMEOUT", "0.5")
    monkeypatch.setenv("HEMOCENTROS_POSTGRES_URL", "postgresql+asyncpg://u:p@127.0.0.1:1/x")
    get_settings.cache_clear()
    try:
        with TestClient(app) as c:
            r = c.get("/api/v1/campanhas")
    finally:
        get_settings.cache_clear()
    assert r.status_code == 503
    assert r.json()["type"] == "urn:startech:error:banco-indisponivel"
