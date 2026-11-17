import asyncio
import re
import unicodedata

import httpx
import pytest
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from rag.services.assistente import Assistente
from rag.services.base_conhecimento import BaseConhecimento, carregar_documentos
from rag.services.circuito import Circuito


def _tokens(texto: str) -> list[str]:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z]{4,}", t)


class EmbeddingsPalavras(Embeddings):
    """Embeddings determinísticos por saco de palavras (sem Ollama): suficiente para testar a recuperação."""

    def __init__(self):
        vocab = sorted({p for d in carregar_documentos() for p in _tokens(d.page_content)})
        self.indice = {p: i for i, p in enumerate(vocab)}

    def _vetor(self, texto: str) -> list[float]:
        v = [0.0] * (len(self.indice) + 1)
        for p in _tokens(texto):
            v[self.indice.get(p, len(self.indice))] += 1.0
        return v

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vetor(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vetor(text)


class LLMLento(GenericFakeChatModel):
    atraso: float = 10.0

    async def _agenerate(self, *args, **kwargs):  # type: ignore[override]
        await asyncio.sleep(self.atraso)
        return await super()._agenerate(*args, **kwargs)


def llm_fake(texto: str = "O peso mínimo é 50 kg. [Peso mínimo]") -> GenericFakeChatModel:
    msg = AIMessage(content=texto, usage_metadata={"input_tokens": 300, "output_tokens": 20, "total_tokens": 320})
    return GenericFakeChatModel(messages=iter([msg] * 100))


CAMPANHAS = [
    {"id": "1", "titulo": "Estoque crítico O-", "hemocentro": "Hemominas Lavras", "tipo_sanguineo": "O-",
     "urgencia": "ALTA", "status": "ATIVA", "data_inicio": "2026-01-01", "data_fim": "2099-12-31"},
    {"id": "2", "titulo": "Campanha encerrada", "hemocentro": "X", "tipo_sanguineo": "O-",
     "urgencia": "BAIXA", "status": "ATIVA", "data_inicio": "2020-01-01", "data_fim": "2020-12-31"},
]


def hemocentros_fake(status: int = 200, chamadas: list | None = None) -> httpx.AsyncClient:
    def handler(req: httpx.Request) -> httpx.Response:
        if chamadas is not None:
            chamadas.append(req)
        return httpx.Response(status, json=CAMPANHAS if status == 200 else {"title": "erro"})

    return httpx.AsyncClient(base_url="http://hemocentros", transport=httpx.MockTransport(handler))


@pytest.fixture
def base():
    b = BaseConhecimento(EmbeddingsPalavras())
    asyncio.run(b.montar())
    return b


def montar_assistente(base, llm=None, hemocentros=None, timeout=0.5) -> Assistente:
    return Assistente(llm or llm_fake(), base, hemocentros or hemocentros_fake(),
                      Circuito("llm", 3, 30, timeout), Circuito("campanhas", 3, 30, timeout))
