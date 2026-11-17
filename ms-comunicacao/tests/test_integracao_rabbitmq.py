"""Integração com RabbitMQ e PostgreSQL reais: comando da SAGA -> lembrete -> resposta publicada pelo Outbox."""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import aio_pika
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from comunicacao.config import Settings
from comunicacao.models.orm import Lembrete, Notificacao
from comunicacao.services.outbox_publisher import executar_publicador
from comunicacao.services.workers import iniciar_workers, parar_workers


def _settings(amqp_url: str, **extra) -> Settings:
    sufixo = uuid.uuid4().hex[:8]  # exchange e filas próprias por teste: nada vaza entre testes
    return Settings(
        postgres_url="postgresql+asyncpg://x:y@h/d", rabbitmq_url=amqp_url,
        rabbitmq_exchange=f"teste.{sufixo}", fila_comandos=f"teste.comandos.{sufixo}",
        fila_notificacoes=f"teste.notificacoes.{sufixo}", fila_notificacoes_dlq=f"teste.notificacoes.dlq.{sufixo}",
        rabbitmq_dlx_exchange=f"teste.dlx.{sufixo}", outbox_intervalo=0.05, lembretes_intervalo=0.05,
        consumidor_reconexao=0.5, outbox_limpeza_habilitada=False, **extra,
    )


async def _preparar_lado_do_orquestrador(s: Settings):
    """Declara o que o ms-orquestrador declara: a fila de comandos SEM argumentos e uma fila de respostas."""
    conn = await aio_pika.connect(s.rabbitmq_url)
    ch = await conn.channel()
    ex = await ch.declare_exchange(s.rabbitmq_exchange, aio_pika.ExchangeType.TOPIC, durable=True)
    comandos = await ch.declare_queue(s.fila_comandos, durable=True)
    await comandos.bind(ex, routing_key=s.binding_comandos)
    respostas = await ch.declare_queue(f"{s.fila_comandos}.respostas", exclusive=True)
    await respostas.bind(ex, routing_key="comunicacao.lembrete.*")
    return conn, ex, respostas


async def _esperar(cond, timeout=10.0):
    fim = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < fim:
        if await cond():
            return True
        await asyncio.sleep(0.05)
    return False


def test_comando_vira_resposta_programado_no_broker(pg_engine, amqp_url):
    s = _settings(amqp_url)
    factory = async_sessionmaker(pg_engine, expire_on_commit=False)

    async def go():
        conn, ex, respostas = await _preparar_lado_do_orquestrador(s)
        app = SimpleNamespace(state=SimpleNamespace(settings=s, session_factory=factory))
        workers = iniciar_workers(app)  # type: ignore[arg-type]
        try:
            inicio = (datetime.now(UTC) + timedelta(days=4)).isoformat().replace("+00:00", "Z")
            corpo = {"tipo": "ProgramarLembreteEConfirmar", "sagaId": "s1", "agendamentoId": "a1",
                     "doadorId": "d1", "slotId": "x", "dataHoraInicio": inicio, "emitidoEm": inicio}
            for _ in range(2):  # reentrega (at-least-once): mesmo message_id
                await ex.publish(aio_pika.Message(json.dumps(corpo).encode(), message_id="saga-s1-step3",
                                                  correlation_id="rid-xyz"),
                                 routing_key="saga.comando.comunicacao.programar-lembrete")
            msg = await _obter(respostas)
            await asyncio.sleep(0.5)
            segunda = await respostas.get(fail=False)
            return msg, segunda
        finally:
            await parar_workers(workers)
            await conn.close()

    msg, segunda = asyncio.run(go())
    assert msg.routing_key == "comunicacao.lembrete.programado"
    assert msg.message_id == "saga-s1-step3-resposta" and msg.correlation_id == "rid-xyz"
    assert json.loads(msg.body)["resultado"] == "PROGRAMADO"
    assert segunda is None  # duplicata não gerou segunda resposta


async def _obter(fila, timeout=10.0):
    fim = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < fim:
        msg = await fila.get(fail=False, no_ack=True)
        if msg is not None:
            return msg
        await asyncio.sleep(0.05)
    raise AssertionError("nenhuma resposta publicada")


def test_lembrete_dispara_e_desfecho_invalido_vai_para_dlq(pg_engine, amqp_url):
    s = _settings(amqp_url, lembrete_antecedencia=timedelta(days=1))
    factory = async_sessionmaker(pg_engine, expire_on_commit=False)

    async def go():
        conn, ex, _ = await _preparar_lado_do_orquestrador(s)
        app = SimpleNamespace(state=SimpleNamespace(settings=s, session_factory=factory))
        workers = iniciar_workers(app)  # type: ignore[arg-type]
        try:
            # início em 1 dia e 1 s: o D-1 vence em ~1 s
            inicio = (datetime.now(UTC) + timedelta(days=1, seconds=1)).isoformat()
            corpo = {"tipo": "ProgramarLembreteEConfirmar", "sagaId": "s2", "agendamentoId": "a2",
                     "doadorId": "d2", "dataHoraInicio": inicio}
            await ex.publish(aio_pika.Message(json.dumps(corpo).encode(), message_id="saga-s2-step3"),
                             routing_key="saga.comando.comunicacao.programar-lembrete")

            async def enviado():
                async with factory() as ses:
                    return await ses.scalar(select(Lembrete.status).where(Lembrete.agendamento_id == "a2")) == "ENVIADO"

            ok_lembrete = await _esperar(enviado)

            await _esperar(lambda: _fila_existe(conn, s.fila_notificacoes))
            await ex.publish(aio_pika.Message(b"{quebrado", message_id="x1"), routing_key="saga.agendamento.confirmado")
            ch = await conn.channel()
            dlq = await ch.declare_queue(s.fila_notificacoes_dlq, durable=True)
            morta = await _obter(dlq)
            await ch.queue_delete(s.fila_notificacoes_dlq)
            await ch.queue_delete(s.fila_notificacoes)
            await ch.queue_delete(s.fila_comandos)
            return ok_lembrete, morta
        finally:
            await parar_workers(workers)
            await conn.close()

    ok_lembrete, morta = asyncio.run(go())
    assert ok_lembrete and morta.body == b"{quebrado"

    async def contar():
        async with factory() as ses:
            return await ses.scalar(select(func.count()).select_from(Notificacao).where(Notificacao.tipo == "LEMBRETE"))

    assert asyncio.run(contar()) == 1


async def _fila_existe(conn, nome: str) -> bool:
    ch = await conn.channel()
    try:
        await ch.declare_queue(nome, passive=True)
        return True
    except Exception:
        return False


def test_respostas_ficam_no_outbox_com_broker_fora_e_saem_quando_volta(pg_engine, amqp_url):
    """Sem broker o comando não chega, mas uma resposta já gravada espera no Outbox e é drenada depois."""
    from comunicacao.services.comandos import PROGRAMAR, Comando, processar_comando

    factory = async_sessionmaker(pg_engine, expire_on_commit=False)
    s_fora = _settings("amqp://guest:guest@127.0.0.1:1/")
    inicio = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    asyncio.run(processar_comando(factory, s_fora, Comando(PROGRAMAR, "s3", "a3", "d3", None, inicio), "saga-s3-step3"))

    s = _settings(amqp_url)

    async def go():
        conn, _, respostas = await _preparar_lado_do_orquestrador(s)
        app = SimpleNamespace(state=SimpleNamespace(settings=s, session_factory=factory))
        tarefa = asyncio.create_task(executar_publicador(app))  # type: ignore[arg-type]
        try:
            return await _obter(respostas)
        finally:
            tarefa.cancel()
            await asyncio.gather(tarefa, return_exceptions=True)
            await conn.close()

    msg = asyncio.run(go())
    assert msg.message_id == "saga-s3-step3-resposta"


@pytest.mark.parametrize("ordem", ["orquestrador_primeiro", "comunicacao_primeiro"])
def test_fila_de_comandos_compativel_com_a_declaracao_do_orquestrador(amqp_url, ordem):
    """Os dois serviços declaram a mesma fila; argumentos divergentes dariam PRECONDITION_FAILED."""
    from comunicacao.messaging.rabbitmq import conectar_consumidor

    s = _settings(amqp_url)

    async def go():
        if ordem == "orquestrador_primeiro":
            conn, _, _ = await _preparar_lado_do_orquestrador(s)
            c2, _ = await conectar_consumidor(s, s.fila_comandos)
        else:
            c2, _ = await conectar_consumidor(s, s.fila_comandos)
            conn, _, _ = await _preparar_lado_do_orquestrador(s)
        ch = await conn.channel()
        await ch.queue_delete(s.fila_comandos)
        await c2.close()
        await conn.close()

    asyncio.run(go())
