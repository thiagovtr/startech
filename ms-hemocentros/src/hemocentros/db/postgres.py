from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from hemocentros.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    # Conexão preguiçosa: criar o engine não exige o banco disponível.
    return create_async_engine(
        settings.postgres_url,
        pool_pre_ping=True,
        connect_args={"timeout": settings.db_check_timeout},
    )
