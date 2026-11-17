"""Banco próprio do ms-comunicacao: lembretes, histórico de notificações, inbox, Outbox e rejeitadas."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _novo_id() -> str:
    return str(uuid.uuid4())


class StatusLembrete:
    PROGRAMADO = "PROGRAMADO"
    CANCELADO = "CANCELADO"
    ENVIADO = "ENVIADO"


class TipoNotificacao:
    CONFIRMACAO = "CONFIRMACAO"
    LEMBRETE = "LEMBRETE"
    CANCELAMENTO = "CANCELAMENTO"
    DESFECHO = "DESFECHO"
    CAMPANHA = "CAMPANHA"


class Lembrete(Base):
    """Lembrete pré-doação (D-1) programado pelo passo 3 da SAGA. Um por agendamento."""

    __tablename__ = "lembretes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_novo_id)
    agendamento_id: Mapped[str] = mapped_column(String(64), unique=True)
    saga_id: Mapped[str] = mapped_column(String(64))
    doador_id: Mapped[str] = mapped_column(String(64), index=True)
    slot_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    data_hora_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    programado_para: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))
    enviado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Polling do disparo: só os ainda programados, pela hora de envio
        Index("idx_lembretes_pendentes", "programado_para", postgresql_where=text("status = 'PROGRAMADO'")),
    )


class Notificacao(Base):
    """Histórico auditável do que foi enviado ao doador (GET /api/v1/comunicacao/historico/{doadorId})."""

    __tablename__ = "notificacoes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    doador_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agendamento_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tipo: Mapped[str] = mapped_column(String(16))
    canal: Mapped[str] = mapped_column(String(16))
    conteudo: Mapped[str] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_notificacoes_doador", "doador_id", "criado_em"),)


class OutboxEvent(Base):
    """Transactional Outbox (ADR-003 §5.1), mesmo esquema do ms-orquestrador."""

    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_novo_id)
    aggregate_type: Mapped[str] = mapped_column(String(64))
    aggregate_id: Mapped[str] = mapped_column(String(64))
    routing_key: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict] = mapped_column(JSONB)
    # message_id AMQP (chave de deduplicação no consumidor; contratos §2.1)
    message_id: Mapped[str] = mapped_column(String(128), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    __table_args__ = (
        Index("idx_outbox_unpublished", "created_at", postgresql_where=text("published = false")),
        Index("idx_outbox_published_at", "published_at", postgresql_where=text("published = true")),
    )


class MensagemProcessada(Base):
    """Inbox idempotente: message_id das mensagens já processadas (entrega at-least-once)."""

    __tablename__ = "processed_messages"

    message_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MensagemRejeitada(Base):
    """Comandos ilegíveis da fila da SAGA, que não tem DLQ (fila sem argumentos, contratos §2.1)."""

    __tablename__ = "mensagens_rejeitadas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fila: Mapped[str] = mapped_column(String(128))
    message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    routing_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    motivo: Mapped[str] = mapped_column(Text)
    corpo: Mapped[str] = mapped_column(Text)
    recebida_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
