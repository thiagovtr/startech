"""Modelo de escrita (Command Store) no PostgreSQL: campanhas e Outbox."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _novo_id() -> str:
    return str(uuid.uuid4())


class CampanhaModel(Base):
    __tablename__ = "campanhas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_novo_id)
    titulo: Mapped[str] = mapped_column(String(200))
    hemocentro: Mapped[str] = mapped_column(String(200))
    tipo_sanguineo: Mapped[str] = mapped_column(String(3), index=True)
    urgencia: Mapped[str] = mapped_column(String(20), default="NORMAL", server_default="NORMAL")
    status: Mapped[str] = mapped_column(String(20), default="ATIVA")
    data_inicio: Mapped[date] = mapped_column(Date)
    data_fim: Mapped[date] = mapped_column(Date)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Versão do estado da campanha: incrementar a cada alteração e enviar no evento (projeção versionada).
    versao: Mapped[int] = mapped_column(Integer, default=1, server_default="1")

    def __init__(self, **kwargs):
        # O id precisa existir antes do flush para ser referenciado no evento do Outbox.
        kwargs.setdefault("id", _novo_id())
        kwargs.setdefault("versao", 1)
        super().__init__(**kwargs)


class OutboxEvent(Base):
    """Esquema conforme ADR (Transactional Outbox)."""

    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_novo_id)
    aggregate_type: Mapped[str] = mapped_column(String(64))
    aggregate_id: Mapped[str] = mapped_column(String(64))
    routing_key: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Correlation id da requisição que gerou o evento (observabilidade ponta a ponta).
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Acelera o polling do publicador: só eventos ainda não publicados.
    __table_args__ = (
        Index("idx_outbox_unpublished", "created_at", postgresql_where=text("published = false")),
        # Acelera a limpeza de retenção: só eventos já publicados, por data de publicação.
        Index("idx_outbox_published_at", "published_at", postgresql_where=text("published = true")),
    )
