import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

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
