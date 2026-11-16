import asyncio
import os

import pytest
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

# As credenciais não têm padrão no código; os testes que sobem o app sem se importar com elas usam
# endereços inalcançáveis (os que precisam de serviços reais sobrescrevem estas variáveis).
os.environ.setdefault("ORQUESTRADOR_POSTGRES_URL", "postgresql+asyncpg://teste:teste@127.0.0.1:1/teste")
os.environ.setdefault("ORQUESTRADOR_RABBITMQ_URL", "amqp://teste:teste@127.0.0.1:1/")
# Os testes do app não iniciam os workers (eles são testados diretamente).
os.environ.setdefault("ORQUESTRADOR_API_EXECUTA_WORKERS", "false")

# Banco próprio dos testes, no mesmo servidor PostgreSQL usado pelos testes do ms-hemocentros (CI e
# scripts/test-docker.sh). Um banco separado evita colisão de tabelas e da `alembic_version` entre os serviços.
TEST_PG_URL = os.getenv(
    "ORQUESTRADOR_TEST_POSTGRES_URL",
    "postgresql+asyncpg://hemocentros:hemocentros@127.0.0.1:15432/orquestrador_test",
)


async def _garantir_banco(url: str) -> None:
    """Cria o banco de teste se ele ainda não existir (o usuário do container de teste é superusuário)."""
    alvo = make_url(url)
    admin = create_async_engine(
        alvo.set(database="postgres"), isolation_level="AUTOCOMMIT", poolclass=NullPool,
        connect_args={"timeout": 2},
    )
    try:
        async with admin.connect() as conn:
            existe = await conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": alvo.database})
            if not existe:
                await conn.execute(text(f'CREATE DATABASE "{alvo.database}"'))
    finally:
        await admin.dispose()


TABELAS = ("saga_execution_state", "saga_step_log", "outbox_events", "processed_messages")


@pytest.fixture
def pg_engine():
    """Engine para um PostgreSQL real, migrado e com as tabelas vazias; ignora o teste se indisponível."""
    # sem pool: cada asyncio.run usa um loop novo
    engine = create_async_engine(TEST_PG_URL, connect_args={"timeout": 2}, poolclass=NullPool)

    async def _prepare():
        from orquestrador.db.postgres import criar_esquema

        await _garantir_banco(TEST_PG_URL)
        await criar_esquema(engine)
        async with engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {', '.join(TABELAS)} CASCADE"))

    try:
        asyncio.run(_prepare())
    except Exception:
        pytest.skip(f"PostgreSQL de teste indisponível em {TEST_PG_URL}")
    yield engine
    asyncio.run(engine.dispose())
