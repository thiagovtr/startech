"""Assistente do doador: `POST /bff-mobile/assistente` {pergunta} -> ms-rag (RAG da Portaria MS nº 5/2017).

O BFF injeta o tipo sanguíneo do doador (perfil em ms-doadores) para a pergunta "Onde posso doar hoje?".
Degradação graciosa: perfil indisponível -> segue sem tipo; ms-rag fora -> 200 com mensagem de fallback (nunca 5xx).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from bff_mobile.autorizacao import exigir_papel
from bff_mobile.clients.servicos import DoadoresClient, RagClient, ServicoIndisponivel

router = APIRouter(prefix="/bff-mobile", tags=["assistente"], dependencies=[Depends(exigir_papel)])

FALLBACK = ("O assistente está temporariamente indisponível. Para dúvidas sobre quem pode doar, "
            "consulte a equipe do hemocentro ou tente novamente em instantes.")


class PerguntaAssistente(BaseModel):
    pergunta: str = Field(min_length=3, max_length=500, examples=["Fiz uma tatuagem há 3 meses. Posso doar?"])


def get_rag(request: Request) -> RagClient:
    return request.app.state.rag_client


def get_doadores(request: Request) -> DoadoresClient:
    return request.app.state.doadores_client


@router.post("/assistente")
async def perguntar(
    request: Request,
    corpo: PerguntaAssistente,
    rag: Annotated[RagClient, Depends(get_rag)],
    doadores: Annotated[DoadoresClient, Depends(get_doadores)],
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
):
    if not x_user_id:
        return JSONResponse(
            {"type": "urn:startech:error:usuario-nao-identificado", "title": "Usuário não identificado",
             "status": 401, "detail": "Cabeçalho X-User-Id ausente.", "instance": request.url.path},
            status_code=401, media_type="application/problem+json",
        )
    tipo = None
    try:
        perfil = await doadores.obter(x_user_id)
        if perfil:
            tipo = perfil.get("tipoSanguineo") or perfil.get("tipo_sanguineo")
    except ServicoIndisponivel:
        pass  # sem o tipo, a ferramenta lista campanhas de todos os tipos
    try:
        r: dict[str, Any] = await rag.perguntar(corpo.pergunta, tipo)
    except ServicoIndisponivel as exc:
        return {"resposta": FALLBACK, "modo": "FALLBACK", "fontes": [], "degradado": True, "motivo": exc.motivo}
    resposta = {
        "resposta": r.get("resposta"),
        "modo": r.get("modo"),
        "fontes": r.get("fontes", []),
        "degradado": r.get("modo") == "FALLBACK",
    }
    if r.get("motivoFallback"):
        resposta["motivo"] = r["motivoFallback"]
    return resposta
