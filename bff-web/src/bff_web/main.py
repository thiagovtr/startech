from fastapi import FastAPI

from bff_web.api import health
from bff_web.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.include_router(health.router)
    return app


app = create_app()
