"""Leitura (Query side do CQRS): view desnormalizada `campanhas_view` no MongoDB."""

from datetime import date

from pymongo import AsyncMongoClient

from hemocentros.db.mongo import COLECAO_CAMPANHAS_VIEW


def _filtro(tipo_sanguineo: str | None, status: str | None, vigentes_em: date | None) -> dict:
    filtro: dict = {}
    if tipo_sanguineo:
        filtro["tipo_sanguineo"] = tipo_sanguineo
    if status:
        filtro["status"] = status
    if vigentes_em:
        # datas ISO (YYYY-MM-DD) na view: a comparação lexicográfica equivale à cronológica
        filtro["data_fim"] = {"$gte": vigentes_em.isoformat()}
    return filtro


async def listar(
    client: AsyncMongoClient,
    db_name: str,
    tipo_sanguineo: str | None = None,
    status: str | None = None,
    vigentes_em: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Devolve (página, total que atende ao filtro). Ordem estável: data_inicio e, no empate, _id."""
    colecao = client[db_name][COLECAO_CAMPANHAS_VIEW]
    filtro = _filtro(tipo_sanguineo, status, vigentes_em)
    total = await colecao.count_documents(filtro)
    cursor = colecao.find(filtro).sort([("data_inicio", 1), ("_id", 1)]).skip(offset).limit(limit)
    docs = []
    async for doc in cursor:
        doc["id"] = doc.pop("_id")  # _id do documento = id da campanha (upsert idempotente, Bloco 14)
        docs.append(doc)
    return docs, total
