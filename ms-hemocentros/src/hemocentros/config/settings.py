from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HEMOCENTROS_")

    app_name: str = "ms-hemocentros"
    port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
