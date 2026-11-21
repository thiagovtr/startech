from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BFF_MOBILE_")

    app_name: str = "bff-mobile"
    port: int = 8001

    # Autorização por papel (X-User-Roles do Gateway). Desligada até o Gateway injetar o cabeçalho.
    exigir_papel: bool = False
    papel_exigido: str = "doador"

    # URLs dos serviços internos (sobrescritas por variável de ambiente)
    doadores_url: str = "http://ms-doadores:8081"
    hemocentros_url: str = "http://ms-hemocentros:8000"
    agendamentos_url: str = "http://ms-agendamentos:8082"
    orquestrador_url: str = "http://ms-orquestrador:8003"
    rag_url: str = "http://ms-rag:8005"

    # Timeouts das chamadas aos serviços internos, em segundos
    http_timeout: float = 3.0  # ms-hemocentros
    doadores_timeout: float = 0.8  # ms-doadores (valor do ADR; falha rápida para degradar)
    orquestrador_timeout: float = 3.0  # ms-orquestrador (só grava a SAGA e responde 202)
    agendamentos_timeout: float = 3.0  # ms-agendamentos (consulta e cancelamento de agendamento)
    # ms-rag: busca (1,5 s) + LLM (4 s) no pior caso; abaixo dos 6 s do Gateway. O ms-rag já degrada sozinho.
    rag_timeout: float = 5.8

    # Prefixo público das rotas do BFF (o Gateway reescreve /api/mobile/** para /bff-mobile/**): usado nos links
    # devolvidos ao app, para que apontem para o Gateway e não para o endereço interno do BFF.
    prefixo_publico: str = "/api/mobile"

    # Tipo sanguíneo usado quando o perfil não traz o tipo (ou ms-doadores está fora).
    # Padrão vazio = sem filtro: mostra todas as campanhas vigentes (decisão P10). Um tipo fixo, como O-,
    # pediria a um doador de tipo desconhecido uma doação que ele provavelmente não pode fazer.
    tipo_sanguineo_fallback: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
