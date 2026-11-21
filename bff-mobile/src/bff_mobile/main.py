from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from bff_mobile import autorizacao
from bff_mobile.api import agendamentos, assistente, errors, health, home
from bff_mobile.clients.servicos import (
    AgendamentosClient,
    DoadoresClient,
    HemocentrosClient,
    OrquestradorClient,
    RagClient,
)
from bff_mobile.config import get_settings
from bff_mobile.observabilidade import RequestIdMiddleware, configurar_logs, propagar_request_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    hooks = {"request": [propagar_request_id]}
    async with (
        httpx.AsyncClient(
            base_url=settings.doadores_url, timeout=settings.doadores_timeout, event_hooks=hooks
        ) as doadores,
        httpx.AsyncClient(
            base_url=settings.hemocentros_url, timeout=settings.http_timeout, event_hooks=hooks
        ) as hemocentros,
        httpx.AsyncClient(
            base_url=settings.orquestrador_url, timeout=settings.orquestrador_timeout, event_hooks=hooks
        ) as orquestrador,
        httpx.AsyncClient(
            base_url=settings.agendamentos_url, timeout=settings.agendamentos_timeout, event_hooks=hooks
        ) as agendamentos,
        httpx.AsyncClient(base_url=settings.rag_url, timeout=settings.rag_timeout, event_hooks=hooks) as rag,
    ):
        app.state.doadores_client = DoadoresClient(doadores)
        app.state.hemocentros_client = HemocentrosClient(hemocentros)
        app.state.orquestrador_client = OrquestradorClient(orquestrador)
        app.state.agendamentos_client = AgendamentosClient(agendamentos)
        app.state.rag_client = RagClient(rag)
        yield


def create_app() -> FastAPI:
    configurar_logs()
    app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
    autorizacao.registrar(app)
    errors.register(app)
    app.include_router(health.router)
    app.include_router(home.router)
    app.include_router(agendamentos.router)
    app.include_router(assistente.router)
    app.add_middleware(RequestIdMiddleware)
    return app


app = create_app()
