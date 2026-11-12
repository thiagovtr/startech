from contextlib import asynccontextmanager

from fastapi import FastAPI

from hemocentros.api import campanhas, health
from hemocentros.config import get_settings
from hemocentros.db.mongo import create_client
from hemocentros.db.postgres import create_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.pg_engine = create_engine(settings)
    app.state.mongo_client = create_client(settings)
    try:
        yield
    finally:
        await app.state.pg_engine.dispose()
        await app.state.mongo_client.close()


def create_app() -> FastAPI:
    app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(campanhas.router)
    return app


app = create_app()
