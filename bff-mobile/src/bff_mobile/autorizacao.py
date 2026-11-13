"""Autorização por papel (defesa em profundidade, ADR: o bloqueio principal de rota cruzada é do Gateway).

O Gateway valida o JWT do Keycloak e injeta os papéis do usuário em `X-User-Roles` (lista separada
por vírgula). Com `exigir_papel` ligado, o BFF recusa com 403 quem não tem o papel desta superfície,
mesmo que o Gateway deixe passar. Desligado por padrão até o Gateway injetar o cabeçalho.
"""

from typing import Annotated

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from bff_mobile.config import get_settings

HEADER_PAPEIS = "X-User-Roles"


def papeis(valor: str | None) -> set[str]:
    return {p.strip().lower() for p in (valor or "").split(",") if p.strip()}


class PapelInsuficiente(Exception):
    def __init__(self, papel: str):
        self.papel = papel


def registrar(app: FastAPI) -> None:
    @app.exception_handler(PapelInsuficiente)
    async def _proibido(request: Request, exc: PapelInsuficiente):
        corpo = {"type": "urn:startech:error:papel-insuficiente", "title": "Acesso negado", "status": 403,
                 "detail": f"Acesso restrito ao papel '{exc.papel}'.", "instance": request.url.path}
        return JSONResponse(corpo, status_code=403, media_type="application/problem+json")


async def exigir_papel(
    request: Request, x_user_roles: Annotated[str | None, Header(alias=HEADER_PAPEIS)] = None
) -> None:
    settings = get_settings()
    if not settings.exigir_papel:
        return
    if settings.papel_exigido.lower() not in papeis(x_user_roles):
        raise PapelInsuficiente(settings.papel_exigido)
