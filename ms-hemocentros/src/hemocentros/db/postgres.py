from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from hemocentros.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    # Conexão preguiçosa: criar o engine não exige o banco disponível.
    return create_async_engine(
        settings.postgres_url,
        pool_pre_ping=True,
        connect_args={"timeout": settings.db_check_timeout},
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def criar_esquema(engine: AsyncEngine) -> None:
    """Aplica as migrações do Alembic até a última revisão (idempotente)."""
    from hemocentros.db.migracoes import aplicar_migracoes

    await aplicar_migracoes(engine)
