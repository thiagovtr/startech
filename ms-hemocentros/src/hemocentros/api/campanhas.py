from fastapi import APIRouter, Query

from hemocentros.models.campanha import Campanha
from hemocentros.services import campanhas_mock

router = APIRouter(prefix="/api/v1/campanhas", tags=["campanhas"])


@router.get("", response_model=list[Campanha])
def listar_campanhas(tipo_sanguineo: str | None = Query(default=None, examples=["O-"])) -> list[Campanha]:
    return campanhas_mock.listar(tipo_sanguineo)
