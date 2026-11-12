from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from bff_mobile.api import health, home
from bff_mobile.clients.servicos import DoadoresClient, HemocentrosClient
from bff_mobile.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    async with (
        httpx.AsyncClient(base_url=settings.doadores_url, timeout=settings.doadores_timeout) as doadores,
        httpx.AsyncClient(base_url=settings.hemocentros_url, timeout=settings.http_timeout) as hemocentros,
    ):
        app.state.doadores_client = DoadoresClient(doadores)
        app.state.hemocentros_client = HemocentrosClient(hemocentros)
        yield


def create_app() -> FastAPI:
    app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(home.router)
    return app


app = create_app()
