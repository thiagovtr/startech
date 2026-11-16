import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta

import aio_pika
import pytest
from sqlalchemy import select

from hemocentros.config import Settings
from hemocentros.db.postgres import create_session_factory
from hemocentros.messaging.rabbitmq import conectar
from hemocentros.models.orm import OutboxEvent
from hemocentros.services.outbox_publisher import publicar_pendentes


def _eventos(n: int) -> list[OutboxEvent]:
    base = datetime.now(UTC)
    return [
        OutboxEvent(
            aggregate_type="Campanha", aggregate_id=f"c{i}", routing_key="hemocentros.campanha.criada",
            payload={"id": f"c{i}"}, created_at=base + timedelta(milliseconds=i),
        )
        for i in range(n)
    ]


async def _semear(factory, n: int):
    async with factory() as s, s.begin():
        s.add_all(_eventos(n))


async def _estado(factory):
    async with factory() as s:
        return (await s.scalars(select(OutboxEvent).order_by(OutboxEvent.created_at))).all()


async def _topologia(amqp_url: str):
    """Exchange topic + fila de teste com binding `hemocentros.campanha.*`."""
    settings = Settings(rabbitmq_url=amqp_url, rabbitmq_exchange=f"test.{uuid.uuid4().hex[:8]}")
    conn, exchange = await conectar(settings)
    ch = await conn.channel()
    fila = await ch.declare_queue(exclusive=True)
    await fila.bind(exchange, routing_key="hemocentros.campanha.*")
    return conn, exchange, fila


async def _drenar(fila) -> list[aio_pika.IncomingMessage]:
    msgs = []
    while (m := await fila.get(fail=False, timeout=1)) is not None:
        await m.ack()
        msgs.append(m)
    return msgs


def test_publica_pendentes_em_ordem_e_marca_como_publicados(pg_engine, amqp_url):
    factory = create_session_factory(pg_engine)

    async def go():
        conn, exchange, fila = await _topologia(amqp_url)
        try:
            await _semear(factory, 5)
            n = await publicar_pendentes(factory, exchange, lote=50)
            n2 = await publicar_pendentes(factory, exchange, lote=50)  # nada pendente
            return n, n2, await _drenar(fila), await _estado(factory)
        finally:
            await conn.close()

    n, n2, msgs, estado = asyncio.run(go())
    assert (n, n2) == (5, 0)
    assert [json.loads(m.body)["id"] for m in msgs] == [f"c{i}" for i in range(5)]  # ordem de criação
    assert all(m.routing_key == "hemocentros.campanha.criada" for m in msgs)
    assert all(m.message_id == e.id for m, e in zip(msgs, estado, strict=True))
    assert all(e.published and e.published_at is not None for e in estado)


def test_workers_concorrentes_nao_duplicam_publicacao(pg_engine, amqp_url):
    factory = create_session_factory(pg_engine)

    async def go():
        conn, exchange, fila = await _topologia(amqp_url)
        try:
            await _semear(factory, 40)
            resultados = await asyncio.gather(*(publicar_pendentes(factory, exchange, lote=10) for _ in range(4)))
            while sum(resultados) < 40:  # esvazia o que sobrou do lote
                resultados.append(await publicar_pendentes(factory, exchange, lote=10))
            return sum(resultados), await _drenar(fila), await _estado(factory)
        finally:
            await conn.close()

    total, msgs, estado = asyncio.run(go())
    ids = [json.loads(m.body)["id"] for m in msgs]
    assert total == 40 and len(ids) == 40 and len(set(ids)) == 40  # sem duplicatas
    assert all(e.published for e in estado)


def test_falha_no_meio_do_lote_mantem_confirmados_e_pendentes_restantes(pg_engine):
    factory = create_session_factory(pg_engine)

    class ExchangeInstavel:
        def __init__(self):
            self.chamadas = 0

        async def publish(self, mensagem, routing_key):
            self.chamadas += 1
            if self.chamadas == 3:
                raise ConnectionError("broker caiu")

    async def go():
        await _semear(factory, 5)
        with pytest.raises(ConnectionError):
            await publicar_pendentes(factory, ExchangeInstavel(), lote=50)
        return await _estado(factory)

    estado = asyncio.run(go())
    assert [e.published for e in estado] == [True, True, False, False, False]


def test_tipo_da_exchange_e_configuravel(amqp_url):
    """O tipo configurado é aplicado: redeclarar a mesma exchange com outro tipo é rejeitado pelo broker."""
    nome = f"test.{uuid.uuid4().hex[:8]}"

    async def declarar(tipo: str):
        settings = Settings(rabbitmq_url=amqp_url, rabbitmq_exchange=nome, rabbitmq_exchange_type=tipo)
        conn, _ = await conectar(settings)
        await conn.close()

    asyncio.run(declarar("topic"))
    asyncio.run(declarar("topic"))  # mesmo tipo: idempotente
    with pytest.raises(aio_pika.exceptions.AMQPError):
        asyncio.run(declarar("direct"))  # tipo divergente: PRECONDITION_FAILED


def test_exchange_inexistente_sem_declarar_falha_claramente(amqp_url):
    settings = Settings(rabbitmq_url=amqp_url, rabbitmq_exchange="nao.existe.xyz", rabbitmq_declarar_exchange=False)
    with pytest.raises(aio_pika.exceptions.AMQPError):
        asyncio.run(conectar(settings))
