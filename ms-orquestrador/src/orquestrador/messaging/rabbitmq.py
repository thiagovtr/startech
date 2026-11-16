"""Conexão com o RabbitMQ e topologia da SAGA (contratos §2.1, "Topologia").

Sem arquivo central de definições: cada serviço declara, de forma idempotente, o que usa. O orquestrador
declara a exchange, a fila de respostas (com DLQ), a DLQ de compensações e também a fila de comandos do
ms-comunicacao, para que nenhum comando seja descartado pela exchange topic enquanto ele não existir.
"""

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractQueue, AbstractRobustConnection

from orquestrador.config import Settings


async def _exchange(channel: AbstractChannel, settings: Settings) -> AbstractExchange:
    if settings.rabbitmq_declarar_exchange:
        return await channel.declare_exchange(
            settings.rabbitmq_exchange, aio_pika.ExchangeType(settings.rabbitmq_exchange_type), durable=True
        )
    return await channel.get_exchange(settings.rabbitmq_exchange, ensure=True)


async def declarar_topologia(channel: AbstractChannel, exchange: AbstractExchange, settings: Settings) -> AbstractQueue:
    """Declara filas e bindings da SAGA e devolve a fila de respostas."""
    dlx = await channel.declare_exchange(settings.rabbitmq_dlx_exchange, aio_pika.ExchangeType.DIRECT, durable=True)
    dlq = await channel.declare_queue(settings.fila_respostas_dlq, durable=True)
    await dlq.bind(dlx, routing_key=settings.routing_key_respostas_dlq)
    respostas = await channel.declare_queue(
        settings.fila_respostas, durable=True,
        arguments={
            "x-dead-letter-exchange": settings.rabbitmq_dlx_exchange,
            "x-dead-letter-routing-key": settings.routing_key_respostas_dlq,
        },
    )
    await respostas.bind(exchange, routing_key=settings.binding_respostas)

    comandos = await channel.declare_queue(settings.fila_comandos_comunicacao, durable=True)  # sem argumentos
    await comandos.bind(exchange, routing_key=settings.binding_comandos_comunicacao)

    compensacoes = await channel.declare_queue(settings.fila_compensacoes_dlq, durable=True)
    await compensacoes.bind(exchange, routing_key=settings.binding_compensacoes_dlq)
    return respostas


async def conectar(settings: Settings) -> tuple[AbstractRobustConnection, AbstractExchange]:
    """Conecta, garante a topologia e devolve a exchange de eventos (publisher confirms, padrão do aio-pika)."""
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        exchange = await _exchange(channel, settings)
        if settings.rabbitmq_declarar_filas:
            await declarar_topologia(channel, exchange, settings)
    except Exception:
        await connection.close()
        raise
    return connection, exchange


async def conectar_consumidor(settings: Settings) -> tuple[AbstractRobustConnection, AbstractQueue]:
    """Conecta, garante a topologia e devolve (connection, fila de respostas) com prefetch configurado."""
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=settings.consumidor_prefetch)
        exchange = await _exchange(channel, settings)
        if settings.rabbitmq_declarar_filas:
            fila = await declarar_topologia(channel, exchange, settings)
        else:
            fila = await channel.get_queue(settings.fila_respostas, ensure=True)
    except Exception:
        await connection.close()
        raise
    return connection, fila
