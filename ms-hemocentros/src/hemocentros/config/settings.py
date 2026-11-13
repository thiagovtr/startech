from functools import lru_cache

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HEMOCENTROS_")

    app_name: str = "ms-hemocentros"
    port: int = 8000

    # Credenciais NÃO têm valor padrão no código: vêm do ambiente (.env no Compose, Secret no Kubernetes).
    # Sem elas o serviço não sobe (falha rápida, em vez de rodar silenciosamente com senha conhecida).

    # PostgreSQL (modelo de escrita) - URL SQLAlchemy com driver assíncrono (postgresql+asyncpg), usuário e senha
    postgres_url: str

    # MongoDB (modelo de leitura / view CQRS)
    mongo_url: str = "mongodb://mongo:27017"
    mongo_db: str = "hemocentros"

    # RabbitMQ (barramento de eventos). Nome da exchange definido no plano; tipo assumido como `topic`.
    # URL AMQP (amqp://...) com usuário e senha
    rabbitmq_url: str
    rabbitmq_exchange: str = "startech.events.exchange"
    rabbitmq_exchange_type: str = "topic"  # topic | direct | fanout | headers
    # True: declara a exchange (idempotente, exige mesmo tipo). False: apenas verifica que ela já existe.
    rabbitmq_declarar_exchange: bool = True

    # Consumidor da projeção CQRS (fila e binding; nomes definidos no plano)
    rabbitmq_queue: str = "hemocentros.cqrs"
    rabbitmq_binding_key: str = "hemocentros.campanha.*"
    # True: declara a fila e o binding (idempotente, exige mesmos argumentos). False: só verifica que a fila existe.
    rabbitmq_declarar_fila: bool = True
    # Dead-letter (mensagens inválidas, rejeitadas sem requeue). Desligado por padrão: argumentos de fila
    # não podem mudar numa fila já existente (PRECONDITION_FAILED). Ver antigravity/docs/dlq-rabbitmq-para-dev1.md.
    rabbitmq_dlq_habilitada: bool = False
    rabbitmq_dlx_exchange: str = "startech.events.dlx"
    rabbitmq_dlq_queue: str = "hemocentros.cqrs.dlq"
    rabbitmq_dlq_routing_key: str = "hemocentros.cqrs.dead"
    consumidor_habilitado: bool = True
    consumidor_prefetch: int = 10
    consumidor_reconexao: float = 5.0  # segundos entre tentativas de conexão ao RabbitMQ
    # segundos antes de devolver à fila uma mensagem que falhou por erro transitório
    consumidor_espera_erro: float = 2.0

    # Publicador do Outbox (polling)
    outbox_worker_habilitado: bool = True
    # segundos entre consultas quando não há eventos pendentes (define o piso da latência)
    outbox_intervalo: float = 0.5
    outbox_lote: int = 50
    # Retenção: eventos já publicados são removidos após `outbox_retencao_dias` (os pendentes nunca são)
    outbox_limpeza_habilitada: bool = True
    outbox_retencao_dias: float = 7.0
    outbox_limpeza_intervalo: float = 3600.0  # segundos entre execuções da limpeza
    outbox_limpeza_lote: int = 1000

    # Tempo máximo, em segundos, para checar a conectividade de cada banco
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
