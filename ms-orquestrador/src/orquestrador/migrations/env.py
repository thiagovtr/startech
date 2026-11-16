"""Ambiente do Alembic. Executado só via `orquestrador.db.migracoes` (conexão síncrona emprestada)."""

from alembic import context

from orquestrador.models.orm import Base

conexao = context.config.attributes["connection"]
context.configure(connection=conexao, target_metadata=Base.metadata, compare_type=True)
with context.begin_transaction():
    context.run_migrations()
