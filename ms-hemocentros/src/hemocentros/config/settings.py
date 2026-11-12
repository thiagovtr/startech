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

    # Publicador do Outbox (polling)
    outbox_worker_habilitado: bool = True
    outbox_intervalo: float = 1.0  # segundos entre consultas quando não há eventos pendentes
    outbox_lote: int = 50

    # Tempo máximo, em segundos, para checar a conectividade de cada banco
    db_check_timeout: float = 2.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
