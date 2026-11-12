from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HEMOCENTROS_")

    app_name: str = "ms-hemocentros"
    port: int = 8000

    # PostgreSQL (modelo de escrita) - driver assíncrono asyncpg
    postgres_url: str = "postgresql+asyncpg://hemocentros:hemocentros@db-hemocentros:5432/hemocentros"

    # MongoDB (modelo de leitura / view CQRS)
    mongo_url: str = "mongodb://mongo:27017"
    mongo_db: str = "hemocentros"

    # Tempo máximo, em segundos, para checar a conectividade de cada banco
    db_check_timeout: float = 2.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
