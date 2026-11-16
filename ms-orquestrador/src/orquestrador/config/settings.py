from functools import lru_cache

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ORQUESTRADOR_")

    app_name: str = "ms-orquestrador"
    port: int = 8003

    # Credenciais NÃO têm valor padrão no código: vêm do ambiente (.env no Compose, Secret no Kubernetes).
    # Sem elas o serviço não sobe (falha rápida, em vez de rodar silenciosamente com senha conhecida).

    # PostgreSQL próprio (estado da SAGA, log de passos, Outbox) - URL SQLAlchemy com driver asyncpg
    postgres_url: str

    # RabbitMQ (comandos do passo 3 via Outbox e respostas do ms-comunicacao) - URL AMQP com usuário e senha
    rabbitmq_url: str
    rabbitmq_exchange: str = "startech.events.exchange"
    rabbitmq_exchange_type: str = "topic"
    # True: declara a exchange (idempotente, exige mesmo tipo). False: apenas verifica que ela já existe.
    rabbitmq_declarar_exchange: bool = True

    # Participantes síncronos da SAGA (passos 1, 2 e 4)
    agendamentos_url: str = "http://ms-agendamentos:8082"
    doadores_url: str = "http://ms-doadores:8081"
    http_timeout: float = 3.0  # segundos por chamada a um participante

    # Retentativas (ADR-002 §5.3): espera = 2^tentativa * backoff_base_ms (+ jitter), até max_retries
    max_retries: int = 5
    backoff_base_ms: int = 500

    # Passo 3 (ms-comunicacao). True: aguarda a resposta `comunicacao.lembrete.*` até `timeout_passo3` segundos.
    # False: o passo 3 conta como concluído quando o comando é publicado pelo Outbox (enquanto o
    # ms-comunicacao não existir; ver contratos §2.1 e .claude/notes/execucao-ms-orquestrador.md Q4).
    passo3_aguardar_resposta: bool = True
    timeout_passo3: float = 30.0

    # False: a API não roda nenhum worker (publicador do Outbox, consumidor de respostas, recuperação).
    api_executa_workers: bool = True

    # Tempo máximo, em segundos, para checar a conectividade do banco
    db_check_timeout: float = 2.0


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        prefixo = Settings.model_config["env_prefix"]
        faltando = [f"{prefixo}{e['loc'][0]}".upper() for e in exc.errors() if e["type"] == "missing"]
        if not faltando:
            raise
        raise RuntimeError(
            "Configuração obrigatória ausente: defina as variáveis de ambiente " + ", ".join(faltando)
            + " (Compose: arquivo .env, ver .env.example; Kubernetes: Secret)."
        ) from None
