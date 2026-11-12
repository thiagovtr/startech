from fastapi import FastAPI

from bff_mobile.api import health, home
from bff_mobile.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.include_router(health.router)
    app.include_router(home.router)
    return app


app = create_app()
