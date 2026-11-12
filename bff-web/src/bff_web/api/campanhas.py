from typing import Annotated

from fastapi import APIRouter, Body, Depends, Header, Query, status

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
    client: Client, x_user_id: UserId = None, tipo_sanguineo: str | None = Query(default=None, examples=["O-"])
) -> list[dict]:
    return await client.listar_campanhas(tipo_sanguineo, x_user_id)
