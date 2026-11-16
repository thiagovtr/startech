"""Resiliência a indisponibilidade do RabbitMQ (ADR-003 §5.3: zero perda, drenagem automática)."""

import asyncio
import uuid
from datetime import date
from types import SimpleNamespace

from pymongo import AsyncMongoClient
from sqlalchemy import select

from hemocentros.config import Settings
from hemocentros.db.postgres import create_session_factory
from hemocentros.messaging.rabbitmq import conectar
from hemocentros.models.campanha import CampanhaCriar
from hemocentros.models.orm import OutboxEvent
from hemocentros.services.campanhas import criar_campanha
from hemocentros.services.outbox_publisher import executar_publicador
from hemocentros.services.projecao import executar_consumidor
from tests.conftest import TEST_MONGO_DB, TEST_MONGO_URL

URL_INALCANCAVEL = "amqp://guest:guest@127.0.0.1:1/"


async def _espera(condicao, timeout: float = 10.0):
    fim = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < fim:
        if await condicao():
            return True
        await asyncio.sleep(0.1)
    return False


def _dados() -> CampanhaCriar:
    return CampanhaCriar(titulo="Alerta O-", hemocentro="Lavras", tipo_sanguineo="O-",
                         data_inicio=date(2026, 11, 10), data_fim=date(2026, 11, 30))


def test_publicador_mantem_pendente_sem_rabbitmq_e_drena_quando_volta(pg_engine, amqp_url):
    sufixo = uuid.uuid4().hex[:8]
    settings = Settings(rabbitmq_url=URL_INALCANCAVEL, rabbitmq_exchange=f"test.{sufixo}",
                        outbox_intervalo=0.1)
    factory = create_session_factory(pg_engine)
    app = SimpleNamespace(state=SimpleNamespace(settings=settings, session_factory=factory))

    async def publicado() -> bool:
        async with factory() as s:
            return all(e.published for e in (await s.scalars(select(OutboxEvent))).all())

    async def go():
        camp = await criar_campanha(factory, _dados())  # o POST continua funcionando sem broker
        tarefa = asyncio.create_task(executar_publicador(app))
        try:
            await asyncio.sleep(1.0)
            ainda_pendente = not await publicado()
            # prepara fila para receber e "religa" o broker
            conn, exchange = await conectar(Settings(rabbitmq_url=amqp_url, rabbitmq_exchange=settings.rabbitmq_exchange))
            ch = await conn.channel()
            fila = await ch.declare_queue(exclusive=True)
            await fila.bind(exchange, routing_key="hemocentros.campanha.*")
            settings.rabbitmq_url = amqp_url
            drenou = await _espera(publicado)
            msg = await fila.get(fail=False, timeout=2)
            await conn.close()
            return camp, ainda_pendente, drenou, msg
        finally:
            tarefa.cancel()
            await asyncio.gather(tarefa, return_exceptions=True)

    camp, ainda_pendente, drenou, msg = asyncio.run(go())
    assert ainda_pendente, "evento não pode ser marcado como publicado sem o broker"
    assert drenou and msg is not None and msg.message_id


def test_consumidor_reconecta_quando_rabbitmq_volta(mongo_view, amqp_url):
    sufixo = uuid.uuid4().hex[:8]
    settings = Settings(rabbitmq_url=URL_INALCANCAVEL, rabbitmq_exchange=f"test.{sufixo}",
                        rabbitmq_queue=f"test.cqrs.{sufixo}", mongo_db=TEST_MONGO_DB, consumidor_reconexao=0.2)

    async def go():
        mongo = AsyncMongoClient(TEST_MONGO_URL, serverSelectionTimeoutMS=1000)
        app = SimpleNamespace(state=SimpleNamespace(settings=settings, mongo_client=mongo))
        tarefa = asyncio.create_task(executar_consumidor(app))
        try:
            await asyncio.sleep(0.8)  # várias tentativas falhas: o consumidor não pode morrer
            vivo = not tarefa.done()
            settings.rabbitmq_url = amqp_url
            conn, exchange = await conectar(settings)  # declara a exchange; o consumidor declara a fila
            await asyncio.sleep(1.0)
            import aio_pika
            await exchange.publish(aio_pika.Message(body=b'{"id": "r1", "tipo_sanguineo": "O-"}'),
                                   routing_key="hemocentros.campanha.criada")

            async def projetado():
                return await mongo[TEST_MONGO_DB]["campanhas_view"].count_documents({"_id": "r1"}) == 1

            ok = await _espera(projetado)
            await conn.close()
            return vivo, ok
        finally:
            tarefa.cancel()
            await asyncio.gather(tarefa, return_exceptions=True)
            await mongo.close()

    vivo, ok = asyncio.run(go())
    assert vivo and ok
