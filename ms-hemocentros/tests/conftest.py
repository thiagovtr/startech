import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

# Os testes do app não devem iniciar o publicador do Outbox (ele é testado diretamente).
os.environ.setdefault("HEMOCENTROS_OUTBOX_WORKER_HABILITADO", "false")
os.environ.setdefault("HEMOCENTROS_CONSUMIDOR_HABILITADO", "false")
os.environ.setdefault("HEMOCENTROS_OUTBOX_LIMPEZA_HABILITADA", "false")

TEST_PG_URL = os.getenv(
    "HEMOCENTROS_TEST_POSTGRES_URL",
    "postgresql+asyncpg://hemocentros:hemocentros@127.0.0.1:15432/hemocentros",
)


@pytest.fixture
def pg_engine():
    """Engine para um PostgreSQL real; os testes são ignorados se ele não estiver disponível."""
    from hemocentros.db.postgres import criar_esquema

    engine = create_async_engine(TEST_PG_URL, connect_args={"timeout": 2}, poolclass=NullPool)  # sem pool: cada asyncio.run usa um loop novo

    async def _prepare():
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        await criar_esquema(engine)
        async with engine.begin() as conn:
            await conn.execute(text("TRUNCATE campanhas, outbox_events"))

    try:
        asyncio.run(_prepare())
    except Exception:
        pytest.skip(f"PostgreSQL de teste indisponível em {TEST_PG_URL}")
    yield engine
    asyncio.run(engine.dispose())


TEST_MONGO_URL = os.getenv("HEMOCENTROS_TEST_MONGO_URL", "mongodb://127.0.0.1:17017")
TEST_MONGO_DB = "hemocentros_test"


@pytest.fixture
def mongo_view():
    """Coleção campanhas_view limpa num MongoDB real; ignora o teste se indisponível."""
    from pymongo import MongoClient

    client = MongoClient(TEST_MONGO_URL, serverSelectionTimeoutMS=1500)
    try:
        client.admin.command("ping")
    except Exception:
        pytest.skip(f"MongoDB de teste indisponível em {TEST_MONGO_URL}")
    colecao = client[TEST_MONGO_DB]["campanhas_view"]
    colecao.delete_many({})
    yield colecao
    client.drop_database(TEST_MONGO_DB)
    client.close()


TEST_AMQP_URL = os.getenv("HEMOCENTROS_TEST_RABBITMQ_URL", "amqp://guest:guest@127.0.0.1:15672/")


@pytest.fixture
def amqp_url():
    """URL de um RabbitMQ real; ignora o teste se indisponível."""
    import aio_pika

    async def _ping():
        conn = await aio_pika.connect(TEST_AMQP_URL, timeout=2)
        await conn.close()

    try:
        asyncio.run(_ping())
    except Exception:
        pytest.skip(f"RabbitMQ de teste indisponível em {TEST_AMQP_URL}")
    return TEST_AMQP_URL
