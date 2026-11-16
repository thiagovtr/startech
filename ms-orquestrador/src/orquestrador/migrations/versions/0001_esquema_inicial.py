"""Esquema inicial: estado da SAGA, log de passos, Outbox e mensagens processadas.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

EM_ANDAMENTO = sa.text("status NOT IN ('CONFIRMED', 'REJECTED', 'COMPENSATED', 'COMPENSATION_FAILED')")


def upgrade() -> None:
    op.create_table(
        "saga_execution_state",
        sa.Column("saga_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tipo", sa.String(32), nullable=False, server_default="AGENDAMENTO"),
        sa.Column("agendamento_id", sa.String(64), nullable=False, unique=True),
        sa.Column("doador_id", sa.String(64), nullable=False),
        sa.Column("slot_id", sa.String(64), nullable=False),
        sa.Column("current_step", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("recusa", JSONB(), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=True, unique=True),
        sa.Column("correlation_id", sa.String(128), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "uq_saga_ativa_por_doador", "saga_execution_state", ["doador_id"], unique=True, postgresql_where=EM_ANDAMENTO
    )
    op.create_index("idx_saga_pendentes", "saga_execution_state", ["next_attempt_at"], postgresql_where=EM_ANDAMENTO)

    op.create_table(
        "saga_step_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "saga_id", UUID(as_uuid=True),
            sa.ForeignKey("saga_execution_state.saga_id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("step", sa.String(32), nullable=False),
        sa.Column("acao", sa.String(16), nullable=False),
        sa.Column("resultado", sa.String(32), nullable=False),
        sa.Column("detalhe", JSONB(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_saga_step_log_saga_id", "saga_step_log", ["saga_id"])

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("aggregate_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", sa.String(64), nullable=False),
        sa.Column("routing_key", sa.String(128), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("message_id", sa.String(128), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correlation_id", sa.String(128), nullable=True),
    )
    op.create_index(
        "idx_outbox_unpublished", "outbox_events", ["created_at"], postgresql_where=sa.text("published = false")
    )
    op.create_index(
        "idx_outbox_published_at", "outbox_events", ["published_at"], postgresql_where=sa.text("published = true")
    )

    op.create_table(
        "processed_messages",
        sa.Column("message_id", sa.String(128), primary_key=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("processed_messages")
    op.drop_table("outbox_events")
    op.drop_table("saga_step_log")
    op.drop_table("saga_execution_state")
