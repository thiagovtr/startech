"""Notificações de eventos de domínio (fila `comunicacao.notificacoes`, com DLQ).

- `saga.agendamento.confirmado` / `.compensado`: avisa o doador do desfecho da solicitação de agendamento;
- `hemocentros.campanha.criada`: aviso geral de nova campanha (sem doador específico; só log e histórico).

Idempotência pelo mesmo inbox (`processed_messages`). Mensagem inválida -> reject sem requeue (DLQ).
"""

import asyncio
import json
import logging

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from comunicacao.config import Settings
from comunicacao.models.orm import Notificacao, TipoNotificacao
from comunicacao.observabilidade import request_id_var
from comunicacao.services import canais
from comunicacao.services.inbox import manter_consumidor, registrar_no_inbox

logger = logging.getLogger(__name__)


class EventoInvalido(ValueError):
    pass


def montar_notificacao(routing_key: str, corpo: bytes) -> Notificacao:
    try:
        dados = json.loads(corpo)
    except ValueError as exc:
        raise EventoInvalido("JSON inválido") from exc
    if not isinstance(dados, dict):
        raise EventoInvalido("corpo não é um objeto")
    rid = request_id_var.get()
    if routing_key.startswith("saga.agendamento."):
        if not dados.get("doadorId") or not dados.get("agendamentoId"):
            raise EventoInvalido("doadorId/agendamentoId ausentes")
        confirmado = dados.get("status") == "CONFIRMED"
        texto = (
            "Seu agendamento foi confirmado. Obrigado por doar!" if confirmado
            else "Não foi possível confirmar seu agendamento. Escolha outro horário ou campanha."
        )
        return Notificacao(
            doador_id=str(dados["doadorId"]), agendamento_id=str(dados["agendamentoId"]),
            tipo=TipoNotificacao.DESFECHO, canal=canais.CANAL_PADRAO, conteudo=texto, correlation_id=rid,
        )
    if routing_key == "hemocentros.campanha.criada":
        if not dados.get("titulo"):
            raise EventoInvalido("titulo ausente")
        texto = (
            f"Nova campanha '{dados['titulo']}' em {dados.get('hemocentro', '?')} "
            f"(tipo {dados.get('tipo_sanguineo', '?')}, urgência {dados.get('urgencia', '?')})."
        )
        return Notificacao(tipo=TipoNotificacao.CAMPANHA, canal=canais.CANAL_PADRAO, conteudo=texto, correlation_id=rid)
    raise EventoInvalido(f"routing key não tratada: {routing_key}")


async def processar_evento(
    factory: async_sessionmaker[AsyncSession], routing_key: str, corpo: bytes, message_id: str
) -> bool:
    """Grava a notificação (com inbox) e a "envia". False se o evento já tinha sido processado."""
    notificacao = montar_notificacao(routing_key, corpo)
    async with factory() as session, session.begin():
        if not await registrar_no_inbox(session, message_id):
            return False
        session.add(notificacao)
    canais.enviar(notificacao)
    return True


async def tratar_evento(message, factory: async_sessionmaker[AsyncSession], settings: Settings) -> None:
    token = request_id_var.set(getattr(message, "correlation_id", None))
    try:
        try:
            if not message.message_id:
                raise EventoInvalido("message_id ausente (sem ele não há deduplicação)")
            await processar_evento(factory, message.routing_key or "", message.body, message.message_id)
        except EventoInvalido as exc:
            logger.error("Evento inválido enviado à DLQ (%s): %r", exc, message.body[:200])
            await message.reject(requeue=False)
            return
        except Exception as exc:
            logger.warning("Falha ao processar evento: %s. Devolvendo à fila.", exc)
            await asyncio.sleep(settings.consumidor_espera_erro)
            await message.nack(requeue=True)
            return
        await message.ack()
    finally:
        request_id_var.reset(token)


async def executar_consumidor_notificacoes(app: FastAPI) -> None:
    settings, factory = app.state.settings, app.state.session_factory

    async def callback(message) -> None:
        await tratar_evento(message, factory, settings)

    await manter_consumidor(settings, settings.fila_notificacoes, callback)
