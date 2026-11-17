"""Esquema inicial: lembretes, notificações, Outbox, mensagens processadas e rejeitadas.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lembretes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agendamento_id", sa.String(64), nullable=False, unique=True),
        sa.Column("saga_id", sa.String(64), nullable=False),
        sa.Column("doador_id", sa.String(64), nullable=False),
        sa.Column("slot_id", sa.String(64), nullable=True),
        sa.Column("data_hora_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("programado_para", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("enviado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_lembretes_doador_id", "lembretes", ["doador_id"])
    op.create_index(
        "idx_lembretes_pendentes", "lembretes", ["programado_para"], postgresql_where=sa.text("status = 'PROGRAMADO'")
    )

    op.create_table(
        "notificacoes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("doador_id", sa.String(64), nullable=True),
        sa.Column("agendamento_id", sa.String(64), nullable=True),
        sa.Column("tipo", sa.String(16), nullable=False),
        sa.Column("canal", sa.String(16), nullable=False),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("correlation_id", sa.String(128), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_notificacoes_doador", "notificacoes", ["doador_id", "criado_em"])

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

    op.create_table(
        "mensagens_rejeitadas",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("fila", sa.String(128), nullable=False),
        sa.Column("message_id", sa.String(128), nullable=True),
        sa.Column("routing_key", sa.String(128), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("corpo", sa.Text(), nullable=False),
        sa.Column("recebida_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("mensagens_rejeitadas")
    op.drop_table("processed_messages")
    op.drop_table("outbox_events")
    op.drop_table("notificacoes")
    op.drop_table("lembretes")
