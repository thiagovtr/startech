import asyncio
import uuid

import aio_pika
from pymongo import AsyncMongoClient

from hemocentros.config import Settings
from hemocentros.messaging.rabbitmq import conectar
from hemocentros.services.projecao import iniciar_consumo
from tests.conftest import TEST_MONGO_DB, TEST_MONGO_URL


def _settings(amqp_url: str, **extra) -> Settings:
    s = uuid.uuid4().hex[:8]
    return Settings(
        rabbitmq_url=amqp_url, rabbitmq_exchange=f"test.{s}", rabbitmq_queue=f"test.cqrs.{s}",
        rabbitmq_dlx_exchange=f"test.dlx.{s}", rabbitmq_dlq_queue=f"test.cqrs.dlq.{s}",
        mongo_db=TEST_MONGO_DB, **extra,
    )


async def _publicar_e_aguardar(settings: Settings, corpos: list[bytes]):
    """Consome com a projeção, publica os corpos e devolve (mensagens da DLQ, ainda na fila principal)."""
    mongo = AsyncMongoClient(TEST_MONGO_URL, serverSelectionTimeoutMS=1500)
    pub_conn, exchange = await conectar(settings)
    consumo = await iniciar_consumo(settings, mongo)
    try:
        for corpo in corpos:
            await exchange.publish(aio_pika.Message(body=corpo), routing_key="hemocentros.campanha.criada")
        await asyncio.sleep(1.5)
        ch = await pub_conn.channel()
        dlq = await ch.declare_queue(settings.rabbitmq_dlq_queue, passive=True)
        mortas = []
        while (m := await dlq.get(fail=False, timeout=1)) is not None:
            await m.ack()
            mortas.append(m)
        principal = await ch.declare_queue(settings.rabbitmq_queue, passive=True)
        return mortas, principal.declaration_result.message_count
    finally:
        await consumo.close()
        await pub_conn.close()
        await mongo.close()


def test_mensagem_invalida_vai_para_a_dlq(mongo_view, amqp_url):
    settings = _settings(amqp_url, rabbitmq_dlq_habilitada=True)
    mortas, na_fila = asyncio.run(_publicar_e_aguardar(settings, [b"nao-e-json", b'{"id": "ok1", "tipo_sanguineo": "O-"}', b"[1]"]))
    assert sorted(m.body for m in mortas) == [b"[1]", b"nao-e-json"]
    assert na_fila == 0
    assert mortas[0].routing_key == settings.rabbitmq_dlq_routing_key
    assert mortas[0].headers["x-first-death-reason"] == "rejected"  # o motivo fica registrado pelo broker
    assert mongo_view.count_documents({"_id": "ok1"}) == 1  # a mensagem válida foi projetada normalmente


def test_sem_dlq_habilitada_a_mensagem_invalida_e_descartada(mongo_view, amqp_url):
    """Comportamento anterior preservado: DLQ desligada não altera a fila principal nem cria a DLQ."""
    settings = _settings(amqp_url)

    async def go():
        mongo = AsyncMongoClient(TEST_MONGO_URL, serverSelectionTimeoutMS=1500)
        pub_conn, exchange = await conectar(settings)
        consumo = await iniciar_consumo(settings, mongo)
        try:
            await exchange.publish(aio_pika.Message(body=b"lixo"), routing_key="hemocentros.campanha.criada")
            await asyncio.sleep(1.0)
            ch = await pub_conn.channel()
            try:
                await ch.declare_queue(settings.rabbitmq_dlq_queue, passive=True)
                return True
            except Exception:
                return False
        finally:
            await consumo.close()
            await pub_conn.close()
            await mongo.close()

    assert asyncio.run(go()) is False
