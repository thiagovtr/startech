import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from bff_mobile.clients.servicos import DoadoresClient, HemocentrosClient, ServicoIndisponivel
from bff_mobile.config import get_settings

router = APIRouter(prefix="/bff-mobile", tags=["home"])


def get_doadores(request: Request) -> DoadoresClient:
    return request.app.state.doadores_client


def get_hemocentros(request: Request) -> HemocentrosClient:
    return request.app.state.hemocentros_client


def _tipo_sanguineo(doador: dict) -> str | None:
    return doador.get("tipoSanguineo") or doador.get("tipo_sanguineo")


@router.get("/home")
async def home(
    request: Request,
    doadores: Annotated[DoadoresClient, Depends(get_doadores)],
    hemocentros: Annotated[HemocentrosClient, Depends(get_hemocentros)],
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
):
    """Agrega perfil do doador e campanhas compatíveis, com degradação graciosa (ADR-005 §5.2).

    O tipo sanguíneo vem do perfil, então o perfil é consultado primeiro. Se `ms-doadores` falhar,
    o BFF não retorna 500: devolve o perfil mínimo marcado como degradado e as campanhas do tipo de fallback.
    """
    if not x_user_id:
        return JSONResponse(
            {"type": "urn:startech:error:usuario-nao-identificado", "title": "Usuário não identificado",
             "status": 401, "detail": "Cabeçalho X-User-Id ausente.", "instance": request.url.path},
            status_code=401, media_type="application/problem+json",
        )
    settings = get_settings()
    indisponiveis: list[str] = []

    try:
        doador = await doadores.obter(x_user_id)
        tipo = _tipo_sanguineo(doador) or settings.tipo_sanguineo_fallback or None
    except ServicoIndisponivel as exc:
        indisponiveis.append(exc.servico)
        doador = {"id": x_user_id, "statusDegradado": True}
        tipo = settings.tipo_sanguineo_fallback or None

    try:
        campanhas = await hemocentros.listar_campanhas(x_user_id, tipo)
    except ServicoIndisponivel as exc:
        indisponiveis.append(exc.servico)
        campanhas = []

    return {
        "status": "degradado" if indisponiveis else "ok",
        "servicosIndisponiveis": indisponiveis,
        "doador": doador,
        "tipoSanguineoCampanhas": tipo,
        "campanhas": campanhas,
    }
