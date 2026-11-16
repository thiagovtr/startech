"""Persistência das transições (PostgreSQL real): atomicidade estado + log + Outbox, lock otimista e reivindicação."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from orquestrador.models.orm import MensagemProcessada, OutboxEvent, SagaExecucao, SagaPassoLog
from orquestrador.repositories import sagas as repo
from orquestrador.saga.estados import (
    CompensacaoConcluida,
    EstadoSaga,
    FalhaTecnica,
    Passo,
    PassoConcluido,
    PassoRecusado,
    Politica,
    RespostaComunicacao,
    StatusSaga,
)
from orquestrador.saga.maquina import transicionar

AGORA = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
P = Politica()
SEM_JITTER = {"jitter": lambda _ms: 0}


@pytest.fixture
def sessoes(pg_engine):
    return async_sessionmaker(pg_engine, expire_on_commit=False)


def _run(coro):
    return asyncio.run(coro)


async def _nova(sessoes, doador="doador-1", **kw):
    return (await repo.criar(sessoes, doador_id=doador, slot_id="slot-1", agora=AGORA, max_retries=5, **kw)).saga


async def _contar(sessoes, modelo, *filtros):
    async with sessoes() as s:
        return await s.scalar(select(func.count()).select_from(modelo).where(*filtros))


async def _avancar(sessoes, saga, evento, politica=P, agora=AGORA, **kw):
    t = transicionar(repo.estado_de(saga), evento, politica)
    return await repo.aplicar_transicao(sessoes, saga, t, agora=agora, **SEM_JITTER, **kw)


# ------------------------------------------------------------------ criação


def test_criar_inicia_em_started_elegivel_para_o_passo1(sessoes):
    saga = _run(_nova(sessoes, correlation_id="req-1"))
    assert (saga.status, saga.current_step, saga.version) == ("STARTED", "STEP1", 0)
    assert saga.next_attempt_at == AGORA and saga.correlation_id == "req-1"
    uuid.UUID(saga.agendamento_id)  # agendamentoId gerado pelo orquestrador


def test_criar_com_mesma_idempotency_key_devolve_a_mesma_saga(sessoes):
    async def go():
        a = await repo.criar(sessoes, doador_id="d", slot_id="s", agora=AGORA, max_retries=5, idempotency_key="k1")
        b = await repo.criar(sessoes, doador_id="d", slot_id="s", agora=AGORA, max_retries=5, idempotency_key="k1")
        return a, b

    a, b = _run(go())
    assert a.criada and not b.criada and a.saga.saga_id == b.saga.saga_id


def test_criar_segunda_saga_ativa_do_mesmo_doador_viola_rn09(sessoes):
    _run(_nova(sessoes))
    with pytest.raises(repo.SagaAtivaParaDoador):
        _run(_nova(sessoes))


# ------------------------------------------------------------------ transição atômica


def test_transicao_grava_estado_log_e_payload(sessoes):
    async def go():
        saga = await _nova(sessoes)
        saga = await _avancar(sessoes, saga, PassoConcluido(Passo.STEP1, {"dataHoraInicio": "2026-11-25T14:00:00Z"}))
        return saga, await repo.listar_log(sessoes, saga.saga_id)

    saga, log = _run(go())
    assert (saga.status, saga.current_step, saga.version) == ("SLOT_RESERVED", "STEP2", 1)
    assert saga.payload == {"dataHoraInicio": "2026-11-25T14:00:00Z"}
    assert saga.next_attempt_at == AGORA  # passo 2 pendente: elegível já
    assert [(r.step, r.acao, r.resultado) for r in log] == [("STEP1", "FORWARD", "OK")]


def test_passo2_ok_grava_o_comando_do_passo3_no_outbox_na_mesma_transacao(sessoes):
    async def go():
        saga = await _nova(sessoes, correlation_id="req-9")
        saga = await _avancar(sessoes, saga, PassoConcluido(Passo.STEP1, {"dataHoraInicio": "2026-11-25T14:00:00Z"}))
        saga = await _avancar(sessoes, saga, PassoConcluido(Passo.STEP2))
        async with sessoes() as s:
            eventos = list(await s.scalars(select(OutboxEvent)))
        return saga, eventos

    saga, (evento,) = _run(go())
    assert saga.status == "AWAITING_COMUNICACAO"
    assert saga.deadline_at == AGORA + timedelta(seconds=30) == saga.next_attempt_at
    assert evento.routing_key == "saga.comando.comunicacao.programar-lembrete"
    assert evento.message_id == f"saga-{saga.saga_id}-step3"
    assert evento.correlation_id == "req-9" and evento.published is False
    assert evento.payload == {
        "tipo": "ProgramarLembreteEConfirmar", "sagaId": str(saga.saga_id), "agendamentoId": saga.agendamento_id,
        "doadorId": "doador-1", "slotId": "slot-1", "dataHoraInicio": "2026-11-25T14:00:00Z",
        "emitidoEm": "2026-11-17T10:00:00Z",
    }


def test_compensacao_completa_grava_cancelamento_e_desfecho(sessoes):
    async def go():
        saga = await _nova(sessoes)
        for ev in (PassoConcluido(Passo.STEP1, {"dataHoraInicio": "x"}), PassoConcluido(Passo.STEP2),
                   RespostaComunicacao(ok=False, motivo="sem contato"),
                   CompensacaoConcluida(Passo.STEP2), CompensacaoConcluida(Passo.STEP1)):
            saga = await _avancar(sessoes, saga, ev)
        async with sessoes() as s:
            rotas = list(await s.scalars(select(OutboxEvent.routing_key).order_by(OutboxEvent.created_at)))
        return saga, rotas

    saga, rotas = _run(go())
    assert saga.status == "COMPENSATED" and saga.next_attempt_at is None and saga.deadline_at is None
    assert saga.recusa == {"type": "urn:startech:error:lembrete-nao-programado", "detail": "sem contato"}
    assert sorted(rotas) == sorted([
        "saga.comando.comunicacao.programar-lembrete", "saga.comando.comunicacao.cancelar-lembrete",
        "saga.agendamento.compensado",
    ])


def test_recusa_fica_registrada_para_o_get(sessoes):
    problema = {"status": 422, "type": "urn:startech:error:intervalo-minimo", "detail": "doou há 10 dias"}

    async def go():
        saga = await _nova(sessoes)
        saga = await _avancar(sessoes, saga, PassoConcluido(Passo.STEP1, {"dataHoraInicio": "x"}))
        return await _avancar(sessoes, saga, PassoRecusado(Passo.STEP2, problema))

    saga = _run(go())
    assert (saga.status, saga.current_step) == ("COMPENSATING", "STEP1") and saga.recusa == problema


def test_falha_tecnica_agenda_retentativa_com_backoff_e_jitter(sessoes):
    async def go():
        saga = await _nova(sessoes)
        t = transicionar(repo.estado_de(saga), FalhaTecnica(Passo.STEP1, "ms-agendamentos: timeout"), P)
        return await repo.aplicar_transicao(sessoes, saga, t, agora=AGORA, jitter=lambda ms: ms // 10)

    saga = _run(go())
    assert saga.retry_count == 1 and saga.status == "STARTED"
    assert saga.next_attempt_at == AGORA + timedelta(milliseconds=550)  # 500 ms + jitter de 10%
    assert saga.error_detail == "ms-agendamentos: timeout"


def test_versao_desatualizada_nao_grava_nada(sessoes):
    async def go():
        saga = await _nova(sessoes)
        await _avancar(sessoes, saga, PassoConcluido(Passo.STEP1, {"dataHoraInicio": "x"}))  # version 0 -> 1
        with pytest.raises(repo.ConflitoVersao):
            await _avancar(sessoes, saga, PassoConcluido(Passo.STEP1, {"dataHoraInicio": "x"}))  # ainda lida como 0
        return await _contar(sessoes, SagaPassoLog, SagaPassoLog.saga_id == saga.saga_id)

    assert _run(go()) == 1  # só o log da primeira transição


def test_erro_no_meio_desfaz_estado_log_e_outbox(sessoes):
    """Atomicidade: se o Outbox falhar, nem o estado nem o log mudam."""

    async def go():
        saga = await _nova(sessoes)
        saga = await _avancar(sessoes, saga, PassoConcluido(Passo.STEP1, {"dataHoraInicio": "x"}))
        async with sessoes() as s, s.begin():  # ocupa o message_id do passo 3: o INSERT no Outbox vai falhar
            s.add(OutboxEvent(id=str(uuid.uuid4()), aggregate_type="X", aggregate_id="x", routing_key="x",
                              payload={}, message_id=f"saga-{saga.saga_id}-step3"))
        with pytest.raises(Exception):  # noqa: B017 - IntegrityError do driver
            await _avancar(sessoes, saga, PassoConcluido(Passo.STEP2))
        return await repo.obter(sessoes, saga.saga_id), await _contar(sessoes, SagaPassoLog)

    saga, n_log = _run(go())
    assert (saga.status, saga.version) == ("SLOT_RESERVED", 1) and n_log == 1


def test_mensagem_recebida_duas_vezes_e_processada_uma_vez(sessoes):
    async def go():
        saga = await _nova(sessoes)
        for ev in (PassoConcluido(Passo.STEP1, {"dataHoraInicio": "x"}), PassoConcluido(Passo.STEP2)):
            saga = await _avancar(sessoes, saga, ev)
        mid = f"saga-{saga.saga_id}-step3-resposta"
        saga = await _avancar(sessoes, saga, RespostaComunicacao(ok=True), mensagem_processada=mid)
        with pytest.raises(repo.MensagemDuplicada):
            await _avancar(sessoes, saga, RespostaComunicacao(ok=True), mensagem_processada=mid)
        return saga, await _contar(sessoes, MensagemProcessada)

    saga, n = _run(go())
    assert saga.status == "CONFIRMING" and n == 1


def test_evento_ignorado_nao_altera_a_saga(sessoes):
    async def go():
        saga = await _nova(sessoes)
        depois = await _avancar(sessoes, saga, PassoConcluido(Passo.STEP4))  # fora de ordem
        return saga, depois, await repo.obter(sessoes, saga.saga_id)

    antes, depois, lida = _run(go())
    assert depois is antes and lida.version == 0


# ------------------------------------------------------------------ reivindicação e pendentes


def test_reivindicar_so_uma_vez_ate_o_prazo_vencer(sessoes):
    async def go():
        saga = await _nova(sessoes)
        a = await repo.reivindicar(sessoes, saga.saga_id, AGORA, prazo_s=10)
        b = await repo.reivindicar(sessoes, saga.saga_id, AGORA + timedelta(seconds=5), prazo_s=10)
        c = await repo.reivindicar(sessoes, saga.saga_id, AGORA + timedelta(seconds=11), prazo_s=10)
        return a, b, c

    a, b, c = _run(go())
    assert a is not None and b is None and c is not None  # após o prazo, outra réplica retoma


def test_saga_finalizada_nao_e_reivindicada(sessoes):
    async def go():
        saga = await _nova(sessoes)
        saga = await _avancar(sessoes, saga, PassoRecusado(Passo.STEP1, {"status": 409}))
        return saga, await repo.reivindicar(sessoes, saga.saga_id, AGORA + timedelta(days=1), prazo_s=10)

    saga, r = _run(go())
    assert saga.status == "REJECTED" and r is None


def test_pendentes_concorrentes_nunca_devolvem_a_mesma_saga(sessoes):
    async def go():
        for i in range(10):
            await _nova(sessoes, doador=f"d{i}")
        lotes = await asyncio.gather(*[
            repo.selecionar_pendentes(sessoes, AGORA, prazo_s=30, limite=4) for _ in range(4)
        ])
        de_novo = await repo.selecionar_pendentes(sessoes, AGORA + timedelta(seconds=1), prazo_s=30)
        return lotes, de_novo

    lotes, de_novo = _run(go())
    todos = [s for lote in lotes for s in lote]
    assert len(todos) == len(set(todos)) == 10
    assert de_novo == []  # todas reservadas pelo prazo


def test_pendentes_respeita_horario_e_ignora_finalizadas(sessoes):
    async def go():
        futura = await _nova(sessoes, doador="d1")
        t = transicionar(repo.estado_de(futura), FalhaTecnica(Passo.STEP1), P)
        await repo.aplicar_transicao(sessoes, futura, t, agora=AGORA, **SEM_JITTER)  # volta em 500 ms
        final = await _nova(sessoes, doador="d2")
        await _avancar(sessoes, final, PassoRecusado(Passo.STEP1, {"status": 409}))
        agora = await repo.selecionar_pendentes(sessoes, AGORA, prazo_s=30)
        depois = await repo.selecionar_pendentes(sessoes, AGORA + timedelta(seconds=1), prazo_s=30)
        return futura.saga_id, agora, depois

    futura, agora, depois = _run(go())
    assert agora == [] and depois == [futura]


def test_estado_de():
    saga = SagaExecucao(status="COMPENSATING", current_step="STEP2", retry_count=3)
    assert repo.estado_de(saga) == EstadoSaga(StatusSaga.COMPENSATING, Passo.STEP2, 3)
