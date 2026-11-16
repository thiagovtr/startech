from contextlib import asynccontextmanager

from fastapi import FastAPI

from orquestrador.api import errors, health
from orquestrador.config import get_settings
from orquestrador.db.postgres import create_engine, create_session_factory
from orquestrador.observabilidade import RequestIdMiddleware, configurar_logs


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.pg_engine = create_engine(settings)
    app.state.session_factory = create_session_factory(app.state.pg_engine)
    try:
        yield
    finally:
        await app.state.pg_engine.dispose()


def create_app() -> FastAPI:
    configurar_logs()
    app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
    errors.register(app)
    app.include_router(health.router)
    app.add_middleware(RequestIdMiddleware)
    return app


app = create_app()
