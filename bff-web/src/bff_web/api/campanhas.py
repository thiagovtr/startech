from typing import Annotated

from fastapi import APIRouter, Body, Depends, Header, Query, Response, status

from bff_web.clients.hemocentros import HemocentrosClient, get_hemocentros_client

router = APIRouter(prefix="/bff-web", tags=["campanhas"])

Client = Annotated[HemocentrosClient, Depends(get_hemocentros_client)]
UserId = Annotated[str | None, Header(alias="X-User-Id")]


@router.post("/campanhas", status_code=status.HTTP_201_CREATED)
async def criar_campanha(client: Client, x_user_id: UserId = None, dados: dict = Body(...)) -> dict:
    """Repassa o comando ao ms-hemocentros. A resposta traz a campanha criada, o que garante
    Read-Your-Own-Writes no painel sem depender da view de leitura (eventualmente consistente)."""
    return await client.criar_campanha(dados, x_user_id)


@router.get("/campanhas")
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
