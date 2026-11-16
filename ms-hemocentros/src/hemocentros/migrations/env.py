"""Ambiente do Alembic. Executado só via `hemocentros.db.migracoes` (conexão síncrona emprestada)."""

from alembic import context

from hemocentros.models.orm import Base

conexao = context.config.attributes["connection"]
context.configure(connection=conexao, target_metadata=Base.metadata, compare_type=True)
with context.begin_transaction():
    context.run_migrations()
