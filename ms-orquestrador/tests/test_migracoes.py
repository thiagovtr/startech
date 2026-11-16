import asyncio
import uuid

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from orquestrador.db.migracoes import aplicar_migracoes
from orquestrador.models.orm import Base
from tests.conftest import TEST_PG_URL


@pytest.fixture
def banco_vazio(pg_engine):
    """Um banco novo e vazio por teste (criado e removido no PostgreSQL de teste)."""
    nome = f"mig_{uuid.uuid4().hex[:10]}"
    admin = create_async_engine(
        make_url(TEST_PG_URL).set(database="postgres"), poolclass=NullPool, isolation_level="AUTOCOMMIT"
    )

    async def _exec(sql):
        async with admin.connect() as c:
            await c.execute(text(sql))

    asyncio.run(_exec(f"CREATE DATABASE {nome}"))
    engine = create_async_engine(make_url(TEST_PG_URL).set(database=nome), poolclass=NullPool)
    yield engine
    asyncio.run(engine.dispose())
    asyncio.run(_exec(f"DROP DATABASE {nome} WITH (FORCE)"))
    asyncio.run(admin.dispose())


async def _estado(engine):
    async with engine.connect() as c:
        def ler(sc):
            ins = inspect(sc)
            tabelas = set(ins.get_table_names())
            indices = {i["name"] for i in ins.get_indexes("saga_execution_state")} if "saga_execution_state" in tabelas else set()
            versao = sc.execute(text("SELECT version_num FROM alembic_version")).scalar() if "alembic_version" in tabelas else None
            return tabelas, indices, versao
        return await c.run_sync(ler)


def test_banco_vazio_vai_ate_a_ultima_revisao(banco_vazio):
    asyncio.run(aplicar_migracoes(banco_vazio))
    tabelas, indices, versao = asyncio.run(_estado(banco_vazio))
    assert {"saga_execution_state", "saga_step_log", "outbox_events", "processed_messages"} <= tabelas
    assert {"uq_saga_ativa_por_doador", "idx_saga_pendentes"} <= indices
    assert versao == "0001"


def test_migracoes_correspondem_aos_modelos(banco_vazio):
    """Se alguém mudar o ORM sem criar migração, este teste falha."""
    asyncio.run(aplicar_migracoes(banco_vazio))

    async def diff():
        async with banco_vazio.connect() as c:
            return await c.run_sync(
                lambda sc: compare_metadata(MigrationContext.configure(sc, opts={"compare_type": True}), Base.metadata)
            )

    assert asyncio.run(diff()) == []


def test_idempotente_e_seguro_com_replicas_concorrentes(banco_vazio):
    async def go():
        await asyncio.gather(*[aplicar_migracoes(banco_vazio) for _ in range(3)])  # advisory lock serializa
        await aplicar_migracoes(banco_vazio)
        return await _estado(banco_vazio)

    assert asyncio.run(go())[2] == "0001"


_INSERIR = (
    "INSERT INTO saga_execution_state (saga_id, agendamento_id, doador_id, slot_id, current_step, status, payload)"
    " VALUES (:id, :ag, :doador, 'slot-1', 'STEP1', :status, '{}')"
)


async def _inserir(engine, doador: str, status: str) -> None:
    async with engine.begin() as c:
        await c.execute(text(_INSERIR), {"id": uuid.uuid4(), "ag": uuid.uuid4().hex, "doador": doador, "status": status})


def test_rn09_uma_saga_em_andamento_por_doador(pg_engine):
    asyncio.run(_inserir(pg_engine, "d1", "STARTED"))
    with pytest.raises(IntegrityError):
        asyncio.run(_inserir(pg_engine, "d1", "SLOT_RESERVED"))
    asyncio.run(_inserir(pg_engine, "d2", "STARTED"))  # outro doador não é afetado


@pytest.mark.parametrize("final", ["CONFIRMED", "REJECTED", "COMPENSATED", "COMPENSATION_FAILED"])
def test_rn09_saga_finalizada_libera_nova_saga(pg_engine, final):
    asyncio.run(_inserir(pg_engine, "d1", final))
    asyncio.run(_inserir(pg_engine, "d1", "STARTED"))
    asyncio.run(_inserir(pg_engine, "d1", final))  # várias finalizadas convivem


def test_message_id_do_outbox_e_unico(pg_engine):
    sql = text(
        "INSERT INTO outbox_events (id, aggregate_type, aggregate_id, routing_key, payload, message_id)"
        " VALUES (:id, 'Saga', 's1', 'saga.x', '{}', 'saga-s1-step3')"
    )

    async def go():
        async with pg_engine.begin() as c:
            await c.execute(sql, {"id": str(uuid.uuid4())})
        async with pg_engine.begin() as c:
            await c.execute(sql, {"id": str(uuid.uuid4())})

    with pytest.raises(IntegrityError):
        asyncio.run(go())
