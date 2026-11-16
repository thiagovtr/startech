"""Escrita na view de leitura (projeção CQRS) — usada somente pelo consumidor de eventos."""

from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError

from hemocentros.db.mongo import COLECAO_CAMPANHAS_VIEW


async def upsert(client: AsyncMongoClient, db_name: str, campanha: dict) -> bool:
    """Upsert idempotente e versionado. Devolve True se a view mudou.

    O `_id` do documento é o id da campanha, então reprocessar não duplica. Cada evento traz o estado
    completo da campanha e sua `versao` (incrementada a cada mudança no modelo de escrita): a view só é
    substituída por uma versão MAIOR. Um evento atrasado ou reentregue fora de ordem é ignorado em vez de
    sobrescrever um estado mais novo. Eventos sem `versao` (anteriores a este controle) contam como 0.
    """
    versao = int(campanha.get("versao", 0))
    doc = {k: v for k, v in campanha.items() if k != "id"} | {"versao": versao}
    filtro = {
        "_id": campanha["id"],
        "$or": [{"versao": {"$lt": versao}}, {"versao": {"$exists": False}}],
    }
    try:
        resultado = await client[db_name][COLECAO_CAMPANHAS_VIEW].replace_one(filtro, doc, upsert=True)
    except DuplicateKeyError:
        # O documento existe com versão >= a deste evento: o filtro não casou e o upsert tentou inserir
        # o mesmo _id. É o caso "evento obsoleto": nada a fazer.
        return False
    return resultado.modified_count > 0 or resultado.upserted_id is not None
