from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response, status

from bff_web.autorizacao import exigir_papel
from bff_web.clients.hemocentros import HemocentrosClient, get_hemocentros_client
from bff_web.models import Campanha, CampanhaCriar

router = APIRouter(prefix="/bff-web", tags=["campanhas"], dependencies=[Depends(exigir_papel)])

Client = Annotated[HemocentrosClient, Depends(get_hemocentros_client)]
UserId = Annotated[str | None, Header(alias="X-User-Id")]


@router.post(
    "/campanhas",
    status_code=status.HTTP_201_CREATED,
    response_model=Campanha,
    responses={400: {"description": "Payload inválido (application/problem+json com `invalidParams`)"}},
)
async def criar_campanha(client: Client, dados: CampanhaCriar, x_user_id: UserId = None) -> dict:
    """Repassa o comando ao ms-hemocentros. A resposta traz a campanha criada, o que garante
    Read-Your-Own-Writes no painel sem depender da view de leitura (eventualmente consistente)."""
    return await client.criar_campanha(dados.model_dump(mode="json"), x_user_id)


@router.get("/campanhas", response_model=list[Campanha])
async def listar_campanhas(
    client: Client,
    response: Response,
    x_user_id: UserId = None,
    tipo_sanguineo: str | None = Query(default=None, examples=["O-"]),
    status: str | None = Query(default=None, examples=["ATIVA"]),
    vigentes: bool | None = Query(default=None, description="Só campanhas que ainda não terminaram."),
    limit: int | None = Query(default=None, ge=1, le=200),
    offset: int | None = Query(default=None, ge=0),
) -> list[dict]:
    """Lista campanhas (paginadas); o total vai em `X-Total-Count`. Sem filtros, inclui as encerradas."""
    campanhas, total = await client.listar_campanhas(
        tipo_sanguineo, x_user_id, status=status, vigentes=vigentes, limit=limit, offset=offset
    )
    if total is not None:
        response.headers["X-Total-Count"] = total
    return campanhas
