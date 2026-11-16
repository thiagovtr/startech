"""Erros de validação em application/problem+json (RFC 7807), no mesmo formato do bff-web e dos serviços."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

PROBLEM_JSON = "application/problem+json"
_ORIGENS = ("body", "query", "header", "path")


def register(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validacao(request: Request, exc: RequestValidationError):
        # 400 + invalidParams, como no bff-web e no ms-orquestrador, para o app tratar um só formato de erro.
        params = [
            {"name": ".".join(str(p) for p in e["loc"] if p not in _ORIGENS), "reason": e["msg"]}
            for e in exc.errors()
        ]
        corpo = {"type": "urn:startech:error:payload-invalido", "title": "Payload inválido", "status": 400,
                 "detail": "A requisição contém campos ausentes ou inválidos.", "instance": request.url.path,
                 "invalidParams": params}
        return JSONResponse(corpo, status_code=400, media_type=PROBLEM_JSON)
