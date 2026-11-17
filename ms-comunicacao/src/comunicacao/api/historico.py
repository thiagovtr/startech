"""Histórico auditável de notificações do doador (contratos §2: GET /api/v1/comunicacao/historico/{doadorId})."""

from datetime import datetime

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select

from comunicacao.models.orm import Notificacao

router = APIRouter(prefix="/api/v1/comunicacao", tags=["comunicacao"])


class NotificacaoOut(BaseModel):
    id: int
    tipo: str
    canal: str
    agendamentoId: str | None
    conteudo: str
    criadoEm: datetime


class HistoricoOut(BaseModel):
    doadorId: str
    total: int
    pagina: int
    tamanho: int
    itens: list[NotificacaoOut]


@router.get("/historico/{doador_id}", response_model=HistoricoOut)
async def historico(
    request: Request, doador_id: str, pagina: int = Query(1, ge=1), tamanho: int = Query(20, ge=1, le=100)
) -> HistoricoOut:
    """Notificações enviadas ao doador, da mais recente para a mais antiga. Doador sem histórico: lista vazia."""
    factory = request.app.state.session_factory
    async with factory() as session:
        total = await session.scalar(select(func.count()).where(Notificacao.doador_id == doador_id)) or 0
        linhas = (
            await session.scalars(
                select(Notificacao)
                .where(Notificacao.doador_id == doador_id)
                .order_by(Notificacao.criado_em.desc(), Notificacao.id.desc())
                .offset((pagina - 1) * tamanho)
                .limit(tamanho)
            )
        ).all()
    return HistoricoOut(
        doadorId=doador_id, total=total, pagina=pagina, tamanho=tamanho,
        itens=[
            NotificacaoOut(id=n.id, tipo=n.tipo, canal=n.canal, agendamentoId=n.agendamento_id, conteudo=n.conteudo,
                           criadoEm=n.criado_em)
            for n in linhas
        ],
    )
