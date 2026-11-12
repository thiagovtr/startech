"""Modelo de escrita (Command Store) no PostgreSQL: campanhas e Outbox."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Integer, String, func, text
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
    status: Mapped[str] = mapped_column(String(20), default="ATIVA")
    data_inicio: Mapped[date] = mapped_column(Date)
    data_fim: Mapped[date] = mapped_column(Date)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        # O id precisa existir antes do flush para ser referenciado no evento do Outbox.
        kwargs.setdefault("id", _novo_id())
        super().__init__(**kwargs)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_novo_id)
    aggregate_type: Mapped[str] = mapped_column(String(50))
    aggregate_id: Mapped[str] = mapped_column(String(36))
    event_type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSONB)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    publicado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tentativas: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Acelera o polling do publicador (Bloco 13): só eventos ainda não publicados.
    __table_args__ = (
        Index(
            "ix_outbox_events_pendentes",
            "criado_em",
            postgresql_where=text("publicado_em IS NULL"),
        ),
    )
