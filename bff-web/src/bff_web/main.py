from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from bff_web.api import campanhas, errors, health
from bff_web.clients.hemocentros import HemocentrosClient
from bff_web.config import get_settings
from bff_web.observabilidade import RequestIdMiddleware, configurar_logs, propagar_request_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    async with httpx.AsyncClient(
        base_url=settings.hemocentros_url, timeout=settings.http_timeout,
        event_hooks={"request": [propagar_request_id]},
    ) as http:
        app.state.hemocentros_client = HemocentrosClient(http)
        yield


def create_app() -> FastAPI:
    configurar_logs()
    app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
    errors.register(app)
    app.include_router(health.router)
    app.include_router(campanhas.router)
    app.add_middleware(RequestIdMiddleware)
    return app


app = create_app()
