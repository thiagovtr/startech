import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from hemocentros.api import campanhas, errors, health
from hemocentros.config import get_settings
from hemocentros.db.mongo import create_client, garantir_indices
from hemocentros.db.postgres import create_engine, create_session_factory, criar_esquema
from hemocentros.services.outbox_limpeza import executar_limpeza
from hemocentros.services.outbox_publisher import executar_publicador
from hemocentros.services.projecao import executar_consumidor

logger = logging.getLogger(__name__)


async def _com_tentativas(nome: str, operacao, tentativas: int = 5, espera: float = 2.0) -> None:
    """Executa a inicialização de um banco. Se ele não estiver disponível, o serviço sobe mesmo assim."""
    for n in range(1, tentativas + 1):
        try:
            await operacao()
            return
        except Exception as exc:
            logger.warning("%s não inicializado (tentativa %d/%d): %s", nome, n, tentativas, exc)
            await asyncio.sleep(espera)


async def _inicializar_bancos(app: FastAPI) -> None:
    await asyncio.gather(
        _com_tentativas("Esquema PostgreSQL", lambda: criar_esquema(app.state.pg_engine)),
        _com_tentativas(
            "Índices MongoDB", lambda: garantir_indices(app.state.mongo_client, app.state.settings.mongo_db)
        ),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.pg_engine = create_engine(settings)
    app.state.session_factory = create_session_factory(app.state.pg_engine)
    app.state.mongo_client = create_client(settings)
    app.state.esquema_task = asyncio.create_task(_inicializar_bancos(app))
    app.state.outbox_task = (
        asyncio.create_task(executar_publicador(app)) if settings.outbox_worker_habilitado else None
    )
    app.state.limpeza_task = (
        asyncio.create_task(executar_limpeza(app)) if settings.outbox_limpeza_habilitada else None
    )
    app.state.consumidor_task = (
        asyncio.create_task(executar_consumidor(app)) if settings.consumidor_habilitado else None
    )
    try:
        yield
    finally:
        app.state.esquema_task.cancel()
        tarefas = [t for t in (app.state.outbox_task, app.state.limpeza_task, app.state.consumidor_task) if t]
        for t in tarefas:
            t.cancel()
        await asyncio.gather(*tarefas, return_exceptions=True)
        await app.state.pg_engine.dispose()
        await app.state.mongo_client.close()


def create_app() -> FastAPI:
    app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
    errors.register(app)
    app.include_router(health.router)
    app.include_router(campanhas.router)
    return app


app = create_app()
