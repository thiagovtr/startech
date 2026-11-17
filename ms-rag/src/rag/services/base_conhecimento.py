"""Base de conhecimento (Bloco 15): Portaria MS nº 5/2017, Anexo IV, em trechos por seção.

Cada seção `## Título` do Markdown vira um documento (o título vai junto do texto, o que melhora a busca).
Os embeddings vêm do Ollama (`nomic-embed-text`) e ficam num `InMemoryVectorStore` do LangChain: a base tem
poucas dezenas de trechos, então um índice em memória, montado na subida em poucos segundos, dispensa um
banco vetorial à parte (Chroma/FAISS) e um volume persistente.
"""

import asyncio
import logging
import re
from importlib import resources

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore

logger = logging.getLogger(__name__)

ARQUIVOS = ("portaria-5-2017-anexo-iv.md",)
FONTE = "Portaria de Consolidação MS nº 5/2017, Anexo IV"


def carregar_documentos() -> list[Document]:
    docs: list[Document] = []
    for nome in ARQUIVOS:
        texto = resources.files("rag.data").joinpath(nome).read_text(encoding="utf-8")
        for bloco in re.split(r"^## ", texto, flags=re.MULTILINE)[1:]:
            titulo, _, corpo = bloco.partition("\n")
            corpo = corpo.strip()
            if corpo:
                docs.append(Document(
                    page_content=f"{titulo.strip()}: {corpo}",
                    metadata={"secao": titulo.strip(), "fonte": FONTE, "arquivo": nome},
                ))
    return docs


class BaseConhecimento:
    def __init__(self, embeddings: Embeddings):
        self._embeddings = embeddings
        self._store: InMemoryVectorStore | None = None

    @property
    def pronta(self) -> bool:
        return self._store is not None

    async def montar(self) -> int:
        store = InMemoryVectorStore(self._embeddings)
        docs = carregar_documentos()
        await store.aadd_documents(docs)
        self._store = store
        return len(docs)

    async def montar_com_retentativas(self, espera: float) -> None:
        """Tenta até conseguir (o Ollama pode subir depois ou ainda estar baixando o modelo)."""
        while True:
            try:
                n = await self.montar()
                logger.info("Base de conhecimento indexada: %d trechos", n)
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Índice não montado (%s). Nova tentativa em %.0fs", exc, espera)
                await asyncio.sleep(espera)

    async def buscar(self, pergunta: str, k: int) -> list[Document]:
        if self._store is None:
            raise RuntimeError("base de conhecimento ainda não indexada")
        return await self._store.asimilarity_search(pergunta, k=k)
