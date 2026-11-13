from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BFF_WEB_")

    app_name: str = "bff-web"
    port: int = 8002

    # Autorização por papel (X-User-Roles do Gateway). Desligada até o Gateway injetar o cabeçalho.
    exigir_papel: bool = False
    papel_exigido: str = "operador"

    # URLs dos serviços internos (sobrescritas por variável de ambiente)
    hemocentros_url: str = "http://ms-hemocentros:8000"
    agendamentos_url: str = "http://ms-agendamentos:8082"

    # Timeout das chamadas aos serviços internos, em segundos
    http_timeout: float = 3.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
