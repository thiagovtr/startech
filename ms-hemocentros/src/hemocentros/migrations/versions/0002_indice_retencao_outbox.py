"""Índice parcial para a limpeza de retenção do Outbox (P3).

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS: bancos criados pelo antigo create_all depois da P3 já têm o índice.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_outbox_published_at ON outbox_events (published_at) WHERE published = true"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_outbox_published_at")
