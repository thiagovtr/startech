from fastapi import APIRouter, Query, Request, status

from hemocentros.models.campanha import Campanha, CampanhaCriar
from hemocentros.services import campanhas as campanhas_service
from hemocentros.services import campanhas_mock

router = APIRouter(prefix="/api/v1/campanhas", tags=["campanhas"])


@router.get("", response_model=list[Campanha])
def listar_campanhas(tipo_sanguineo: str | None = Query(default=None, examples=["O-"])) -> list[Campanha]:
    # Mock até o Bloco 15 (leitura no MongoDB).
    return campanhas_mock.listar(tipo_sanguineo)


@router.post("", response_model=Campanha, status_code=status.HTTP_201_CREATED)
async def criar_campanha(dados: CampanhaCriar, request: Request) -> Campanha:
    campanha = await campanhas_service.criar_campanha(request.app.state.session_factory, dados)
    return Campanha.model_validate(campanha)
