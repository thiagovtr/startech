"""Persistência da SAGA: cada transição é UMA transação local (estado + log + Outbox [+ inbox]).

- Lock otimista: a transição só é gravada se `version` ainda for a lida (`ConflitoVersao` caso contrário).
- `next_attempt_at` diz quando a SAGA precisa de atenção do worker de recuperação:
  retentativa (agora + backoff + jitter), prazo da resposta do passo 3, "agora" quando há chamada pendente
  e NULL quando a SAGA termina. Quem vai executar uma chamada a "reivindica" empurrando esse horário
  (`reivindicar` / `selecionar_pendentes`), e assim duas réplicas não chamam o mesmo passo ao mesmo tempo.
"""

import random
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import and_, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orquestrador.models.orm import MensagemProcessada, OutboxEvent, SagaExecucao, SagaPassoLog
from orquestrador.saga import mensagens
from orquestrador.saga.estados import (
    STATUS_TERMINAIS,
    AgendarRetentativa,
    AguardarResposta,
    EstadoSaga,
    Passo,
    PublicarMensagem,
    StatusSaga,
    Transicao,
)

Sessoes = async_sessionmaker[AsyncSession]
_EM_ANDAMENTO = SagaExecucao.status.not_in([str(s) for s in STATUS_TERMINAIS])


class SagaAtivaParaDoador(Exception):
    """RN09: o doador já tem uma SAGA em andamento."""


class ConflitoVersao(Exception):
    """A SAGA mudou desde que foi lida (outra réplica ou evento concorrente)."""


class MensagemDuplicada(Exception):
    """A mensagem recebida já foi processada (inbox idempotente)."""


@dataclass(frozen=True)
class Criacao:
    saga: SagaExecucao
    criada: bool  # False: devolvida pela Idempotency-Key de uma requisição anterior


def estado_de(saga: SagaExecucao) -> EstadoSaga:
    return EstadoSaga(StatusSaga(saga.status), Passo(saga.current_step), saga.retry_count)


def jitter_padrao(espera_ms: int) -> int:
    return int(espera_ms * 0.2 * random.random())  # até +20% para não sincronizar retentativas


# ---------------------------------------------------------------- criação e leitura


async def criar(
    sessoes: Sessoes,
    *,
    doador_id: str,
    slot_id: str,
    agora: datetime,
    max_retries: int,
    idempotency_key: str | None = None,
    correlation_id: str | None = None,
) -> Criacao:
    """Cria a SAGA em STARTED, já elegível para o passo 1 (`next_attempt_at = agora`)."""
    saga = SagaExecucao(
        saga_id=uuid.uuid4(), agendamento_id=str(uuid.uuid4()), doador_id=doador_id, slot_id=slot_id,
        current_step=Passo.STEP1, status=StatusSaga.STARTED, payload={}, retry_count=0, max_retries=max_retries,
        next_attempt_at=agora, idempotency_key=idempotency_key, correlation_id=correlation_id, version=0,
    )
    try:
        async with sessoes() as session, session.begin():
            session.add(saga)
    except IntegrityError as exc:
        restricao = str(exc.orig)
        if idempotency_key and "idempotency_key" in restricao:
            async with sessoes() as session:
                existente = await session.scalar(
                    select(SagaExecucao).where(SagaExecucao.idempotency_key == idempotency_key)
                )
            if existente is not None:
                return Criacao(existente, criada=False)
        if "uq_saga_ativa_por_doador" in restricao:
            raise SagaAtivaParaDoador(doador_id) from None
        raise
    return Criacao(saga, criada=True)


async def obter(sessoes: Sessoes, saga_id: uuid.UUID) -> SagaExecucao | None:
    async with sessoes() as session:
        return await session.get(SagaExecucao, saga_id)


async def listar_log(sessoes: Sessoes, saga_id: uuid.UUID) -> list[SagaPassoLog]:
    async with sessoes() as session:
        resultado = await session.scalars(
            select(SagaPassoLog).where(SagaPassoLog.saga_id == saga_id).order_by(SagaPassoLog.id)
        )
        return list(resultado)


# ---------------------------------------------------------------- reivindicação (quem executa a próxima chamada)


async def reivindicar(sessoes: Sessoes, saga_id: uuid.UUID, agora: datetime, prazo_s: float) -> SagaExecucao | None:
    """Reserva a SAGA para quem vai executar a chamada pendente, por `prazo_s` segundos.

    Só funciona se ninguém a reservou (`next_attempt_at <= agora`). Se o processo cair no meio da chamada,
    o worker de recuperação a retoma quando o prazo vencer (a chamada é idempotente).
    """
    async with sessoes() as session, session.begin():
        linha = await session.execute(
            update(SagaExecucao)
            .where(SagaExecucao.saga_id == saga_id, _EM_ANDAMENTO, SagaExecucao.next_attempt_at <= agora)
            .values(next_attempt_at=agora + timedelta(seconds=prazo_s))
            .returning(SagaExecucao.saga_id)
        )
        if linha.first() is None:
            return None
    return await obter(sessoes, saga_id)


async def selecionar_pendentes(sessoes: Sessoes, agora: datetime, prazo_s: float, limite: int = 20) -> list[uuid.UUID]:
    """SAGAs vencidas (retentativa, prazo do passo 3 ou retomada), já reservadas para quem chamou.

    `FOR UPDATE SKIP LOCKED` permite várias réplicas: cada SAGA vencida vai para uma só.
    """
    async with sessoes() as session, session.begin():
        ids = list(await session.scalars(
            select(SagaExecucao.saga_id)
            .where(_EM_ANDAMENTO, SagaExecucao.next_attempt_at <= agora)
            .order_by(SagaExecucao.next_attempt_at)
            .limit(limite)
            .with_for_update(skip_locked=True)
        ))
        if ids:
            await session.execute(
                update(SagaExecucao)
                .where(SagaExecucao.saga_id.in_(ids))
                .values(next_attempt_at=agora + timedelta(seconds=prazo_s))
            )
    return ids


# ---------------------------------------------------------------- transição


def _proximo_horario(transicao: Transicao, agora: datetime, jitter: Callable[[int], int]) -> tuple:
    """(next_attempt_at, deadline_at) depois da transição."""
    if transicao.terminal:
        return None, None
    for acao in transicao.acoes:
        if isinstance(acao, AgendarRetentativa):
            espera = acao.espera_ms + jitter(acao.espera_ms)
            return agora + timedelta(milliseconds=espera), None
        if isinstance(acao, AguardarResposta):
            prazo = agora + timedelta(seconds=acao.timeout_s)
            return prazo, prazo  # o worker de recuperação acorda no prazo para aplicar o timeout
    return agora, None  # há chamada pendente: elegível já (quem executa a reivindica)


async def aplicar_transicao(
    sessoes: Sessoes,
    saga: SagaExecucao,
    transicao: Transicao,
    *,
    agora: datetime,
    mensagem_processada: str | None = None,
    jitter: Callable[[int], int] = jitter_padrao,
) -> SagaExecucao:
    """Grava a transição numa única transação e devolve a SAGA atualizada.

    `saga` é o estado lido (com a `version` usada no lock otimista). Transição ignorada não grava nada,
    exceto a mensagem recebida no inbox (para não reprocessá-la).
    """
    async with sessoes() as session, session.begin():
        if mensagem_processada is not None:
            nova = await session.execute(
                pg_insert(MensagemProcessada).values(message_id=mensagem_processada)
                .on_conflict_do_nothing().returning(MensagemProcessada.message_id)
            )
            if nova.first() is None:
                raise MensagemDuplicada(mensagem_processada)
        if transicao.ignorado:
            return saga

        proximo, prazo = _proximo_horario(transicao, agora, jitter)
        falhas = [r.detalhe.get("motivo") for r in transicao.registros if r.detalhe and r.detalhe.get("motivo")]
        valores: dict = {
            "status": transicao.estado.status,
            "current_step": transicao.estado.passo,
            "retry_count": transicao.estado.retry_count,
            "next_attempt_at": proximo,
            "deadline_at": prazo,
            "version": SagaExecucao.version + 1,
            "updated_at": agora,
        }
        if transicao.dados:
            valores["payload"] = {**saga.payload, **transicao.dados}
        if transicao.recusa is not None:
            valores["recusa"] = transicao.recusa
        if falhas:
            valores["error_detail"] = falhas[-1]

        atualizada = await session.scalar(
            update(SagaExecucao)
            .where(and_(SagaExecucao.saga_id == saga.saga_id, SagaExecucao.version == saga.version))
            .values(**valores)
            .returning(SagaExecucao)
        )
        if atualizada is None:
            raise ConflitoVersao(str(saga.saga_id))

        for registro in transicao.registros:
            session.add(SagaPassoLog(
                saga_id=saga.saga_id, step=registro.passo, acao=registro.direcao,
                resultado=registro.resultado, detalhe=registro.detalhe,
            ))

        detalhe = (transicao.recusa or {}).get("detail") or atualizada.error_detail
        for acao in transicao.acoes:
            if not isinstance(acao, PublicarMensagem):
                continue
            routing_key, message_id, corpo = mensagens.montar(
                acao.tipo, saga_id=saga.saga_id, agendamento_id=saga.agendamento_id, doador_id=saga.doador_id,
                slot_id=saga.slot_id, payload=atualizada.payload, status=transicao.estado.status,
                detalhe=detalhe, agora=agora,
            )
            await session.execute(insert(OutboxEvent).values(
                id=str(uuid.uuid4()), aggregate_type="Saga", aggregate_id=str(saga.saga_id),
                routing_key=routing_key, message_id=message_id, payload=corpo,
                correlation_id=saga.correlation_id,
            ))
    return atualizada

