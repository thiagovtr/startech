from fastapi import APIRouter, Request

from hemocentros.services import health as health_service

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict:
    """Sempre 200 (o processo está vivo); o campo `status` indica ok/degradado por banco."""
    state = request.app.state
    return await health_service.verificar(state.pg_engine, state.mongo_client, state.settings.db_check_timeout)
