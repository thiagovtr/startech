from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from bff_mobile.api import health, home
from bff_mobile.clients.servicos import DoadoresClient, HemocentrosClient
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
    ):
        app.state.doadores_client = DoadoresClient(doadores)
        app.state.hemocentros_client = HemocentrosClient(hemocentros)
        yield


def create_app() -> FastAPI:
    configurar_logs()
    app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(home.router)
    app.add_middleware(RequestIdMiddleware)
    return app


app = create_app()
