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

    # RabbitMQ (barramento de eventos). Nome da exchange definido no plano; tipo assumido como `topic`.
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    rabbitmq_exchange: str = "startech.events.exchange"
    rabbitmq_exchange_type: str = "topic"  # topic | direct | fanout | headers
    # True: declara a exchange (idempotente, exige mesmo tipo). False: apenas verifica que ela já existe.
    rabbitmq_declarar_exchange: bool = True

    # Consumidor da projeção CQRS (fila e binding; nomes definidos no plano)
    rabbitmq_queue: str = "hemocentros.cqrs"
    rabbitmq_binding_key: str = "hemocentros.campanha.*"
    # True: declara a fila e o binding (idempotente, exige mesmos argumentos). False: só verifica que a fila existe.
    rabbitmq_declarar_fila: bool = True
    consumidor_habilitado: bool = True
    consumidor_prefetch: int = 10
    consumidor_reconexao: float = 5.0  # segundos entre tentativas de conexão ao RabbitMQ
    consumidor_espera_erro: float = 2.0  # segundos antes de devolver à fila uma mensagem que falhou por erro transitório

    # Publicador do Outbox (polling)
    outbox_worker_habilitado: bool = True
    outbox_intervalo: float = 0.5  # segundos entre consultas quando não há eventos pendentes (define o piso da latência)
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
    return Settings()
