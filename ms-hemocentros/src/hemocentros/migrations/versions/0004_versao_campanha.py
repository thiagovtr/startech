"""Versão da campanha (projeção CQRS versionada, P11c).

Revision ID: 0004
Revises: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS: um banco legado do create_all (adotado via stamp) pode já ter a coluna.
    op.execute("ALTER TABLE campanhas ADD COLUMN IF NOT EXISTS versao INTEGER NOT NULL DEFAULT 1")


def downgrade() -> None:
    op.execute("ALTER TABLE campanhas DROP COLUMN IF EXISTS versao")
