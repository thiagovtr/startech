from datetime import date

from fastapi import APIRouter, Query, Request, Response, status

from hemocentros.models.campanha import Campanha, CampanhaAtualizar, CampanhaCriar, HemocentroOpcao
from hemocentros.repositories import campanhas_view
from hemocentros.services import campanhas as campanhas_service

router = APIRouter(prefix="/api/v1/campanhas", tags=["campanhas"])
hemocentros_router = APIRouter(prefix="/api/v1/hemocentros", tags=["hemocentros"])


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


@router.put("/{campanha_id}", response_model=Campanha, status_code=status.HTTP_200_OK)
async def atualizar_campanha(campanha_id: str, dados: CampanhaAtualizar, request: Request) -> Campanha:
    """Atualiza uma campanha existente no PostgreSQL e projeta a nova versão no MongoDB via Outbox."""
    campanha = await campanhas_service.atualizar_campanha(request.app.state.session_factory, campanha_id, dados)
    return Campanha.model_validate(campanha)


@hemocentros_router.get("", response_model=list[HemocentroOpcao])
async def listar_hemocentros(request: Request) -> list[HemocentroOpcao]:
    """Lista os hemocentros disponíveis para preenchimento de campanhas."""
    state = request.app.state
    itens = await campanhas_view.listar_hemocentros(state.mongo_client, state.settings.mongo_db)
    return [HemocentroOpcao.model_validate(item) for item in itens]
