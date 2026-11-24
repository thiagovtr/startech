from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from bff_mobile.autorizacao import exigir_papel
from bff_mobile.clients.servicos import DoadoresClient, HemocentrosClient, ServicoIndisponivel
from bff_mobile.config import get_settings

router = APIRouter(prefix="/bff-mobile", tags=["home"], dependencies=[Depends(exigir_papel)])


class PerfilDoadorSalvar(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    tipoSanguineo: str = Field(pattern=r"^(A|B|AB|O)[+-]$")
    sexo: str = Field(pattern=r"^[MF]$")
    dataUltimaDoacao: date | None = None


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
    o BFF não retorna 500: devolve o perfil mínimo marcado como degradado e as campanhas vigentes sem
    filtro de tipo (o app sinaliza que não estão personalizadas). Ver decisão P10.
    Doador sem cadastro (404 no ms-doadores) não é falha: `status` segue `ok`, o perfil mínimo vem com
    `cadastrado: false` (o app pode convidar a completar o cadastro) e as campanhas vêm sem filtro de tipo.
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
        perfil = await doadores.obter(x_user_id)
        if perfil is None:  # ms-doadores no ar, mas o usuário ainda não tem cadastro de doador
            doador = {"id": x_user_id, "cadastrado": False}
            tipo = settings.tipo_sanguineo_fallback or None
        else:
            doador = perfil
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
        "campanhasPersonalizadas": tipo is not None,
        "campanhas": campanhas,
    }


@router.put("/perfil")
async def salvar_perfil(
    request: Request,
    corpo: PerfilDoadorSalvar,
    doadores: Annotated[DoadoresClient, Depends(get_doadores)],
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
):
    """Cadastra ou atualiza o perfil do doador autenticado (exposto no Gateway como PUT /api/mobile/perfil)."""
    if not x_user_id:
        return JSONResponse(
            {"type": "urn:startech:error:usuario-nao-identificado", "title": "Usuário não identificado",
             "status": 401, "detail": "Cabeçalho X-User-Id ausente.", "instance": request.url.path},
            status_code=401, media_type="application/problem+json",
        )
    payload = corpo.model_dump(mode="json", exclude_none=True)
    try:
        status, resposta = await doadores.salvar(x_user_id, payload)
    except ServicoIndisponivel as exc:
        return JSONResponse(
            {"type": "urn:startech:error:servico-indisponivel", "title": "Serviço de doadores indisponível",
             "status": 503, "detail": f"Não foi possível salvar seu perfil ({exc.motivo}). Tente novamente.",
             "instance": request.url.path},
            status_code=503, media_type="application/problem+json",
        )
    if status != 200:
        return JSONResponse(resposta, status_code=status, media_type="application/problem+json")
    return resposta
