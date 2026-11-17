"""Assistente do doador (Blocos 16-18): roteamento, cadeia RAG, ferramenta e fallback.

Fluxo de `responder`:
1. Pergunta sobre "onde doar" -> ferramenta de campanhas (ms-hemocentros), sem LLM.
2. Senão, com RAG: busca os `top_k` trechos da Portaria e pede ao LLM uma resposta restrita ao contexto.
   Sem RAG (só para a avaliação comparativa do Bloco 20): pergunta direto ao LLM.
3. LLM ou ferramenta acima do timeout, com erro ou com o circuito aberto -> fallback amigável. Com RAG, o
   fallback inclui o trecho recuperado, que não depende do LLM.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate

from rag.services import ferramentas
from rag.services.base_conhecimento import FONTE, BaseConhecimento
from rag.services.circuito import Circuito, CircuitoAberto

logger = logging.getLogger(__name__)

SEM_RESPOSTA = (
    "Não encontrei essa informação na Portaria de Consolidação MS nº 5/2017. "
    "Procure a equipe de triagem do hemocentro para orientação."
)
AVISO = "Orientação informativa: a decisão final sobre a aptidão é da triagem clínica do hemocentro."
FALLBACK_LLM = (
    "O assistente está temporariamente indisponível. Para dúvidas sobre quem pode doar, "
    "consulte a equipe do hemocentro ou tente novamente em instantes."
)
FALLBACK_CAMPANHAS = "Não foi possível consultar as campanhas agora. Tente novamente em instantes."

# Prompt calibrado no qwen2.5:1.5b (ver docs/ia/avaliacao-rag.md): o modelo informa a REGRA do trecho, sem decidir
# se a pessoa está apta (escopo do projeto; e modelos pequenos erram esse raciocínio). Uma frase exata de recusa no
# prompt fazia o modelo recusar perguntas cobertas; a recusa de perguntas fora do domínio é feita antes, sem LLM.
PROMPT_RAG = ChatPromptTemplate.from_messages([
    ("system",
     "Você é o assistente de doação de sangue da StarTech. Use SOMENTE as regras do CONTEXTO abaixo, extraído da "
     "{fonte}; não use conhecimento próprio e não invente prazos ou números. Responda informando a regra exata "
     "(prazo, idade, peso ou critério) do trecho que trata do assunto da pergunta. Se nenhum trecho tratar do "
     "assunto, diga que essa informação não consta nos trechos da Portaria e oriente procurar a triagem do "
     "hemocentro. Responda em português do Brasil, em no máximo 2 frases, e termine com o título do trecho usado "
     "entre colchetes.\n\nCONTEXTO:\n{contexto}"),
    ("human", "{pergunta}"),
])
PROMPT_SEM_RAG = ChatPromptTemplate.from_messages([
    ("system", "Você é um assistente de doação de sangue. Responda em português do Brasil, em no máximo 3 frases."),
    ("human", "{pergunta}"),
])


@dataclass
class Resposta:
    resposta: str
    modo: str  # RAG | SEM_RAG | FERRAMENTA | FORA_DO_ESCOPO | FALLBACK
    fontes: list[dict[str, str]] = field(default_factory=list)
    latencia_ms: float = 0.0
    uso: dict[str, int] | None = None
    motivo_fallback: str | None = None


def _contexto(docs: list[Document]) -> str:
    return "\n\n".join(f"[{d.metadata['secao']}] {d.page_content}" for d in docs)


def _fontes(docs: list[Document]) -> list[dict[str, str]]:
    return [{"secao": d.metadata["secao"], "fonte": d.metadata.get("fonte", FONTE),
             "trecho": d.page_content[:300]} for d in docs]


def _uso(msg: BaseMessage) -> dict[str, int] | None:
    if isinstance(msg, AIMessage) and msg.usage_metadata:
        return {"tokensEntrada": msg.usage_metadata["input_tokens"], "tokensSaida": msg.usage_metadata["output_tokens"]}
    meta = msg.response_metadata or {}
    if "prompt_eval_count" in meta:
        return {"tokensEntrada": int(meta["prompt_eval_count"]), "tokensSaida": int(meta.get("eval_count", 0))}
    return None


class Assistente:
    def __init__(self, llm: BaseChatModel, base: BaseConhecimento, hemocentros: httpx.AsyncClient,
                 circuito_llm: Circuito, circuito_campanhas: Circuito, top_k: int = 3, max_campanhas: int = 5,
                 timeout_busca: float = 1.5, circuito_busca: Circuito | None = None):
        self.llm, self.base, self.top_k, self.timeout_busca = llm, base, top_k, timeout_busca
        # A busca embute a pergunta no Ollama: circuito próprio (sucesso na busca não pode zerar as falhas do LLM).
        self.circuito_busca = circuito_busca or Circuito("busca", circuito_llm.limite, circuito_llm.aberto_por,
                                                         timeout_busca)
        self.circuito_llm, self.circuito_campanhas = circuito_llm, circuito_campanhas
        self.tool = ferramentas.criar_tool(hemocentros, max_campanhas)

    async def responder(self, pergunta: str, usar_rag: bool = True, tipo_sanguineo: str | None = None) -> Resposta:
        inicio = time.perf_counter()
        if usar_rag and ferramentas.e_pergunta_de_campanhas(pergunta):
            r = await self._campanhas(tipo_sanguineo)
        elif usar_rag and not ferramentas.e_do_dominio(pergunta):
            # Recusa determinística: um LLM de 1,5B responde perguntas gerais mesmo instruído a não fazê-lo.
            r = Resposta(SEM_RESPOSTA, "FORA_DO_ESCOPO")
        elif usar_rag:
            r = await self._rag(pergunta)
        else:
            r = await self._sem_rag(pergunta)
        r.latencia_ms = round((time.perf_counter() - inicio) * 1000, 1)
        logger.info("Pergunta respondida: modo=%s latencia_ms=%s%s", r.modo, r.latencia_ms,
                    f" fallback={r.motivo_fallback}" if r.motivo_fallback else "")
        return r

    async def _campanhas(self, tipo_sanguineo: str | None) -> Resposta:
        try:
            texto = await self.circuito_campanhas.chamar(lambda: self.tool.ainvoke({"tipo_sanguineo": tipo_sanguineo}))
        except Exception as exc:
            return Resposta(FALLBACK_CAMPANHAS, "FALLBACK", motivo_fallback=_motivo(exc))
        return Resposta(str(texto), "FERRAMENTA", fontes=[{"secao": "Campanhas ativas", "fonte": "ms-hemocentros",
                                                            "trecho": ""}])

    async def _rag(self, pergunta: str) -> Resposta:
        try:
            if not self.base.pronta:
                raise RuntimeError("índice pendente")
            docs = await self.circuito_busca.chamar(lambda: self.base.buscar(pergunta, self.top_k))
        except Exception as exc:  # índice não montado ou Ollama (embeddings) fora
            return Resposta(FALLBACK_LLM, "FALLBACK", motivo_fallback=f"busca: {_motivo(exc)}")
        mensagens = PROMPT_RAG.format_messages(fonte=FONTE, contexto=_contexto(docs), pergunta=pergunta)
        try:
            msg = await self.circuito_llm.chamar(lambda: self.llm.ainvoke(mensagens))
        except Exception as exc:
            trecho = f" Enquanto isso, veja o trecho da Portaria [{docs[0].metadata['secao']}]: " \
                     f"{docs[0].page_content.split(': ', 1)[-1][:300]}" if docs else ""
            return Resposta(FALLBACK_LLM + trecho, "FALLBACK", fontes=_fontes(docs), motivo_fallback=_motivo(exc))
        return Resposta(f"{str(msg.content).strip()}\n\n{AVISO}", "RAG", fontes=_fontes(docs), uso=_uso(msg))

    async def _sem_rag(self, pergunta: str) -> Resposta:
        try:
            mensagens = PROMPT_SEM_RAG.format_messages(pergunta=pergunta)
            msg = await self.circuito_llm.chamar(lambda: self.llm.ainvoke(mensagens))
        except Exception as exc:
            return Resposta(FALLBACK_LLM, "FALLBACK", motivo_fallback=_motivo(exc))
        return Resposta(str(msg.content).strip(), "SEM_RAG", uso=_uso(msg))


def _motivo(exc: BaseException) -> str:
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, CircuitoAberto):
        return "circuito aberto"
    return type(exc).__name__


def serializar(r: Resposta) -> dict[str, Any]:
    return {"resposta": r.resposta, "modo": r.modo, "fontes": r.fontes, "latenciaMs": r.latencia_ms,
            "uso": r.uso, "motivoFallback": r.motivo_fallback}
