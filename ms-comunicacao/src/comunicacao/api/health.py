from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from comunicacao.services import health as health_service

router = APIRouter(tags=["health"])


async def _estado(request: Request) -> dict:
    state = request.app.state
    return await health_service.verificar(state.pg_engine, state.settings.db_check_timeout)


@router.get("/health")
async def health(request: Request) -> dict:
    """Liveness: sempre 200 (o processo está vivo); `status` indica ok/degradado.

    Não deve falhar por causa de banco: reiniciar o pod não resolve indisponibilidade de banco.
    """
    return await _estado(request)


@router.get("/ready", responses={503: {"description": "PostgreSQL indisponível"}})
async def ready(request: Request) -> JSONResponse:
    """Readiness: 200 só com o PostgreSQL ok; 503 caso contrário (mesmo corpo do /health)."""
    estado = await _estado(request)
    codigo = status.HTTP_200_OK if estado["status"] == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(estado, status_code=codigo)
