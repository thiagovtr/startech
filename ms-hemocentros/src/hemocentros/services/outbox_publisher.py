"""Publicador do Transactional Outbox (Polling Publisher), conforme ADR-003."""

import asyncio
import json
import logging

import aio_pika
from aio_pika.abc import AbstractExchange
from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hemocentros.messaging.rabbitmq import conectar
from hemocentros.models.orm import OutboxEvent

logger = logging.getLogger(__name__)


async def publicar_pendentes(
    factory: async_sessionmaker[AsyncSession], exchange: AbstractExchange, lote: int = 50
) -> int:
    """Publica até `lote` eventos pendentes, em ordem de criação, e os marca como publicados.

    `FOR UPDATE SKIP LOCKED` permite workers concorrentes sem publicar o mesmo evento duas vezes.
    Se a publicação falhar no meio do lote, os eventos já confirmados pelo broker são mantidos como
    publicados (commit) e o erro é relançado; os demais continuam pendentes (entrega at-least-once,
    o consumidor deve ser idempotente — o `message_id` é o id do evento).
    """
    publicados = 0
    erro: Exception | None = None
    async with factory() as session, session.begin():
        eventos = (
            await session.scalars(
                select(OutboxEvent)
                .where(OutboxEvent.published.is_(False))
                .order_by(OutboxEvent.created_at)
                .limit(lote)
                .with_for_update(skip_locked=True)
            )
        ).all()
        for evento in eventos:
            mensagem = aio_pika.Message(
                body=json.dumps(evento.payload).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                message_id=evento.id,
                correlation_id=evento.correlation_id,
            )
            try:
                await exchange.publish(mensagem, routing_key=evento.routing_key)  # aguarda o confirm do broker
            except Exception as exc:
                erro = exc
                break
            evento.published = True
            evento.published_at = func.now()
            publicados += 1
    if erro is not None:
        raise erro
    return publicados


async def executar_publicador(app: FastAPI) -> None:
    """Laço do worker: mantém a conexão com o RabbitMQ e publica o Outbox. Nunca derruba o serviço."""
    settings = app.state.settings
    connection = None
    while True:
        try:
            if connection is None:
                connection, exchange = await conectar(settings)
                logger.info("Publicador do Outbox conectado ao RabbitMQ (%s)", settings.rabbitmq_exchange)
            n = await publicar_pendentes(app.state.session_factory, exchange, settings.outbox_lote)
            if n == 0:
                await asyncio.sleep(settings.outbox_intervalo)
        except asyncio.CancelledError:
            if connection is not None:
                await connection.close()
            raise
        except Exception as exc:
            logger.warning("Publicador do Outbox: %s. Nova tentativa em %.0fs", exc, settings.outbox_intervalo * 3)
            if connection is not None and connection.is_closed:
                connection = None
            await asyncio.sleep(settings.outbox_intervalo * 3)
