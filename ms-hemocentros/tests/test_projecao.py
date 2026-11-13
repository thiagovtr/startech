import asyncio
import uuid
from datetime import date

import pytest
from pymongo import AsyncMongoClient

from hemocentros.config import Settings
from hemocentros.db.postgres import create_session_factory
from hemocentros.messaging.rabbitmq import conectar
from hemocentros.models.campanha import CampanhaCriar
from hemocentros.repositories import campanhas_view, campanhas_view_escrita
from hemocentros.services.campanhas import criar_campanha
from hemocentros.services.outbox_publisher import publicar_pendentes
from hemocentros.services.projecao import iniciar_consumo, tratar_mensagem
from tests.conftest import TEST_MONGO_DB, TEST_MONGO_URL

PAYLOAD = {"id": "c1", "titulo": "Alerta O-", "hemocentro": "Lavras", "tipo_sanguineo": "O-",
           "urgencia": "CRITICO", "status": "ATIVA", "data_inicio": "2026-11-10", "data_fim": "2026-11-30"}


class MsgFake:
    def __init__(self, body: bytes):
        self.body, self.acao = body, None

    async def ack(self):
        self.acao = "ack"

    async def nack(self, requeue=True):
        self.acao = f"nack(requeue={requeue})"

    async def reject(self, requeue=False):
        self.acao = f"reject(requeue={requeue})"


def _mongo(url=TEST_MONGO_URL):
    return AsyncMongoClient(url, serverSelectionTimeoutMS=500)


def test_upsert_idempotente_e_atualiza(mongo_view):
    async def go():
        mongo = _mongo()
        await campanhas_view_escrita.upsert(mongo, TEST_MONGO_DB, PAYLOAD)
        await campanhas_view_escrita.upsert(mongo, TEST_MONGO_DB, PAYLOAD)  # reprocessamento
        await campanhas_view_escrita.upsert(mongo, TEST_MONGO_DB, {**PAYLOAD, "titulo": "Novo título"})
        docs, _ = await campanhas_view.listar(mongo, TEST_MONGO_DB)
        await mongo.close()
        return docs

    docs = asyncio.run(go())
    assert len(docs) == 1 and docs[0]["id"] == "c1" and docs[0]["titulo"] == "Novo título"


def test_tratar_mensagem_ack_so_apos_gravar(mongo_view):
    msg = MsgFake(b'{"id": "c9", "titulo": "x", "tipo_sanguineo": "O-"}')

    async def go():
        mongo = _mongo()
        await tratar_mensagem(msg, mongo, TEST_MONGO_DB)
        await mongo.close()

    asyncio.run(go())
    assert msg.acao == "ack" and mongo_view.count_documents({"_id": "c9"}) == 1


@pytest.mark.parametrize("corpo", [b"nao-e-json", b"[1, 2]", b'{"sem": "id"}'])
def test_mensagem_invalida_e_descartada_sem_requeue(mongo_view, corpo):
    msg = MsgFake(corpo)
    asyncio.run(tratar_mensagem(msg, _mongo(), TEST_MONGO_DB))
    assert msg.acao == "reject(requeue=False)" and mongo_view.count_documents({}) == 0


def test_mongo_fora_devolve_a_fila_sem_ack():
    msg = MsgFake(b'{"id": "c1"}')
    asyncio.run(tratar_mensagem(msg, _mongo("mongodb://127.0.0.1:1"), TEST_MONGO_DB, espera_erro=0))
    assert msg.acao == "nack(requeue=True)"  # nunca confirma sem ter gravado


def test_fluxo_completo_postgres_outbox_rabbitmq_mongo(pg_engine, mongo_view, amqp_url):
    """POST (PostgreSQL+Outbox) -> publicador -> RabbitMQ -> consumidor -> MongoDB, com reentrega duplicada."""
    sufixo = uuid.uuid4().hex[:8]
    settings = Settings(
        rabbitmq_url=amqp_url, rabbitmq_exchange=f"test.{sufixo}", rabbitmq_queue=f"test.cqrs.{sufixo}",
        mongo_url=TEST_MONGO_URL, mongo_db=TEST_MONGO_DB,
    )
    factory = create_session_factory(pg_engine)

    async def go():
        mongo = _mongo()
        consumo = await iniciar_consumo(settings, mongo)
        pub_conn, exchange = await conectar(settings)
        try:
            camp = await criar_campanha(factory, CampanhaCriar(
                titulo="Doação Urgente O-", hemocentro="Lavras", tipo_sanguineo="O-", urgencia="CRITICO",
                data_inicio=date(2026, 11, 10), data_fim=date(2026, 11, 30)))
            assert await publicar_pendentes(factory, exchange) == 1
            # reentrega do mesmo evento (at-least-once): não pode duplicar
            import aio_pika
            await exchange.publish(aio_pika.Message(body=b'{"id": "%s"}' % camp.id.encode()),
                                   routing_key="hemocentros.campanha.criada")
            for _ in range(40):  # aguarda a projeção (consistência eventual)
                docs, _ = await campanhas_view.listar(mongo, TEST_MONGO_DB, "O-")
                if docs:
                    break
                await asyncio.sleep(0.1)
            await asyncio.sleep(0.5)
            return camp, (await campanhas_view.listar(mongo, TEST_MONGO_DB))[0]
        finally:
            await pub_conn.close()
            await consumo.close()
            await mongo.close()

    camp, docs = asyncio.run(go())
    assert [d["id"] for d in docs] == [camp.id]
    assert mongo_view.count_documents({}) == 1
