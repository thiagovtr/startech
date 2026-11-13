import asyncio
import uuid
from datetime import date

from fastapi.testclient import TestClient

from hemocentros import worker
from hemocentros.config import get_settings
from hemocentros.db.postgres import create_session_factory
from hemocentros.main import app
from hemocentros.models.campanha import CampanhaCriar
from hemocentros.services.campanhas import criar_campanha
from tests.conftest import TEST_MONGO_DB, TEST_MONGO_URL, TEST_PG_URL


def _ambiente(monkeypatch, amqp_url, **extra):
    s = uuid.uuid4().hex[:8]
    env = {
        "HEMOCENTROS_POSTGRES_URL": TEST_PG_URL, "HEMOCENTROS_MONGO_URL": TEST_MONGO_URL,
        "HEMOCENTROS_MONGO_DB": TEST_MONGO_DB, "HEMOCENTROS_RABBITMQ_URL": amqp_url,
        "HEMOCENTROS_RABBITMQ_EXCHANGE": f"test.{s}", "HEMOCENTROS_RABBITMQ_QUEUE": f"test.cqrs.{s}",
        "HEMOCENTROS_OUTBOX_WORKER_HABILITADO": "true", "HEMOCENTROS_CONSUMIDOR_HABILITADO": "true",
        "HEMOCENTROS_OUTBOX_LIMPEZA_HABILITADA": "true", "HEMOCENTROS_CONSUMIDOR_RECONEXAO": "0.2", **extra,
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()


def test_processo_worker_projeta_sem_api(pg_engine, mongo_view, amqp_url, monkeypatch):
    """Só o worker rodando: a campanha gravada no PostgreSQL chega ao MongoDB, e o SIGTERM encerra limpo."""
    _ambiente(monkeypatch, amqp_url)

    async def go():
        parada = asyncio.Event()
        tarefa = asyncio.create_task(worker.executar(parada))
        try:
            await asyncio.sleep(1.0)  # conecta ao RabbitMQ e declara a fila
            camp = await criar_campanha(create_session_factory(pg_engine), CampanhaCriar(
                titulo="Via worker", hemocentro="Lavras", tipo_sanguineo="O-",
                data_inicio=date(2026, 11, 10), data_fim=date(2026, 11, 30)))
            for _ in range(50):
                if mongo_view.count_documents({"_id": camp.id}):
                    break
                await asyncio.sleep(0.1)
            projetado = mongo_view.count_documents({"_id": camp.id}) == 1
        finally:
            parada.set()
            await asyncio.wait_for(tarefa, 5)
        return projetado, tarefa.exception()

    try:
        projetado, erro = asyncio.run(go())
    finally:
        get_settings.cache_clear()
    assert projetado and erro is None


def test_api_sem_workers_quando_desabilitado(monkeypatch):
    monkeypatch.setenv("HEMOCENTROS_API_EXECUTA_WORKERS", "false")
    monkeypatch.setenv("HEMOCENTROS_OUTBOX_WORKER_HABILITADO", "true")
    monkeypatch.setenv("HEMOCENTROS_CONSUMIDOR_HABILITADO", "true")
    get_settings.cache_clear()
    try:
        with TestClient(app):
            assert app.state.workers == []
    finally:
        get_settings.cache_clear()


def test_api_com_workers_por_padrao(monkeypatch):
    monkeypatch.setenv("HEMOCENTROS_OUTBOX_WORKER_HABILITADO", "true")
    monkeypatch.setenv("HEMOCENTROS_CONSUMIDOR_RECONEXAO", "0.2")
    get_settings.cache_clear()
    try:
        with TestClient(app):
            assert [t.get_name() for t in app.state.workers] == ["outbox-publicador"]
    finally:
        get_settings.cache_clear()
