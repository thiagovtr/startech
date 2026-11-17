"""Inbox idempotente e laço genérico de consumo do RabbitMQ (reconexão, ack/nack, correlation id)."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from comunicacao.config import Settings
from comunicacao.messaging.rabbitmq import conectar_consumidor
from comunicacao.models.orm import MensagemProcessada

logger = logging.getLogger(__name__)


async def registrar_no_inbox(session: AsyncSession, message_id: str) -> bool:
    """Registra o message_id na transação corrente. False se ele já tinha sido processado (reentrega)."""
    resultado = await session.execute(
        insert(MensagemProcessada).values(message_id=message_id).on_conflict_do_nothing().returning(
            MensagemProcessada.message_id
        )
    )
    return resultado.scalar_one_or_none() is not None


async def manter_consumidor(
    settings: Settings, fila: str, callback: Callable[..., Awaitable[None]]
) -> None:
    """Mantém um consumidor ativo na `fila`; reconecta se o RabbitMQ cair. Nunca derruba o serviço."""
    while True:
        connection = None
        try:
            connection, queue = await conectar_consumidor(settings, fila)
            await queue.consume(callback, no_ack=False)
            logger.info("Consumidor ativo na fila %s", fila)
            await asyncio.Event().wait()  # consome até o cancelamento
        except asyncio.CancelledError:
            if connection is not None:
                await connection.close()
            raise
        except Exception as exc:
            logger.warning(
                "Consumidor da fila %s: %s. Nova tentativa em %.0fs", fila, exc, settings.consumidor_reconexao
            )
            if connection is not None:
                await connection.close()
            await asyncio.sleep(settings.consumidor_reconexao)
