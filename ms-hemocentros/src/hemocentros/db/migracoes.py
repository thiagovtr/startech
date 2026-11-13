"""Migrações do esquema (Alembic), aplicadas na subida do serviço.

- Banco vazio: aplica todas as revisões.
- Banco criado pelo antigo `create_all` (tabelas sem `alembic_version`): marca a revisão 0001 como
  aplicada (`stamp`) e segue dali, sem recriar tabelas nem perder dados.
- Várias réplicas subindo juntas: um advisory lock do PostgreSQL serializa a migração.
"""

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine

REVISAO_BASE = "0001"  # equivalente ao esquema do antigo create_all
_LOCK_ID = 726_001  # identificador arbitrário do advisory lock das migrações


def _config(conexao) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", "hemocentros:migrations")
    cfg.attributes["connection"] = conexao
    return cfg


def _migrar(conexao) -> None:
    conexao.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": _LOCK_ID})
    cfg = _config(conexao)
    tabelas = set(inspect(conexao).get_table_names())
    if "alembic_version" not in tabelas and {"campanhas", "outbox_events"} <= tabelas:
        command.stamp(cfg, REVISAO_BASE)
    command.upgrade(cfg, "head")


async def aplicar_migracoes(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(_migrar)
