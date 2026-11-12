import asyncio
from datetime import date

import pytest
from sqlalchemy import inspect, select

from hemocentros.db.postgres import criar_esquema, create_session_factory
from hemocentros.models.orm import CampanhaModel, OutboxEvent


def _run(coro):
    return asyncio.run(coro)


def test_esquema_criado_e_idempotente(pg_engine):
    async def go():
        await criar_esquema(pg_engine)  # segunda chamada não pode falhar
        async with pg_engine.connect() as conn:
            return await conn.run_sync(lambda c: set(inspect(c).get_table_names()))

    assert {"campanhas", "outbox_events"} <= _run(go())


def _campanha() -> CampanhaModel:
    return CampanhaModel(
        titulo="Alerta O-", hemocentro="Hemocentro Lavras", tipo_sanguineo="O-",
        data_inicio=date(2026, 11, 10), data_fim=date(2026, 11, 30),
    )


def test_campanha_e_evento_na_mesma_transacao(pg_engine):
    factory = create_session_factory(pg_engine)

    async def go():
        async with factory() as s, s.begin():
            c = _campanha()
            s.add(c)
            s.add(OutboxEvent(aggregate_type="campanha", aggregate_id=c.id,
                              routing_key="hemocentros.campanha.criada", payload={"id": c.id}))
        async with factory() as s:
            camps = (await s.scalars(select(CampanhaModel))).all()
            evs = (await s.scalars(select(OutboxEvent))).all()
            return camps, evs

    camps, evs = _run(go())
    assert len(camps) == 1 and len(evs) == 1
    assert evs[0].aggregate_id == camps[0].id
    assert evs[0].published is False and evs[0].published_at is None
    assert camps[0].status == "ATIVA" and camps[0].criada_em is not None


def test_falha_na_transacao_nao_deixa_evento_orfao(pg_engine):
    factory = create_session_factory(pg_engine)

    async def go():
        with pytest.raises(RuntimeError):
            async with factory() as s, s.begin():
                c = _campanha()
                s.add(c)
                s.add(OutboxEvent(aggregate_type="campanha", aggregate_id=c.id,
                                  routing_key="hemocentros.campanha.criada", payload={}))
                await s.flush()
                raise RuntimeError("falha após gravar")
        async with factory() as s:
            return (await s.scalars(select(CampanhaModel))).all(), (await s.scalars(select(OutboxEvent))).all()

    camps, evs = _run(go())
    assert camps == [] and evs == []
