import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from hemocentros.db.postgres import create_session_factory
from hemocentros.models.orm import OutboxEvent
from hemocentros.services.outbox_limpeza import limpar_publicados

AGORA = datetime.now(UTC)


def _evento(id_: str, published: bool, published_ha: timedelta | None) -> OutboxEvent:
    return OutboxEvent(
        id=id_, aggregate_type="Campanha", aggregate_id=id_, routing_key="hemocentros.campanha.criada",
        payload={"id": id_}, published=published,
        published_at=AGORA - published_ha if published_ha is not None else None,
    )


async def _ids(factory) -> set[str]:
    async with factory() as s:
        return set((await s.scalars(select(OutboxEvent.id))).all())


def test_remove_so_publicados_fora_da_retencao(pg_engine):
    factory = create_session_factory(pg_engine)

    async def go():
        async with factory() as s, s.begin():
            s.add_all([
                _evento("velho", True, timedelta(days=8)),
                _evento("recente", True, timedelta(days=1)),
                _evento("pendente", False, None),
                _evento("pendente-antigo", False, None),  # pendente nunca é removido, por mais velho que seja
            ])
        apagados = await limpar_publicados(factory, timedelta(days=7))
        return apagados, await _ids(factory)

    apagados, restantes = asyncio.run(go())
    assert apagados == 1
    assert restantes == {"recente", "pendente", "pendente-antigo"}


def test_apaga_em_varios_lotes_e_e_idempotente(pg_engine):
    factory = create_session_factory(pg_engine)

    async def go():
        async with factory() as s, s.begin():
            s.add_all([_evento(f"v{i}", True, timedelta(days=30)) for i in range(7)])
            s.add(_evento("p", False, None))
        primeira = await limpar_publicados(factory, timedelta(days=7), lote=3)  # 3 + 3 + 1
        segunda = await limpar_publicados(factory, timedelta(days=7), lote=3)
        return primeira, segunda, await _ids(factory)

    primeira, segunda, restantes = asyncio.run(go())
    assert (primeira, segunda, restantes) == (7, 0, {"p"})


def test_limpezas_concorrentes_nao_conflitam(pg_engine):
    factory = create_session_factory(pg_engine)

    async def go():
        async with factory() as s, s.begin():
            s.add_all([_evento(f"v{i}", True, timedelta(days=30)) for i in range(20)])
        totais = await asyncio.gather(*[limpar_publicados(factory, timedelta(days=7), lote=4) for _ in range(3)])
        return sum(totais), await _ids(factory)

    total, restantes = asyncio.run(go())
    assert total == 20 and restantes == set()  # cada evento é apagado exatamente uma vez
