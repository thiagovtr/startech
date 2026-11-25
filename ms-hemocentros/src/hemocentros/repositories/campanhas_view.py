"""Leitura (Query side do CQRS): view desnormalizada `campanhas_view` no MongoDB."""

import re
import unicodedata
from datetime import date

from pymongo import AsyncMongoClient

from hemocentros.db.mongo import COLECAO_CAMPANHAS_VIEW

HEMOCENTROS_PADRAO: tuple[dict[str, str | None], ...] = (
    {"id": "hemominas-lavras", "nome": "Hemominas Lavras", "cidade": "Lavras - MG"},
    {"id": "santa-casa-lavras", "nome": "Santa Casa de Lavras", "cidade": "Lavras - MG"},
    {"id": "hemocentro-varginha", "nome": "Hemocentro Regional de Varginha", "cidade": "Varginha - MG"},
    {"id": "hemominas-pouso-alegre", "nome": "Hemominas Pouso Alegre", "cidade": "Pouso Alegre - MG"},
    {"id": "hemominas-sao-joao-del-rei", "nome": "Hemominas São João del-Rei", "cidade": "São João del-Rei - MG"},
    {"id": "hemominas-juiz-de-fora", "nome": "Hemominas Juiz de Fora", "cidade": "Juiz de Fora - MG"},
    {"id": "hemominas-bh", "nome": "Hemominas Belo Horizonte", "cidade": "Belo Horizonte - MG"},
)


def _slug(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento).strip("-") or "hemocentro"


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


async def listar_hemocentros(client: AsyncMongoClient, db_name: str) -> list[dict[str, str | None]]:
    """Lista os hemocentros padrão combinados com nomes distintos já registrados em campanhas."""
    itens = [dict(h) for h in HEMOCENTROS_PADRAO]
    vistos = {h["nome"].strip().lower() for h in itens if h["nome"]}
    colecao = client[db_name][COLECAO_CAMPANHAS_VIEW]
    nomes = await colecao.distinct("hemocentro")
    for nome in sorted(str(n).strip() for n in nomes if n and str(n).strip()):
        chave = nome.lower()
        if chave not in vistos:
            vistos.add(chave)
            itens.append({"id": _slug(nome), "nome": nome, "cidade": None})
    return itens
