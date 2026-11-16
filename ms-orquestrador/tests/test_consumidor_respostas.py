"""Consumidor das respostas do passo 3: transição, deduplicação, DLQ e retorno à fila."""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta

import aio_pika
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from orquestrador.config import Settings
from orquestrador.messaging.rabbitmq import conectar
from orquestrador.repositories import sagas as repo
from orquestrador.saga.estados import Passo, PassoConcluido, Politica, TimeoutPasso3
from orquestrador.saga.maquina import transicionar
from orquestrador.services.consumidor_respostas import iniciar_consumo, tratar_mensagem

P = Politica(aguardar_resposta_passo3=True)


class Mensagem:
    """IncomingMessage simulada: registra ack/reject/nack."""

    def __init__(self, corpo, message_id=None, correlation_id="req-1"):
        self.body = corpo if isinstance(corpo, bytes) else json.dumps(corpo).encode()
        self.message_id = message_id
        self.correlation_id = correlation_id
        self.desfecho = None

    async def ack(self):
        self.desfecho = "ack"

    async def reject(self, requeue=False):
        self.desfecho = f"reject(requeue={requeue})"

    async def nack(self, requeue=True):
        self.desfecho = f"nack(requeue={requeue})"


@pytest.fixture
def sessoes(pg_engine):
    return async_sessionmaker(pg_engine, expire_on_commit=False)


async def _aguardando(sessoes, doador="d1"):
    agora = datetime.now(UTC)
    saga = (await repo.criar(sessoes, doador_id=doador, slot_id="slot-1", agora=agora, max_retries=5)).saga
    for ev in (PassoConcluido(Passo.STEP1, {"dataHoraInicio": "2026-11-25T14:00:00Z"}), PassoConcluido(Passo.STEP2)):
        saga = await repo.aplicar_transicao(sessoes, saga, transicionar(repo.estado_de(saga), ev, P), agora=agora)
    assert saga.status == "AWAITING_COMUNICACAO"
    return saga


def _resposta(saga, resultado="PROGRAMADO", **extra):
    return {"sagaId": str(saga.saga_id), "agendamentoId": saga.agendamento_id, "resultado": resultado,
            "emitidoEm": "2026-11-17T10:00:01Z", **extra}


def _run(coro):
    return asyncio.run(coro)


# ------------------------------------------------------------------ tratamento (sem broker)


def test_programado_leva_a_confirming_e_dispara_o_passo4(sessoes):
    disparadas = []

    async def ao_confirmar(saga_id):
        disparadas.append(saga_id)

    async def go():
        saga = await _aguardando(sessoes)
        msg = Mensagem(_resposta(saga), message_id=f"saga-{saga.saga_id}-step3-resposta")
        await tratar_mensagem(msg, sessoes, P, ao_confirmar)
        return saga, msg, await repo.obter(sessoes, saga.saga_id), await repo.listar_log(sessoes, saga.saga_id)

    saga, msg, final, log = _run(go())
    assert msg.desfecho == "ack"
    assert (final.status, final.current_step, final.deadline_at) == ("CONFIRMING", "STEP4", None)
    assert disparadas == [saga.saga_id]
    assert (log[-1].step, log[-1].acao, log[-1].resultado) == ("STEP3", "FORWARD", "OK")


def test_falhou_inicia_a_compensacao_com_o_motivo(sessoes):
    async def go():
        saga = await _aguardando(sessoes)
        msg = Mensagem(_resposta(saga, "FALHOU", motivo="doador sem e-mail"))
        await tratar_mensagem(msg, sessoes, P)
        return msg, await repo.obter(sessoes, saga.saga_id)

    msg, final = _run(go())
    assert msg.desfecho == "ack"
    assert (final.status, final.current_step) == ("COMPENSATING", "STEP2")
    assert final.recusa["detail"] == "doador sem e-mail"


def test_resposta_duplicada_e_reconhecida_e_ignorada(sessoes):
    disparadas = []

    async def ao_confirmar(saga_id):
        disparadas.append(saga_id)

    async def go():
        saga = await _aguardando(sessoes)
        primeira, segunda = Mensagem(_resposta(saga), "m-1"), Mensagem(_resposta(saga), "m-1")
        await tratar_mensagem(primeira, sessoes, P, ao_confirmar)
        await tratar_mensagem(segunda, sessoes, P, ao_confirmar)
        return primeira, segunda, await repo.obter(sessoes, saga.saga_id)

    primeira, segunda, final = _run(go())
    assert primeira.desfecho == segunda.desfecho == "ack"
    assert final.version == 3 and len(disparadas) == 1  # a segunda não mudou nada


def test_sem_message_id_usa_o_id_do_contrato(sessoes):
    async def go():
        saga = await _aguardando(sessoes)
        await tratar_mensagem(Mensagem(_resposta(saga)), sessoes, P)
        segunda = Mensagem(_resposta(saga), message_id=f"saga-{saga.saga_id}-step3-resposta")
        await tratar_mensagem(segunda, sessoes, P)
        return segunda, await repo.obter(sessoes, saga.saga_id)

    segunda, final = _run(go())
    assert segunda.desfecho == "ack" and final.version == 3


def test_resposta_atrasada_apos_timeout_e_registrada_e_ignorada(sessoes):
    async def go():
        saga = await _aguardando(sessoes)
        saga = await repo.aplicar_transicao(  # o prazo venceu antes: a SAGA já está compensando
            sessoes, saga, transicionar(repo.estado_de(saga), TimeoutPasso3(), P), agora=datetime.now(UTC)
        )
        msg = Mensagem(_resposta(saga), "m-tarde")
        await tratar_mensagem(msg, sessoes, P)
        return saga, msg, await repo.obter(sessoes, saga.saga_id)

    antes, msg, final = _run(go())
    assert msg.desfecho == "ack"
    assert (final.status, final.version) == ("COMPENSATING", antes.version)


@pytest.mark.parametrize("corpo", [
    b"nao-e-json",
    b"[1, 2]",
    {"resultado": "PROGRAMADO"},  # sem sagaId
    {"sagaId": "nao-e-uuid", "resultado": "PROGRAMADO"},
])
def test_mensagem_malformada_vai_para_a_dlq(sessoes, corpo):
    msg = Mensagem(corpo)
    _run(tratar_mensagem(msg, sessoes, P))
    assert msg.desfecho == "reject(requeue=False)"


def test_resultado_desconhecido_saga_inexistente_ou_de_outro_agendamento_vao_para_a_dlq(sessoes):
    async def go():
        saga = await _aguardando(sessoes)
        msgs = [
            Mensagem(_resposta(saga, "TALVEZ")),
            Mensagem({"sagaId": str(uuid.uuid4()), "resultado": "PROGRAMADO"}),
            Mensagem({**_resposta(saga), "agendamentoId": "outro"}),
        ]
        for m in msgs:
            await tratar_mensagem(m, sessoes, P)
        return msgs, await repo.obter(sessoes, saga.saga_id)

    msgs, final = _run(go())
    assert [m.desfecho for m in msgs] == ["reject(requeue=False)"] * 3
    assert final.status == "AWAITING_COMUNICACAO"


def test_banco_fora_devolve_a_mensagem_a_fila():
    def sessoes_quebradas():
        raise ConnectionError("PostgreSQL fora")

    msg = Mensagem({"sagaId": str(uuid.uuid4()), "resultado": "PROGRAMADO"})
    _run(tratar_mensagem(msg, sessoes_quebradas, P, espera_erro=0))
    assert msg.desfecho == "nack(requeue=True)"


# ------------------------------------------------------------------ RabbitMQ real


def _settings(amqp_url):
    s = uuid.uuid4().hex[:8]
    return Settings(
        postgres_url="postgresql+asyncpg://x:y@127.0.0.1:1/z", rabbitmq_url=amqp_url,
        rabbitmq_exchange=f"test.{s}.events", rabbitmq_dlx_exchange=f"test.{s}.dlx",
        fila_respostas=f"test.{s}.respostas", fila_respostas_dlq=f"test.{s}.respostas.dlq",
        fila_comandos_comunicacao=f"test.{s}.comandos", fila_compensacoes_dlq=f"test.{s}.compensacoes.dlq",
    )


def test_ponta_a_ponta_no_broker_resposta_valida_e_invalida(sessoes, amqp_url):
    settings = _settings(amqp_url)

    async def go():
        saga = await _aguardando(sessoes)
        pub, exchange = await conectar(settings)
        consumo = await iniciar_consumo(settings, sessoes, P)
        try:
            await exchange.publish(
                aio_pika.Message(json.dumps(_resposta(saga)).encode(), message_id=f"saga-{saga.saga_id}-step3-resposta"),
                routing_key="comunicacao.lembrete.programado",
            )
            await exchange.publish(aio_pika.Message(b"lixo"), routing_key="comunicacao.lembrete.falhou")
            prazo = datetime.now(UTC) + timedelta(seconds=5)
            while datetime.now(UTC) < prazo:
                final = await repo.obter(sessoes, saga.saga_id)
                if final.status == "CONFIRMING":
                    break
                await asyncio.sleep(0.1)
            await asyncio.sleep(0.5)
            ch = await pub.channel()
            dlq = await ch.get_queue(settings.fila_respostas_dlq)
            morta = await dlq.get(fail=False, timeout=2)
            if morta is not None:
                await morta.ack()
            return final, morta
        finally:
            await consumo.close()
            ch = await pub.channel()
            for fila in (settings.fila_respostas, settings.fila_respostas_dlq, settings.fila_comandos_comunicacao,
                         settings.fila_compensacoes_dlq):
                await ch.queue_delete(fila)
            await ch.exchange_delete(settings.rabbitmq_exchange)
            await ch.exchange_delete(settings.rabbitmq_dlx_exchange)
            await pub.close()

    final, morta = _run(go())
    assert final.status == "CONFIRMING"
    assert morta is not None and morta.body == b"lixo"


def test_laco_do_consumidor_sobrevive_ao_rabbitmq_fora():
    from types import SimpleNamespace

    from orquestrador.services.consumidor_respostas import executar_consumidor

    settings = Settings(postgres_url="postgresql+asyncpg://x:y@127.0.0.1:1/z", rabbitmq_url="amqp://x:y@127.0.0.1:1/",
                        consumidor_reconexao=0.05)

    async def go():
        app = SimpleNamespace(state=SimpleNamespace(settings=settings, session_factory=None,
                                                    executor=SimpleNamespace(politica=P)))
        tarefa = asyncio.create_task(executar_consumidor(app))
        await asyncio.sleep(0.3)
        vivo = not tarefa.done()
        tarefa.cancel()
        await asyncio.gather(tarefa, return_exceptions=True)
        return vivo

    assert _run(go())
