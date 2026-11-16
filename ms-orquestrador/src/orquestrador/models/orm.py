"""Banco próprio do orquestrador: estado da SAGA, log de passos, Outbox e mensagens já processadas."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# Status finais da SAGA: fora deles a SAGA está "em andamento" (índices parciais abaixo).
# Os demais status e as transições ficam em `orquestrador.saga` (máquina de estados).
STATUS_TERMINAIS = ("CONFIRMED", "REJECTED", "COMPENSATED", "COMPENSATION_FAILED")
_EM_ANDAMENTO = text("status NOT IN ('CONFIRMED', 'REJECTED', 'COMPENSATED', 'COMPENSATION_FAILED')")


def _novo_id() -> str:
    return str(uuid.uuid4())


class SagaExecucao(Base):
    """Estado de uma SAGA de agendamento (ADR-002 §5.1, ADR-006)."""

    __tablename__ = "saga_execution_state"

    saga_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo: Mapped[str] = mapped_column(String(32), default="AGENDAMENTO", server_default="AGENDAMENTO")
    agendamento_id: Mapped[str] = mapped_column(String(64), unique=True)
    doador_id: Mapped[str] = mapped_column(String(64))
    slot_id: Mapped[str] = mapped_column(String(64))
    current_step: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    # Dados acumulados ao longo dos passos (ex.: dataHoraInicio devolvida pelo passo 1)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_retries: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    # Quando o worker de recuperação deve agir de novo (retentativa, retomada após queda)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Prazo da resposta do passo 3 (ms-comunicacao)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Recusa de negócio de um participante (problem+json), devolvida em GET /api/v1/sagas/{id}
    recusa: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Idempotency-Key enviada pelo cliente no POST (mesma chave devolve a mesma SAGA)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Lock otimista das transições: UPDATE ... WHERE version = :lida
    version: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # RN09 no orquestrador: no máximo uma SAGA em andamento por doador
        Index("uq_saga_ativa_por_doador", "doador_id", unique=True, postgresql_where=_EM_ANDAMENTO),
        # Polling do worker de recuperação: só SAGAs em andamento, pela próxima tentativa
        Index("idx_saga_pendentes", "next_attempt_at", postgresql_where=_EM_ANDAMENTO),
    )


class SagaPassoLog(Base):
    """Trilha de auditoria: uma linha por ação positiva ou compensação executada."""

    __tablename__ = "saga_step_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    saga_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("saga_execution_state.saga_id", ondelete="CASCADE"), index=True
    )
    step: Mapped[str] = mapped_column(String(32))
    acao: Mapped[str] = mapped_column(String(16))  # FORWARD | COMPENSATE
    resultado: Mapped[str] = mapped_column(String(32))
    detalhe: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OutboxEvent(Base):
    """Transactional Outbox (ADR-003 §5.1), mesmo esquema do ms-hemocentros."""

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
    """Deduplicação das respostas recebidas do RabbitMQ (inbox idempotente)."""

    __tablename__ = "processed_messages"

    message_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
