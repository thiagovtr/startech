from datetime import date

from fastapi import APIRouter, Query, Request, Response, status

from hemocentros.models.campanha import Campanha, CampanhaCriar
from hemocentros.services import campanhas as campanhas_service
from hemocentros.repositories import campanhas_view

router = APIRouter(prefix="/api/v1/campanhas", tags=["campanhas"])


@router.get("", response_model=list[Campanha])
async def listar_campanhas(
    request: Request,
    response: Response,
    tipo_sanguineo: str | None = Query(default=None, examples=["O-"]),
    status: str | None = Query(default=None, examples=["ATIVA"], description="Filtra pelo status da campanha."),
    vigentes: bool = Query(default=False, description="Só campanhas que ainda não terminaram (data_fim >= hoje)."),
    limit: int = Query(default=50, ge=1, le=200, description="Tamanho da página."),
    offset: int = Query(default=0, ge=0, description="Itens a pular."),
) -> list[Campanha]:
    """Leitura direta no MongoDB (view CQRS); não consulta o PostgreSQL.

    Paginada (`limit`/`offset`), ordenada por `data_inicio`. O total que atende ao filtro vai
    no cabeçalho `X-Total-Count`. Sem `vigentes`, campanhas encerradas também são devolvidas.
    """
    state = request.app.state
    docs, total = await campanhas_view.listar(
        state.mongo_client,
        state.settings.mongo_db,
        tipo_sanguineo,
        status,
        date.today() if vigentes else None,
        limit,
        offset,
    )
    response.headers["X-Total-Count"] = str(total)
    return [Campanha.model_validate(d) for d in docs]


@router.post("", response_model=Campanha, status_code=status.HTTP_201_CREATED)
async def criar_campanha(dados: CampanhaCriar, request: Request) -> Campanha:
    campanha = await campanhas_service.criar_campanha(request.app.state.session_factory, dados)
    return Campanha.model_validate(campanha)
