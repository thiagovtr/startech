"""Disparo dos lembretes pré-doação (D-1) programados pelo passo 3 da SAGA.

`FOR UPDATE SKIP LOCKED` permite várias réplicas sem enviar o mesmo lembrete duas vezes. Lembrete cancelado
(compensação) nunca é enviado: só os `PROGRAMADO` com `programado_para` vencido são selecionados.
"""

import asyncio
import logging
from datetime import UTC, datetime

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from comunicacao.models.orm import Lembrete, Notificacao, StatusLembrete, TipoNotificacao
from comunicacao.services import canais

logger = logging.getLogger(__name__)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


async def enviar_vencidos(
    factory: async_sessionmaker[AsyncSession], lote: int = 50, agora: datetime | None = None
) -> int:
    """Envia até `lote` lembretes vencidos e os marca como ENVIADO. Devolve quantos enviou."""
    agora = agora or datetime.now(UTC)
    notificacoes: list[Notificacao] = []
    async with factory() as session, session.begin():
        lembretes = (
            await session.scalars(
                select(Lembrete)
                .where(Lembrete.status == StatusLembrete.PROGRAMADO, Lembrete.programado_para <= agora)
                .order_by(Lembrete.programado_para)
                .limit(lote)
                .with_for_update(skip_locked=True)
            )
        ).all()
        for lembrete in lembretes:
            lembrete.status, lembrete.enviado_em, lembrete.atualizado_em = StatusLembrete.ENVIADO, agora, agora
            notificacao = Notificacao(
                doador_id=lembrete.doador_id, agendamento_id=lembrete.agendamento_id, tipo=TipoNotificacao.LEMBRETE,
                canal=canais.CANAL_PADRAO,
                conteudo=f"Lembrete: sua doação de sangue está marcada para {_iso(lembrete.data_hora_inicio)}.",
            )
            session.add(notificacao)
            notificacoes.append(notificacao)
    for n in notificacoes:
        canais.enviar(n)
    return len(notificacoes)


async def executar_lembretes(app: FastAPI) -> None:
    """Laço do worker de lembretes. Nunca derruba o serviço."""
    settings = app.state.settings
    while True:
        try:
            if await enviar_vencidos(app.state.session_factory, settings.lembretes_lote) > 0:
                continue
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Disparo de lembretes: %s", exc)
        await asyncio.sleep(settings.lembretes_intervalo)
