"""Consumidor das respostas do passo 3: RabbitMQ (`orquestrador.saga.respostas`) -> transição da SAGA.

Corpo (contratos §2.1): {"sagaId", "agendamentoId", "resultado": "PROGRAMADO" | "FALHOU", "motivo"?, "emitidoEm"}.

- O ack só acontece DEPOIS de gravar a transição. A mensagem entra no inbox (`processed_messages`) na mesma
  transação: reentregas (at-least-once) são reconhecidas e ignoradas.
- Mensagem inválida (JSON, campos, SAGA inexistente ou de outro agendamento): reject sem requeue -> DLQ.
- Erro transitório (banco fora): aguarda e devolve à fila.
- Resposta que chega tarde (SAGA já em compensação por timeout) é registrada e ignorada pela máquina.
- Resposta PROGRAMADO leva a SAGA a CONFIRMING; o passo 4 é disparado na hora (e a recuperação garante).
"""

import asyncio
import json
import logging
import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI

from orquestrador.config import Settings
from orquestrador.messaging.rabbitmq import conectar_consumidor
from orquestrador.observabilidade import request_id_var
from orquestrador.repositories import sagas as repo
from orquestrador.saga.estados import Politica, RespostaComunicacao, StatusSaga
from orquestrador.saga.maquina import transicionar

logger = logging.getLogger(__name__)

_RESULTADOS = {"PROGRAMADO": True, "FALHOU": False}
_TENTATIVAS_CONFLITO = 3


class MensagemInvalida(ValueError):
    pass


def _ler(corpo: bytes) -> tuple[uuid.UUID, str, bool, str]:
    try:
        dados = json.loads(corpo)
    except ValueError as exc:
        raise MensagemInvalida("JSON inválido") from exc
    if not isinstance(dados, dict):
        raise MensagemInvalida("corpo não é um objeto")
    try:
        saga_id = uuid.UUID(str(dados["sagaId"]))
    except (KeyError, ValueError) as exc:
        raise MensagemInvalida("sagaId ausente ou inválido") from exc
    if dados.get("resultado") not in _RESULTADOS:
        raise MensagemInvalida(f"resultado inválido: {dados.get('resultado')!r}")
    return saga_id, str(dados.get("agendamentoId", "")), _RESULTADOS[dados["resultado"]], str(dados.get("motivo") or "")


async def processar_resposta(
    sessoes, politica: Politica, saga_id: uuid.UUID, agendamento_id: str, ok: bool, motivo: str, message_id: str
) -> StatusSaga | None:
    """Aplica a resposta à SAGA. Devolve o novo status (None se a mensagem já tinha sido processada)."""
    for _ in range(_TENTATIVAS_CONFLITO):
        saga = await repo.obter(sessoes, saga_id)
        if saga is None:
            raise MensagemInvalida(f"SAGA {saga_id} inexistente")
        if agendamento_id and agendamento_id != saga.agendamento_id:
            raise MensagemInvalida(f"agendamentoId {agendamento_id} não pertence à SAGA {saga_id}")
        transicao = transicionar(repo.estado_de(saga), RespostaComunicacao(ok=ok, motivo=motivo), politica)
        try:
            atualizada = await repo.aplicar_transicao(
                sessoes, saga, transicao, agora=datetime.now(UTC), mensagem_processada=message_id
            )
        except repo.MensagemDuplicada:
            logger.info("Resposta %s já processada; ignorada", message_id)
            return None
        except repo.ConflitoVersao:
            continue  # a SAGA mudou (ex.: timeout aplicado agora); relê e reavalia
        if transicao.ignorado:
            logger.info("Resposta do passo 3 para a SAGA %s ignorada no status %s", saga_id, saga.status)
        return StatusSaga(atualizada.status)
    raise repo.ConflitoVersao(str(saga_id))


async def tratar_mensagem(
    message,
    sessoes,
    politica: Politica,
    ao_confirmar: Callable[[uuid.UUID], Coroutine[Any, Any, Any]] | None = None,
    espera_erro: float = 2.0,
) -> None:
    token = request_id_var.set(getattr(message, "correlation_id", None))
    try:
        try:
            saga_id, agendamento_id, ok, motivo = _ler(message.body)
            message_id = message.message_id or f"saga-{saga_id}-step3-resposta"
            status = await processar_resposta(sessoes, politica, saga_id, agendamento_id, ok, motivo, message_id)
        except MensagemInvalida as exc:
            logger.error("Resposta inválida descartada para a DLQ (%s): %r", exc, message.body[:200])
            await message.reject(requeue=False)
            return
        except Exception as exc:
            logger.warning("Falha ao processar resposta: %s. Devolvendo à fila.", exc)
            await asyncio.sleep(espera_erro)
            await message.nack(requeue=True)
            return
        await message.ack()
        if status == StatusSaga.CONFIRMING and ao_confirmar is not None:
            await ao_confirmar(saga_id)
    finally:
        request_id_var.reset(token)


async def iniciar_consumo(settings: Settings, sessoes, politica: Politica, ao_confirmar=None):
    """Conecta e começa a consumir. Retorna a conexão (feche-a para parar)."""
    connection, fila = await conectar_consumidor(settings)

    async def callback(message):
        await tratar_mensagem(message, sessoes, politica, ao_confirmar, settings.consumidor_espera_erro)

    await fila.consume(callback, no_ack=False)
    logger.info("Consumidor de respostas ativo na fila %s", settings.fila_respostas)
    return connection


async def executar_consumidor(app: FastAPI) -> None:
    """Mantém o consumidor ativo; reconecta se o RabbitMQ cair. Nunca derruba o serviço."""
    from orquestrador.services.workers import disparar

    settings = app.state.settings

    async def ao_confirmar(saga_id: uuid.UUID) -> None:
        disparar(app, app.state.executor.avancar(saga_id))  # passo 4 já; a recuperação cobre se falhar

    while True:
        connection = None
        try:
            connection = await iniciar_consumo(
                settings, app.state.session_factory, app.state.executor.politica, ao_confirmar
            )
            await asyncio.Event().wait()  # consome até o cancelamento
        except asyncio.CancelledError:
            if connection is not None:
                await connection.close()
            raise
        except Exception as exc:
            logger.warning("Consumidor de respostas: %s. Nova tentativa em %.0fs", exc, settings.consumidor_reconexao)
            if connection is not None:
                await connection.close()
            await asyncio.sleep(settings.consumidor_reconexao)
