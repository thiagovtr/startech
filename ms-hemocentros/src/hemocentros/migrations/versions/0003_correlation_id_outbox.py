"""Correlation id no Outbox (observabilidade ponta a ponta, P11b).

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS: um banco legado criado pelo create_all (adotado via stamp em 0001) pode já ter a coluna.
    op.execute("ALTER TABLE outbox_events ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(128)")


def downgrade() -> None:
    op.execute("ALTER TABLE outbox_events DROP COLUMN IF EXISTS correlation_id")
