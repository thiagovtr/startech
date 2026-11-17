"""Conexão com o RabbitMQ e topologia do ms-comunicacao (contratos §2.1, "Topologia").

Cada serviço declara, de forma idempotente, o que usa:
- `comunicacao.saga.comandos` (binding `saga.comando.comunicacao.*`): também declarada pelo ms-orquestrador,
  por isso é durável e SEM argumentos extras (o RabbitMQ recusa redeclaração divergente). Não tem DLQ:
  comandos ilegíveis vão para a tabela `mensagens_rejeitadas`.
- `comunicacao.notificacoes` (desfecho da SAGA e novas campanhas): fila só nossa, com DLQ em `startech.events.dlx`.
"""

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractQueue, AbstractRobustConnection

from comunicacao.config import Settings


async def _exchange(channel: AbstractChannel, settings: Settings) -> AbstractExchange:
    if settings.rabbitmq_declarar_exchange:
        return await channel.declare_exchange(
            settings.rabbitmq_exchange, aio_pika.ExchangeType(settings.rabbitmq_exchange_type), durable=True
        )
    return await channel.get_exchange(settings.rabbitmq_exchange, ensure=True)


async def declarar_fila_comandos(
    channel: AbstractChannel, exchange: AbstractExchange, settings: Settings
) -> AbstractQueue:
    fila = await channel.declare_queue(settings.fila_comandos, durable=True)  # sem argumentos (contratos §2.1)
    await fila.bind(exchange, routing_key=settings.binding_comandos)
    return fila


async def declarar_fila_notificacoes(
    channel: AbstractChannel, exchange: AbstractExchange, settings: Settings
) -> AbstractQueue:
    dlx = await channel.declare_exchange(settings.rabbitmq_dlx_exchange, aio_pika.ExchangeType.DIRECT, durable=True)
    dlq = await channel.declare_queue(settings.fila_notificacoes_dlq, durable=True)
    await dlq.bind(dlx, routing_key=settings.routing_key_notificacoes_dlq)
    fila = await channel.declare_queue(
        settings.fila_notificacoes, durable=True,
        arguments={
            "x-dead-letter-exchange": settings.rabbitmq_dlx_exchange,
            "x-dead-letter-routing-key": settings.routing_key_notificacoes_dlq,
        },
    )
    for binding in settings.lista_bindings_notificacoes:
        await fila.bind(exchange, routing_key=binding)
    return fila


async def conectar(settings: Settings) -> tuple[AbstractRobustConnection, AbstractExchange]:
    """Conecta e devolve a exchange de eventos (publisher confirms, padrão do aio-pika). Usado pelo Outbox."""
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        exchange = await _exchange(channel, settings)
    except Exception:
        await connection.close()
        raise
    return connection, exchange


async def conectar_consumidor(settings: Settings, fila: str) -> tuple[AbstractRobustConnection, AbstractQueue]:
    """Conecta, garante a topologia da `fila` (comandos ou notificações) e a devolve com prefetch configurado."""
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=settings.consumidor_prefetch)
        exchange = await _exchange(channel, settings)
        if not settings.rabbitmq_declarar_filas:
            queue = await channel.get_queue(fila, ensure=True)
        elif fila == settings.fila_comandos:
            queue = await declarar_fila_comandos(channel, exchange, settings)
        else:
            queue = await declarar_fila_notificacoes(channel, exchange, settings)
    except Exception:
        await connection.close()
        raise
    return connection, queue
