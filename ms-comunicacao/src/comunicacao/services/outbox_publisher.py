"""Publicador do Transactional Outbox (Polling Publisher), conforme ADR-003.

Publica as respostas do passo 3 da SAGA (`comunicacao.lembrete.*`) com as propriedades AMQP de contratos §2.1:
`message_id` (chave de deduplicação no consumidor), `correlation_id`, `content_type` JSON e entrega persistente.
"""

import asyncio
import json
import logging

import aio_pika
from aio_pika.abc import AbstractExchange
from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from comunicacao.messaging.rabbitmq import conectar
from comunicacao.models.orm import OutboxEvent

logger = logging.getLogger(__name__)


def mensagem_de(evento: OutboxEvent) -> aio_pika.Message:
    return aio_pika.Message(
        body=json.dumps(evento.payload, ensure_ascii=False).encode(),
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        message_id=evento.message_id,
        correlation_id=evento.correlation_id,
        type=evento.routing_key,
        app_id="ms-comunicacao",
    )


async def publicar_pendentes(
    factory: async_sessionmaker[AsyncSession], exchange: AbstractExchange, lote: int = 50
) -> int:
    """Publica até `lote` mensagens pendentes, em ordem de criação, e as marca como publicadas.

    `FOR UPDATE SKIP LOCKED` permite publicadores concorrentes sem publicar a mesma mensagem duas vezes.
    Se a publicação falhar no meio do lote, as já confirmadas pelo broker ficam marcadas (commit) e o erro
    é relançado; as demais seguem pendentes (entrega at-least-once; o consumidor deduplica por message_id).
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
            try:
                await exchange.publish(mensagem_de(evento), routing_key=evento.routing_key)  # aguarda o confirm
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
    """Laço do worker: mantém a conexão com o RabbitMQ e publica o Outbox. Nunca derruba o serviço.

    Com o RabbitMQ fora, as respostas ficam pendentes até ele voltar.
    """
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
            logger.warning("Publicador do Outbox: %s. Nova tentativa em %.1fs", exc, settings.outbox_intervalo * 10)
            if connection is not None and connection.is_closed:
                connection = None
            await asyncio.sleep(settings.outbox_intervalo * 10)
