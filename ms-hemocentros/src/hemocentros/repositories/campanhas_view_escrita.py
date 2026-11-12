"""Escrita na view de leitura (projeção CQRS) — usada somente pelo consumidor de eventos."""

from pymongo import AsyncMongoClient

from hemocentros.db.mongo import COLECAO_CAMPANHAS_VIEW


async def upsert(client: AsyncMongoClient, db_name: str, campanha: dict) -> None:
    """Upsert idempotente: o `_id` do documento é o id da campanha, então reprocessar não duplica."""
    doc = {k: v for k, v in campanha.items() if k != "id"}
    await client[db_name][COLECAO_CAMPANHAS_VIEW].replace_one({"_id": campanha["id"]}, doc, upsert=True)
