"""Outbox do orquestrador: publicação (propriedades AMQP, ordem, falhas), retenção e topologia no RabbitMQ."""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import aio_pika
import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from orquestrador.config import Settings
from orquestrador.messaging.rabbitmq import conectar
from orquestrador.models.orm import OutboxEvent
from orquestrador.repositories import sagas as repo
from orquestrador.saga.estados import (
    CompensacaoConcluida,
    FalhaTecnica,
    Passo,
    PassoConcluido,
    PassoRecusado,
    Politica,
)
from orquestrador.saga.maquina import transicionar
from orquestrador.services.outbox_limpeza import limpar_publicados
from orquestrador.services.outbox_publisher import executar_publicador, publicar_pendentes

AGORA = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)


@pytest.fixture
def sessoes(pg_engine):
    return async_sessionmaker(pg_engine, expire_on_commit=False)


class ExchangeFalsa:
    def __init__(self, falhar_na=None):
        self.publicadas: list[tuple[str, aio_pika.Message]] = []
        self._falhar_na = falhar_na

    async def publish(self, mensagem, routing_key):
        if self._falhar_na is not None and len(self.publicadas) + 1 == self._falhar_na:
            raise ConnectionError("broker caiu")
        self.publicadas.append((routing_key, mensagem))


async def _saga_ate_o_passo3(sessoes, doador="d1", correlation_id="req-7"):
    """SAGA real até gravar o comando do passo 3 no Outbox."""
    saga = (await repo.criar(sessoes, doador_id=doador, slot_id="slot-1", agora=AGORA, max_retries=5,
                             correlation_id=correlation_id)).saga
    for ev in (PassoConcluido(Passo.STEP1, {"dataHoraInicio": "2026-11-25T14:00:00Z"}), PassoConcluido(Passo.STEP2)):
        saga = await repo.aplicar_transicao(sessoes, saga, transicionar(repo.estado_de(saga), ev, Politica()), agora=AGORA)
    return saga


async def _pendentes(sessoes):
    async with sessoes() as s:
        return list(await s.scalars(select(OutboxEvent).where(OutboxEvent.published.is_(False))))


# ------------------------------------------------------------------ publicação (sem broker)


def test_publica_com_as_propriedades_do_contrato(sessoes):
    async def go():
        saga = await _saga_ate_o_passo3(sessoes)
        exchange = ExchangeFalsa()
        n = await publicar_pendentes(sessoes, exchange)
        return saga, n, exchange.publicadas, await _pendentes(sessoes)

    saga, n, publicadas, pendentes = asyncio.run(go())
    assert n == 1 and pendentes == []
    ((rota, msg),) = publicadas
    assert rota == "saga.comando.comunicacao.programar-lembrete"
    assert msg.message_id == f"saga-{saga.saga_id}-step3"
    assert msg.correlation_id == "req-7"
    assert msg.content_type == "application/json"
    assert msg.delivery_mode == aio_pika.DeliveryMode.PERSISTENT
    assert msg.type == rota
    corpo = json.loads(msg.body)
    assert corpo["tipo"] == "ProgramarLembreteEConfirmar" and corpo["dataHoraInicio"] == "2026-11-25T14:00:00Z"


def test_publica_em_ordem_e_falha_no_meio_mantem_o_resto_pendente(sessoes):
    async def go():
        for i in range(4):
            await _saga_ate_o_passo3(sessoes, doador=f"d{i}")
        exchange = ExchangeFalsa(falhar_na=3)
        with pytest.raises(ConnectionError):
            await publicar_pendentes(sessoes, exchange)
        restantes = await _pendentes(sessoes)
        n = await publicar_pendentes(sessoes, ExchangeFalsa())
        return exchange.publicadas, len(restantes), n

    publicadas, restantes, n = asyncio.run(go())
    assert len(publicadas) == 2 and restantes == 2 and n == 2
    assert len({m.message_id for _, m in publicadas}) == 2


def test_publicadores_concorrentes_nao_duplicam(sessoes):
    async def go():
        for i in range(12):
            await _saga_ate_o_passo3(sessoes, doador=f"d{i}")
        exchanges = [ExchangeFalsa() for _ in range(3)]
        await asyncio.gather(*(publicar_pendentes(sessoes, e, lote=4) for e in exchanges))
        while await _pendentes(sessoes):
            await publicar_pendentes(sessoes, exchanges[0], lote=4)
        return [m.message_id for e in exchanges for _, m in e.publicadas]

    ids = asyncio.run(go())
    assert len(ids) == len(set(ids)) == 12


def test_rabbitmq_fora_o_laco_continua_e_as_mensagens_esperam(sessoes):
    settings = Settings(postgres_url="postgresql+asyncpg://x:y@127.0.0.1:1/z", rabbitmq_url="amqp://x:y@127.0.0.1:1/",
                        outbox_intervalo=0.01)

    async def go():
        await _saga_ate_o_passo3(sessoes)
        app = SimpleNamespace(state=SimpleNamespace(settings=settings, session_factory=sessoes))
        tarefa = asyncio.create_task(executar_publicador(app))
        await asyncio.sleep(0.5)
        vivo = not tarefa.done()
        tarefa.cancel()
        await asyncio.gather(tarefa, return_exceptions=True)
        return vivo, await _pendentes(sessoes)

    vivo, pendentes = asyncio.run(go())
    assert vivo and len(pendentes) == 1  # nada perdido: será publicado quando o broker voltar


# ------------------------------------------------------------------ retenção


def test_limpeza_remove_so_publicadas_antigas(sessoes):
    async def go():
        for i in range(3):
            await _saga_ate_o_passo3(sessoes, doador=f"d{i}")
        await publicar_pendentes(sessoes, ExchangeFalsa(), lote=2)  # 2 publicadas, 1 pendente
        async with sessoes() as s, s.begin():
            await s.execute(update(OutboxEvent).where(OutboxEvent.published.is_(True))
                            .values(published_at=datetime.now(UTC) - timedelta(days=8)))
        apagadas = await limpar_publicados(sessoes, timedelta(days=7))
        return apagadas, await _pendentes(sessoes)

    apagadas, pendentes = asyncio.run(go())
    assert apagadas == 2 and len(pendentes) == 1


# ------------------------------------------------------------------ topologia e entrega no RabbitMQ real


def _settings_de_teste(amqp_url):
    """Nomes únicos por teste para não interferir com outras execuções no mesmo broker."""
    s = uuid.uuid4().hex[:8]
    return Settings(
        postgres_url="postgresql+asyncpg://x:y@127.0.0.1:1/z", rabbitmq_url=amqp_url,
        rabbitmq_exchange=f"test.{s}.events", rabbitmq_dlx_exchange=f"test.{s}.dlx",
        fila_respostas=f"test.{s}.respostas", fila_respostas_dlq=f"test.{s}.respostas.dlq",
        fila_comandos_comunicacao=f"test.{s}.comandos", fila_compensacoes_dlq=f"test.{s}.compensacoes.dlq",
    )


async def _apagar(conn, settings):
    ch = await conn.channel()
    for fila in (settings.fila_respostas, settings.fila_respostas_dlq, settings.fila_comandos_comunicacao,
                 settings.fila_compensacoes_dlq):
        await ch.queue_delete(fila)
    await ch.exchange_delete(settings.rabbitmq_exchange)
    await ch.exchange_delete(settings.rabbitmq_dlx_exchange)


async def _receber(conn, fila):
    ch = await conn.channel()
    q = await ch.get_queue(fila)
    msg = await q.get(fail=False, timeout=2)
    if msg is not None:
        await msg.ack()
    return msg


def test_comando_do_passo3_chega_na_fila_do_ms_comunicacao(sessoes, amqp_url):
    """A fila de comandos é declarada pelo orquestrador: o comando não se perde sem o ms-comunicacao no ar."""
    settings = _settings_de_teste(amqp_url)

    async def go():
        conn, exchange = await conectar(settings)
        try:
            saga = await _saga_ate_o_passo3(sessoes)
            await publicar_pendentes(sessoes, exchange)
            return saga, await _receber(conn, settings.fila_comandos_comunicacao)
        finally:
            await _apagar(conn, settings)
            await conn.close()

    saga, msg = asyncio.run(go())
    assert msg is not None and msg.message_id == f"saga-{saga.saga_id}-step3"
    assert msg.routing_key == "saga.comando.comunicacao.programar-lembrete"
    assert json.loads(msg.body)["sagaId"] == str(saga.saga_id)


def test_compensacao_falha_chega_na_dlq_de_compensacoes(sessoes, amqp_url):
    settings = _settings_de_teste(amqp_url)
    politica = Politica(max_retries=0)

    async def go():
        conn, exchange = await conectar(settings)
        try:
            saga = (await repo.criar(sessoes, doador_id="d1", slot_id="s", agora=AGORA, max_retries=0)).saga
            for ev in (PassoConcluido(Passo.STEP1, {"dataHoraInicio": "x"}), PassoRecusado(Passo.STEP2, {"status": 422}),
                       FalhaTecnica(Passo.STEP1, "500")):
                saga = await repo.aplicar_transicao(sessoes, saga, transicionar(repo.estado_de(saga), ev, politica), agora=AGORA)
            await publicar_pendentes(sessoes, exchange)
            return saga, await _receber(conn, settings.fila_compensacoes_dlq)
        finally:
            await _apagar(conn, settings)
            await conn.close()

    saga, msg = asyncio.run(go())
    assert saga.status == "COMPENSATION_FAILED"
    assert msg is not None and json.loads(msg.body)["status"] == "COMPENSATION_FAILED"


def test_resposta_do_ms_comunicacao_chega_na_fila_de_respostas(amqp_url):
    settings = _settings_de_teste(amqp_url)

    async def go():
        conn, exchange = await conectar(settings)
        try:
            await exchange.publish(aio_pika.Message(b'{"resultado": "PROGRAMADO"}', message_id="m1"),
                                   routing_key="comunicacao.lembrete.programado")
            return await _receber(conn, settings.fila_respostas)
        finally:
            await _apagar(conn, settings)
            await conn.close()

    msg = asyncio.run(go())
    assert msg is not None and msg.message_id == "m1"


def test_topologia_e_idempotente(amqp_url):
    settings = _settings_de_teste(amqp_url)

    async def go():
        for _ in range(2):  # várias réplicas subindo: redeclarar com os mesmos argumentos não falha
            conn, _ = await conectar(settings)
            await conn.close()
        conn, _ = await conectar(settings)
        await _apagar(conn, settings)
        await conn.close()

    asyncio.run(go())


def test_compensacao_concluida_nao_publica_dlq(sessoes):
    """Sanidade: uma compensação bem-sucedida publica o desfecho, não a DLQ."""

    async def go():
        saga = (await repo.criar(sessoes, doador_id="d1", slot_id="s", agora=AGORA, max_retries=5)).saga
        for ev in (PassoConcluido(Passo.STEP1, {"dataHoraInicio": "x"}), PassoRecusado(Passo.STEP2, {"status": 422}),
                   CompensacaoConcluida(Passo.STEP1)):
            saga = await repo.aplicar_transicao(sessoes, saga, transicionar(repo.estado_de(saga), ev, Politica()), agora=AGORA)
        exchange = ExchangeFalsa()
        await publicar_pendentes(sessoes, exchange)
        return [r for r, _ in exchange.publicadas]

    assert asyncio.run(go()) == ["saga.agendamento.compensado"]
