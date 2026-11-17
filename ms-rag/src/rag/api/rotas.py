from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from rag.services.assistente import serializar

router = APIRouter(tags=["rag"])


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=3, max_length=500, examples=["Fiz uma tatuagem há 3 meses. Posso doar?"])
    usarRag: bool = Field(True, description="false: pergunta direto ao LLM, sem contexto (avaliação comparativa).")
    tipoSanguineo: str | None = Field(None, pattern=r"^(A|B|AB|O)[+-]$", description="Injetado pelo BFF Mobile.")


class Fonte(BaseModel):
    secao: str
    fonte: str
    trecho: str


class RespostaOut(BaseModel):
    resposta: str
    modo: str = Field(description="RAG | SEM_RAG | FERRAMENTA | FORA_DO_ESCOPO | FALLBACK")
    fontes: list[Fonte]
    latenciaMs: float
    uso: dict[str, int] | None = None
    motivoFallback: str | None = None


@router.post("/api/v1/rag/perguntas", response_model=RespostaOut)
async def perguntar(corpo: Pergunta, request: Request) -> dict[str, Any]:
    """Responde dúvidas do doador com base na Portaria MS nº 5/2017 (RAG) ou nas campanhas ativas (ferramenta).

    Nunca devolve 5xx por causa do LLM: timeout de 4 s, erro ou circuito aberto -> `modo: FALLBACK`, 200.
    """
    r = await request.app.state.assistente.responder(corpo.pergunta, corpo.usarRag, corpo.tipoSanguineo)
    return serializar(r)


@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
    """Liveness (sempre 200). O serviço degrada (fallback) em vez de cair, então /ready também é sempre 200."""
    st = request.app.state
    circuitos = {"llm": st.circuito_llm.estado, "busca": st.assistente.circuito_busca.estado,
                 "campanhas": st.circuito_campanhas.estado}
    ok = st.base.pronta and circuitos["llm"] == circuitos["busca"] == "FECHADO"
    return {"status": "ok" if ok else "degradado", "indice": "pronto" if st.base.pronta else "pendente",
            "circuitos": circuitos}


@router.get("/ready")
async def ready(request: Request) -> dict[str, Any]:
    return await health(request)
