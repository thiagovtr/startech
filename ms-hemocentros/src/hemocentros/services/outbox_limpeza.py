"""Retenção do Outbox: remove eventos já publicados após o período de retenção."""

import asyncio
import logging
from datetime import timedelta

from fastapi import FastAPI
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hemocentros.models.orm import OutboxEvent

logger = logging.getLogger(__name__)


async def limpar_publicados(
    factory: async_sessionmaker[AsyncSession], retencao: timedelta, lote: int = 1000
) -> int:
    """Apaga eventos `published = true` com `published_at` anterior a `agora - retencao`.

    Nunca toca em eventos pendentes. Apaga em lotes (transações curtas) para não segurar locks nem
    inflar o WAL; `SKIP LOCKED` permite várias réplicas limpando ao mesmo tempo. Devolve o total apagado.
    """
    total = 0
    while True:
        async with factory() as session, session.begin():
            ids = (
                select(OutboxEvent.id)
                .where(OutboxEvent.published.is_(True), OutboxEvent.published_at < func.now() - retencao)
                .limit(lote)
                .with_for_update(skip_locked=True)
            )
            resultado = await session.execute(delete(OutboxEvent).where(OutboxEvent.id.in_(ids)))
            apagados = resultado.rowcount  # type: ignore[attr-defined]  # CursorResult em DELETE
        total += apagados
        if apagados < lote:
            return total


async def executar_limpeza(app: FastAPI) -> None:
    """Laço do worker de retenção. Nunca derruba o serviço."""
    settings = app.state.settings
    retencao = timedelta(days=settings.outbox_retencao_dias)
    while True:
        try:
            apagados = await limpar_publicados(app.state.session_factory, retencao, settings.outbox_limpeza_lote)
            if apagados:
                logger.info("Outbox: %d eventos publicados removidos (retenção de %s)", apagados, retencao)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Limpeza do Outbox: %s", exc)
        await asyncio.sleep(settings.outbox_limpeza_intervalo)
