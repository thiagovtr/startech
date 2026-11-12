from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BFF_MOBILE_")

    app_name: str = "bff-mobile"
    port: int = 8001

    # URLs dos serviços internos (sobrescritas por variável de ambiente)
    doadores_url: str = "http://ms-doadores:8081"
    hemocentros_url: str = "http://ms-hemocentros:8000"
    agendamentos_url: str = "http://ms-agendamentos:8082"

    # Timeout das chamadas aos serviços internos, em segundos
    http_timeout: float = 3.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
