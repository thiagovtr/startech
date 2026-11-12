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

    # Timeouts das chamadas aos serviços internos, em segundos
    http_timeout: float = 3.0  # ms-hemocentros
    doadores_timeout: float = 0.8  # ms-doadores (valor do ADR; falha rápida para degradar)

    # Tipo sanguíneo usado para filtrar campanhas quando o perfil do doador não pôde ser obtido
    # (fallback do ADR). Vazio = sem filtro.
    tipo_sanguineo_fallback: str = "O-"


@lru_cache
def get_settings() -> Settings:
    return Settings()
