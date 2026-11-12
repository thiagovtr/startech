import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from hemocentros.api import campanhas, errors, health
from hemocentros.config import get_settings
from hemocentros.db.mongo import create_client
from hemocentros.db.postgres import create_engine, create_session_factory, criar_esquema

logger = logging.getLogger(__name__)


async def _garantir_esquema(engine, tentativas: int = 5, espera: float = 2.0) -> None:
    """Cria o esquema na subida. Se o banco não estiver disponível, o serviço sobe mesmo assim."""
    for n in range(1, tentativas + 1):
        try:
            await criar_esquema(engine)
            return
        except Exception as exc:
            logger.warning("Esquema não criado (tentativa %d/%d): %s", n, tentativas, exc)
            await asyncio.sleep(espera)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.pg_engine = create_engine(settings)
    app.state.session_factory = create_session_factory(app.state.pg_engine)
    app.state.mongo_client = create_client(settings)
    app.state.esquema_task = asyncio.create_task(_garantir_esquema(app.state.pg_engine))
    try:
        yield
    finally:
        app.state.esquema_task.cancel()
        await app.state.pg_engine.dispose()
        await app.state.mongo_client.close()


def create_app() -> FastAPI:
    app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
    errors.register(app)
    app.include_router(health.router)
    app.include_router(campanhas.router)
    return app


app = create_app()
