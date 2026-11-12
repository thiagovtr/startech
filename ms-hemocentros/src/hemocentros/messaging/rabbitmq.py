import aio_pika
from aio_pika.abc import AbstractExchange, AbstractRobustConnection

from hemocentros.config import Settings


async def conectar(settings: Settings) -> tuple[AbstractRobustConnection, AbstractExchange]:
    """Conecta ao RabbitMQ e obtém a exchange de eventos (com publisher confirms, padrão do aio-pika)."""
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        if settings.rabbitmq_declarar_exchange:
            exchange = await channel.declare_exchange(
                settings.rabbitmq_exchange,
                aio_pika.ExchangeType(settings.rabbitmq_exchange_type),
                durable=True,
            )
        else:
            exchange = await channel.get_exchange(settings.rabbitmq_exchange, ensure=True)
    except Exception:
        await connection.close()
        raise
    return connection, exchange
