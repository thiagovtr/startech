"""Passo 3 da SAGA de agendamento: consumo dos comandos do ms-orquestrador (contratos §2.1, ADR-006).

- `ProgramarLembreteEConfirmar` (`saga.comando.comunicacao.programar-lembrete`): numa ÚNICA transação registra o
  message_id no inbox, programa o lembrete D-1, grava a confirmação no histórico e grava no Outbox a resposta
  `comunicacao.lembrete.programado` (ou `.falhou`). Sem dual write: a resposta só sai se tudo persistiu.
- `CancelarLembreteAgendado` (`...cancelar-lembrete`): compensação; cancela o lembrete (idempotente, inclusive
  se ele não existir: grava um lembrete já CANCELADO para que um `programar` atrasado não o reative). Sem resposta.

Erros:
- Comando de programar legível mas inválido (sem dataHoraInicio, data no passado): responde FALHOU, e a SAGA
  compensa na hora em vez de esperar o timeout do passo 3.
- Comando ilegível (JSON quebrado, sem sagaId/agendamentoId): a fila não tem DLQ (é declarada sem argumentos
  também pelo orquestrador), então vai para a tabela `mensagens_rejeitadas` e recebe ack.
- Erro transitório (banco fora): espera e devolve à fila (nack com requeue).
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from comunicacao.config import Settings
from comunicacao.models.orm import (
    Lembrete,
    MensagemRejeitada,
    Notificacao,
    OutboxEvent,
    StatusLembrete,
    TipoNotificacao,
)
from comunicacao.observabilidade import request_id_var
from comunicacao.services import canais
from comunicacao.services.inbox import manter_consumidor, registrar_no_inbox

logger = logging.getLogger(__name__)

PROGRAMAR = "ProgramarLembreteEConfirmar"
CANCELAR = "CancelarLembreteAgendado"


class ComandoIlegivel(ValueError):
    """Comando que não dá para associar a uma SAGA: não há a quem responder."""


@dataclass(frozen=True)
class Comando:
    tipo: str
    saga_id: str
    agendamento_id: str
    doador_id: str
    slot_id: str | None
    data_hora_inicio: str | None


@dataclass(frozen=True)
class Resultado:
    """O que o processamento fez (para log e testes)."""

    acao: str  # PROGRAMADO | FALHOU | CANCELADO | DUPLICADO
    motivo: str | None = None


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def ler_comando(corpo: bytes, routing_key: str | None, settings: Settings) -> Comando:
    try:
        dados = json.loads(corpo)
    except ValueError as exc:
        raise ComandoIlegivel("JSON inválido") from exc
    if not isinstance(dados, dict):
        raise ComandoIlegivel("corpo não é um objeto")
    tipo = dados.get("tipo")
    if tipo not in (PROGRAMAR, CANCELAR):  # o corpo manda; a routing key é o plano B
        tipo = {settings.routing_key_programar: PROGRAMAR, settings.routing_key_cancelar: CANCELAR}.get(
            routing_key or ""
        )
    if tipo is None:
        raise ComandoIlegivel(f"tipo de comando desconhecido: {dados.get('tipo')!r}")
    campos = {}
    for campo in ("sagaId", "agendamentoId"):
        valor = dados.get(campo)
        if not isinstance(valor, str) or not valor:
            raise ComandoIlegivel(f"{campo} ausente ou inválido")
        campos[campo] = valor
    return Comando(
        tipo=tipo, saga_id=campos["sagaId"], agendamento_id=campos["agendamentoId"],
        doador_id=str(dados.get("doadorId") or ""), slot_id=dados.get("slotId"),
        data_hora_inicio=dados.get("dataHoraInicio"),
    )


def _validar_programacao(cmd: Comando, settings: Settings, agora: datetime) -> tuple[datetime | None, str | None]:
    """Devolve (início do agendamento, motivo da falha). Falha => resposta FALHOU."""
    if cmd.doador_id in settings.doadores_com_falha_simulada:
        return None, "Falha simulada no envio da confirmação (COMUNICACAO_SIMULAR_FALHA_DOADORES)"
    if not cmd.doador_id:
        return None, "doadorId ausente"
    if not cmd.data_hora_inicio:
        return None, "dataHoraInicio ausente"
    try:
        inicio = datetime.fromisoformat(cmd.data_hora_inicio.replace("Z", "+00:00"))
    except ValueError:
        return None, f"dataHoraInicio inválida: {cmd.data_hora_inicio!r}"
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=UTC)
    if inicio <= agora:
        return None, "dataHoraInicio já passou: não há o que lembrar"
    return inicio, None


def _resposta(cmd: Comando, settings: Settings, ok: bool, motivo: str | None, agora: datetime) -> OutboxEvent:
    payload: dict[str, Any] = {
        "sagaId": cmd.saga_id, "agendamentoId": cmd.agendamento_id,
        "resultado": "PROGRAMADO" if ok else "FALHOU", "emitidoEm": _iso(agora),
    }
    if motivo:
        payload["motivo"] = motivo
    return OutboxEvent(
        aggregate_type="Lembrete", aggregate_id=cmd.agendamento_id,
        routing_key=settings.routing_key_programado if ok else settings.routing_key_falhou,
        payload=payload, message_id=f"saga-{cmd.saga_id}-step3-resposta", correlation_id=request_id_var.get(),
    )


def _notificacao(cmd: Comando, tipo: str, conteudo: str) -> Notificacao:
    return Notificacao(
        doador_id=cmd.doador_id or None, agendamento_id=cmd.agendamento_id, tipo=tipo, canal=canais.CANAL_PADRAO,
        conteudo=conteudo, correlation_id=request_id_var.get(),
    )


async def _programar(
    session: AsyncSession, cmd: Comando, settings: Settings, agora: datetime
) -> tuple[Resultado, list[Notificacao]]:
    inicio, motivo = _validar_programacao(cmd, settings, agora)
    existente = await session.scalar(
        select(Lembrete).where(Lembrete.agendamento_id == cmd.agendamento_id).with_for_update()
    )
    if motivo is None and existente is not None and existente.status == StatusLembrete.CANCELADO:
        motivo = "o lembrete deste agendamento já foi cancelado (compensação recebida antes)"
    if motivo is not None or inicio is None:
        session.add(_resposta(cmd, settings, False, motivo, agora))
        return Resultado("FALHOU", motivo), []

    programado_para = max(inicio - settings.lembrete_antecedencia, agora)  # D-1 já passou: lembra logo
    if existente is None:
        session.add(Lembrete(
            agendamento_id=cmd.agendamento_id, saga_id=cmd.saga_id, doador_id=cmd.doador_id, slot_id=cmd.slot_id,
            data_hora_inicio=inicio, programado_para=programado_para, status=StatusLembrete.PROGRAMADO,
        ))
    elif existente.status == StatusLembrete.PROGRAMADO:  # nova SAGA sobre o mesmo agendamento: reprograma
        existente.data_hora_inicio, existente.programado_para, existente.atualizado_em = inicio, programado_para, agora
    notificacao = _notificacao(
        cmd, TipoNotificacao.CONFIRMACAO,
        f"Sua doação está agendada para {_iso(inicio)}. Enviaremos um lembrete em {_iso(programado_para)}.",
    )
    session.add(notificacao)
    session.add(_resposta(cmd, settings, True, None, agora))
    return Resultado("PROGRAMADO"), [notificacao]


async def _cancelar(session: AsyncSession, cmd: Comando, agora: datetime) -> tuple[Resultado, list[Notificacao]]:
    existente = await session.scalar(
        select(Lembrete).where(Lembrete.agendamento_id == cmd.agendamento_id).with_for_update()
    )
    if existente is None:
        # Compensação antes do comando de programar (reordenação): marca para que o programar não reative.
        session.add(Lembrete(
            agendamento_id=cmd.agendamento_id, saga_id=cmd.saga_id, doador_id=cmd.doador_id or "",
            slot_id=cmd.slot_id, data_hora_inicio=agora, programado_para=agora, status=StatusLembrete.CANCELADO,
        ))
        return Resultado("CANCELADO", "lembrete inexistente"), []
    if existente.status == StatusLembrete.CANCELADO:
        return Resultado("CANCELADO", "já estava cancelado"), []
    existente.status, existente.atualizado_em = StatusLembrete.CANCELADO, agora
    notificacao = _notificacao(
        cmd, TipoNotificacao.CANCELAMENTO,
        "Não foi possível concluir o seu agendamento; o lembrete foi cancelado.",
    )
    session.add(notificacao)
    return Resultado("CANCELADO"), [notificacao]


async def processar_comando(
    factory: async_sessionmaker[AsyncSession], settings: Settings, cmd: Comando, message_id: str,
    agora: datetime | None = None,
) -> Resultado:
    """Aplica o comando numa única transação (inbox + lembrete + histórico + Outbox). Idempotente."""
    agora = agora or datetime.now(UTC)
    async with factory() as session, session.begin():
        if not await registrar_no_inbox(session, message_id):
            return Resultado("DUPLICADO")
        if cmd.tipo == PROGRAMAR:
            resultado, notificacoes = await _programar(session, cmd, settings, agora)
        else:
            resultado, notificacoes = await _cancelar(session, cmd, agora)
    for n in notificacoes:  # "envio" só depois do commit
        canais.enviar(n)
    return resultado


async def registrar_rejeitada(
    factory: async_sessionmaker[AsyncSession], fila: str, message, motivo: str
) -> None:
    async with factory() as session, session.begin():
        session.add(MensagemRejeitada(
            fila=fila, message_id=message.message_id, routing_key=getattr(message, "routing_key", None),
            motivo=motivo, corpo=message.body[:4000].decode("utf-8", errors="replace"),
        ))


async def tratar_mensagem(message, factory: async_sessionmaker[AsyncSession], settings: Settings) -> None:
    """Callback do consumidor: ack só depois do commit; ilegível -> rejeitadas; transitório -> devolve à fila."""
    token = request_id_var.set(getattr(message, "correlation_id", None))
    try:
        try:
            cmd = ler_comando(message.body, getattr(message, "routing_key", None), settings)
            sufixo = "step3" if cmd.tipo == PROGRAMAR else "step3-comp"
            message_id = message.message_id or f"saga-{cmd.saga_id}-{sufixo}"
            resultado = await processar_comando(factory, settings, cmd, message_id)
            logger.info(
                "Comando %s da SAGA %s: %s%s", cmd.tipo, cmd.saga_id, resultado.acao,
                f" ({resultado.motivo})" if resultado.motivo else "",
            )
        except ComandoIlegivel as exc:
            logger.error("Comando ilegível descartado em mensagens_rejeitadas (%s): %r", exc, message.body[:200])
            try:
                await registrar_rejeitada(factory, settings.fila_comandos, message, str(exc))
            except Exception as erro_banco:
                logger.warning("Falha ao registrar comando rejeitado: %s. Devolvendo à fila.", erro_banco)
                await asyncio.sleep(settings.consumidor_espera_erro)
                await message.nack(requeue=True)
                return
        except Exception as exc:
            logger.warning("Falha ao processar comando: %s. Devolvendo à fila.", exc)
            await asyncio.sleep(settings.consumidor_espera_erro)
            await message.nack(requeue=True)
            return
        await message.ack()
    finally:
        request_id_var.reset(token)


async def executar_consumidor_comandos(app: FastAPI) -> None:
    settings, factory = app.state.settings, app.state.session_factory

    async def callback(message) -> None:
        await tratar_mensagem(message, factory, settings)

    await manter_consumidor(settings, settings.fila_comandos, callback)

