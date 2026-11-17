"""Migrações do esquema (Alembic), aplicadas na subida do serviço.

Várias réplicas subindo juntas: um advisory lock do PostgreSQL serializa a migração.
"""

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

_LOCK_ID = 726_004  # identificador arbitrário do advisory lock das migrações do ms-comunicacao


def _migrar(conexao) -> None:
    conexao.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": _LOCK_ID})
    cfg = Config()
    cfg.set_main_option("script_location", "comunicacao:migrations")
    cfg.attributes["connection"] = conexao
    command.upgrade(cfg, "head")


async def aplicar_migracoes(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(_migrar)
