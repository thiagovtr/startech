import asyncio
import uuid

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from hemocentros.db.migracoes import aplicar_migracoes
from hemocentros.models.orm import Base
from tests.conftest import TEST_PG_URL


@pytest.fixture
def banco_vazio(pg_engine):
    """Um banco novo e vazio por teste (criado e removido no PostgreSQL de teste)."""
    nome = f"mig_{uuid.uuid4().hex[:10]}"
    admin = create_async_engine(TEST_PG_URL, poolclass=NullPool, isolation_level="AUTOCOMMIT")

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
            indices = {i["name"] for i in ins.get_indexes("outbox_events")} if "outbox_events" in tabelas else set()
            versao = sc.execute(text("SELECT version_num FROM alembic_version")).scalar() if "alembic_version" in tabelas else None
            return tabelas, indices, versao
        return await c.run_sync(ler)


def test_banco_vazio_vai_ate_a_ultima_revisao(banco_vazio):
    asyncio.run(aplicar_migracoes(banco_vazio))
    tabelas, indices, versao = asyncio.run(_estado(banco_vazio))
    assert {"campanhas", "outbox_events", "alembic_version"} <= tabelas
    assert {"idx_outbox_unpublished", "idx_outbox_published_at"} <= indices
    assert versao == "0002"


def test_migracoes_correspondem_aos_modelos(banco_vazio):
    """Se alguém mudar o ORM sem criar migração, este teste falha."""
    asyncio.run(aplicar_migracoes(banco_vazio))

    async def diff():
        async with banco_vazio.connect() as c:
            return await c.run_sync(
                lambda sc: compare_metadata(MigrationContext.configure(sc, opts={"compare_type": True}), Base.metadata)
            )

    assert asyncio.run(diff()) == []


def test_banco_legado_do_create_all_e_adotado_sem_perder_dados(banco_vazio):
    async def go():
        async with banco_vazio.begin() as c:  # esquema antigo: create_all, sem o índice da P3 e sem alembic_version
            await c.run_sync(Base.metadata.create_all)
            await c.execute(text("DROP INDEX idx_outbox_published_at"))
            await c.execute(text(
                "INSERT INTO campanhas (id, titulo, hemocentro, tipo_sanguineo, urgencia, status, data_inicio, data_fim)"
                " VALUES ('c1', 'Antiga', 'Lavras', 'O-', 'NORMAL', 'ATIVA', '2026-11-01', '2026-11-30')"))
        await aplicar_migracoes(banco_vazio)
        async with banco_vazio.connect() as c:
            n = (await c.execute(text("SELECT count(*) FROM campanhas"))).scalar()
        return n, await _estado(banco_vazio)

    n, (_, indices, versao) = asyncio.run(go())
    assert n == 1 and versao == "0002" and "idx_outbox_published_at" in indices


def test_idempotente_e_seguro_com_replicas_concorrentes(banco_vazio):
    async def go():
        await asyncio.gather(*[aplicar_migracoes(banco_vazio) for _ in range(3)])  # advisory lock serializa
        await aplicar_migracoes(banco_vazio)
        return await _estado(banco_vazio)

    assert asyncio.run(go())[2] == "0002"
