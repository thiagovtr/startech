"""Consumidor da projeção CQRS: RabbitMQ (`hemocentros.cqrs`) -> MongoDB (`campanhas_view`)."""

import asyncio
import json
import logging

from fastapi import FastAPI
from pymongo import AsyncMongoClient

from hemocentros.config import Settings
from hemocentros.messaging.rabbitmq import conectar_consumidor
from hemocentros.repositories import campanhas_view_escrita

logger = logging.getLogger(__name__)


async def tratar_mensagem(message, mongo: AsyncMongoClient, db_name: str, espera_erro: float = 2.0) -> None:
    """Projeta um evento. O ack só acontece DEPOIS de gravar no MongoDB.

    - sucesso: ack;
    - mensagem inválida (JSON/estrutura): reject sem requeue (reentregar não resolveria);
    - erro transitório (ex.: MongoDB fora): aguarda e devolve à fila (nack com requeue).
    """
    try:
        payload = json.loads(message.body)
        if not isinstance(payload, dict) or "id" not in payload:
            raise ValueError("payload sem 'id'")
    except ValueError as exc:
        logger.error("Mensagem inválida descartada (%s): %r", exc, message.body[:200])
        await message.reject(requeue=False)
        return
    try:
        await campanhas_view_escrita.upsert(mongo, db_name, payload)
    except Exception as exc:
        logger.warning("Falha ao projetar campanha %s: %s. Devolvendo à fila.", payload["id"], exc)
        await asyncio.sleep(espera_erro)
        await message.nack(requeue=True)
        return
    await message.ack()


async def iniciar_consumo(settings: Settings, mongo: AsyncMongoClient):
    """Conecta e começa a consumir. Retorna a conexão (feche-a para parar)."""
    connection, queue = await conectar_consumidor(settings)

    async def callback(message):
        await tratar_mensagem(message, mongo, settings.mongo_db, settings.consumidor_espera_erro)

    await queue.consume(callback, no_ack=False)
    logger.info("Consumidor da projeção ativo na fila %s", settings.rabbitmq_queue)
    return connection


async def executar_consumidor(app: FastAPI) -> None:
    """Mantém o consumidor ativo; tenta reconectar se o RabbitMQ estiver indisponível. Nunca derruba o serviço."""
    settings = app.state.settings
    while True:
        connection = None
        try:
            connection = await iniciar_consumo(settings, app.state.mongo_client)
            await asyncio.Event().wait()  # consome até o cancelamento
        except asyncio.CancelledError:
            if connection is not None:
                await connection.close()
            raise
        except Exception as exc:
            logger.warning("Consumidor da projeção: %s. Nova tentativa em %.0fs", exc, settings.consumidor_reconexao)
            if connection is not None:
                await connection.close()
            await asyncio.sleep(settings.consumidor_reconexao)
