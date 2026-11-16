import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def check_postgres(engine: AsyncEngine, timeout: float) -> str:
    async def _ping() -> None:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    try:
        await asyncio.wait_for(_ping(), timeout)
        return "ok"
    except Exception:
        return "indisponivel"


async def verificar(engine: AsyncEngine, timeout: float) -> dict:
    """Estado do único banco do orquestrador.

    O RabbitMQ fica de fora de propósito: sem ele a SAGA continua sendo aceita e os comandos ficam no
    Outbox até o broker voltar (ADR-003 §5.3), então tirar o pod do balanceador não ajudaria.
    """
    postgres = await check_postgres(engine, timeout)
    return {"status": "ok" if postgres == "ok" else "degradado", "bancos": {"postgres": postgres}}
