"""Esquema inicial: campanhas e outbox_events (equivale ao antigo create_all).

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
        "campanhas",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("hemocentro", sa.String(200), nullable=False),
        sa.Column("tipo_sanguineo", sa.String(3), nullable=False),
        sa.Column("urgencia", sa.String(20), nullable=False, server_default="NORMAL"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=False),
        sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_campanhas_tipo_sanguineo", "campanhas", ["tipo_sanguineo"])
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("aggregate_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", sa.String(64), nullable=False),
        sa.Column("routing_key", sa.String(128), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_outbox_unpublished", "outbox_events", ["created_at"], postgresql_where=sa.text("published = false")
    )


def downgrade() -> None:
    op.drop_table("outbox_events")
    op.drop_table("campanhas")
