import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from orquestrador.api import errors, health, sagas
from orquestrador.clients.agendamentos import AgendamentosClient
from orquestrador.clients.doadores import DoadoresClient
from orquestrador.config import get_settings
from orquestrador.db.postgres import create_engine, create_session_factory, criar_esquema
from orquestrador.observabilidade import RequestIdMiddleware, configurar_logs
from orquestrador.saga.estados import Politica
from orquestrador.saga.executor import Executor
from orquestrador.services.workers import iniciar_workers, parar_workers

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


def politica_de(settings) -> Politica:
    return Politica(
        max_retries=settings.max_retries, backoff_base_ms=settings.backoff_base_ms,
        aguardar_resposta_passo3=settings.passo3_aguardar_resposta, timeout_passo3=settings.timeout_passo3,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.pg_engine = create_engine(settings)
    app.state.session_factory = create_session_factory(app.state.pg_engine)
    app.state.esquema_task = asyncio.create_task(_migrar_com_tentativas(app))
    timeout = httpx.Timeout(settings.http_timeout)
    http_agendamentos = httpx.AsyncClient(base_url=settings.agendamentos_url, timeout=timeout)
    http_doadores = httpx.AsyncClient(base_url=settings.doadores_url, timeout=timeout)
    app.state.agendamentos_client = AgendamentosClient(http_agendamentos)
    app.state.doadores_client = DoadoresClient(http_doadores)
    app.state.executor = Executor(
        app.state.session_factory, app.state.agendamentos_client, app.state.doadores_client,
        politica_de(settings), settings.prazo_reivindicacao,
    )
    app.state.tarefas_saga = set()  # SAGAs disparadas pelo POST e ainda em execução
    app.state.workers = iniciar_workers(app) if settings.api_executa_workers else []
    try:
        yield
    finally:
        app.state.esquema_task.cancel()
        await parar_workers(app.state.workers + list(app.state.tarefas_saga))
        await http_agendamentos.aclose()
        await http_doadores.aclose()
        await app.state.pg_engine.dispose()


def create_app() -> FastAPI:
    configurar_logs()
    app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
    errors.register(app)
    app.include_router(health.router)
    app.include_router(sagas.router)
    app.add_middleware(RequestIdMiddleware)
    return app


app = create_app()
