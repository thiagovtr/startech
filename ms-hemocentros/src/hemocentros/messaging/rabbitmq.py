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


async def _declarar_dlq(channel, settings: Settings) -> dict:
    """Declara a DLX (direct) e a DLQ e devolve os argumentos que ligam a fila principal a elas."""
    dlx = await channel.declare_exchange(settings.rabbitmq_dlx_exchange, aio_pika.ExchangeType.DIRECT, durable=True)
    dlq = await channel.declare_queue(settings.rabbitmq_dlq_queue, durable=True)
    await dlq.bind(dlx, routing_key=settings.rabbitmq_dlq_routing_key)
    return {
        "x-dead-letter-exchange": settings.rabbitmq_dlx_exchange,
        "x-dead-letter-routing-key": settings.rabbitmq_dlq_routing_key,
    }


async def conectar_consumidor(settings: Settings):
    """Conecta, garante exchange/fila/binding e devolve (connection, queue) com prefetch configurado."""
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=settings.consumidor_prefetch)
        if settings.rabbitmq_declarar_fila:
            exchange = await channel.declare_exchange(
                settings.rabbitmq_exchange, aio_pika.ExchangeType(settings.rabbitmq_exchange_type), durable=True
            ) if settings.rabbitmq_declarar_exchange else await channel.get_exchange(settings.rabbitmq_exchange)
            argumentos = await _declarar_dlq(channel, settings) if settings.rabbitmq_dlq_habilitada else None
            queue = await channel.declare_queue(settings.rabbitmq_queue, durable=True, arguments=argumentos)
            await queue.bind(exchange, routing_key=settings.rabbitmq_binding_key)
        else:
            queue = await channel.get_queue(settings.rabbitmq_queue, ensure=True)
    except Exception:
        await connection.close()
        raise
    return connection, queue
