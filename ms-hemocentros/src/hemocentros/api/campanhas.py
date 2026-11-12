from fastapi import APIRouter, Query, Request, status

from hemocentros.models.campanha import Campanha, CampanhaCriar
from hemocentros.services import campanhas as campanhas_service
from hemocentros.repositories import campanhas_view

router = APIRouter(prefix="/api/v1/campanhas", tags=["campanhas"])


@router.get("", response_model=list[Campanha])
async def listar_campanhas(
    request: Request, tipo_sanguineo: str | None = Query(default=None, examples=["O-"])
) -> list[Campanha]:
    """Leitura direta no MongoDB (view CQRS); não consulta o PostgreSQL."""
    state = request.app.state
    docs = await campanhas_view.listar(state.mongo_client, state.settings.mongo_db, tipo_sanguineo)
    return [Campanha.model_validate(d) for d in docs]


@router.post("", response_model=Campanha, status_code=status.HTTP_201_CREATED)
async def criar_campanha(dados: CampanhaCriar, request: Request) -> Campanha:
    campanha = await campanhas_service.criar_campanha(request.app.state.session_factory, dados)
    return Campanha.model_validate(campanha)
