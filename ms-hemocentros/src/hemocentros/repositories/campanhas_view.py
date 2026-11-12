"""Leitura (Query side do CQRS): view desnormalizada `campanhas_view` no MongoDB."""

from pymongo import AsyncMongoClient

from hemocentros.db.mongo import COLECAO_CAMPANHAS_VIEW


async def listar(client: AsyncMongoClient, db_name: str, tipo_sanguineo: str | None = None) -> list[dict]:
    filtro = {"tipo_sanguineo": tipo_sanguineo} if tipo_sanguineo else {}
    cursor = client[db_name][COLECAO_CAMPANHAS_VIEW].find(filtro).sort("data_inicio", 1)
    docs = []
    async for doc in cursor:
        doc["id"] = doc.pop("_id")  # _id do documento = id da campanha (upsert idempotente, Bloco 14)
        docs.append(doc)
    return docs
