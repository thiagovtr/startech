import asyncio

from pymongo import AsyncMongoClient
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


async def check_mongo(client: AsyncMongoClient, timeout: float) -> str:
    try:
        await asyncio.wait_for(client.admin.command("ping"), timeout)
        return "ok"
    except Exception:
        return "indisponivel"


async def verificar(engine: AsyncEngine, mongo: AsyncMongoClient, timeout: float) -> dict:
    postgres, mongodb = await asyncio.gather(
        check_postgres(engine, timeout), check_mongo(mongo, timeout)
    )
    bancos = {"postgres": postgres, "mongo": mongodb}
    status = "ok" if all(v == "ok" for v in bancos.values()) else "degradado"
    return {"status": status, "bancos": bancos}
