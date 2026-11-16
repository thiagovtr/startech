import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from orquestrador.api import errors, health
from orquestrador.config import get_settings
from orquestrador.db.postgres import create_engine, create_session_factory, criar_esquema
from orquestrador.observabilidade import RequestIdMiddleware, configurar_logs

logger = logging.getLogger(__name__)


async def _migrar_com_tentativas(app: FastAPI, tentativas: int = 5, espera: float = 2.0) -> None:
    """Aplica as migrações. Se o banco não estiver disponível, o serviço sobe mesmo assim (/ready indica)."""
    for n in range(1, tentativas + 1):
        try:
            await criar_esquema(app.state.pg_engine)
            return
        except Exception as exc:
            logger.warning("Esquema PostgreSQL não inicializado (tentativa %d/%d): %s", n, tentativas, exc)
            await asyncio.sleep(espera)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.pg_engine = create_engine(settings)
    app.state.session_factory = create_session_factory(app.state.pg_engine)
    app.state.esquema_task = asyncio.create_task(_migrar_com_tentativas(app))
    try:
        yield
    finally:
        app.state.esquema_task.cancel()
        await app.state.pg_engine.dispose()


def create_app() -> FastAPI:
    configurar_logs()
    app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
    errors.register(app)
    app.include_router(health.router)
    app.add_middleware(RequestIdMiddleware)
    return app


app = create_app()
