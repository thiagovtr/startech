"""Erros no padrão RFC 7807 (application/problem+json), conforme a especificação de contratos."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from sqlalchemy.exc import SQLAlchemyError

PROBLEM_JSON = "application/problem+json"


def problem(request: Request, status: int, type_: str, title: str, detail: str, **extra) -> JSONResponse:
    body = {"type": type_, "title": title, "status": status, "detail": detail, "instance": request.url.path, **extra}
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)


def register(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validacao(request: Request, exc: RequestValidationError):
        params = [
            {"name": ".".join(str(p) for p in e["loc"] if p != "body"), "reason": e["msg"]}
            for e in exc.errors()
        ]
        return problem(
            request, 400, "urn:startech:error:payload-invalido", "Payload inválido",
            "A requisição contém campos ausentes ou inválidos.", invalidParams=params,
        )

    @app.exception_handler(PyMongoError)
    @app.exception_handler(SQLAlchemyError)
    @app.exception_handler(OSError)
    async def _banco(request: Request, exc: Exception):
        return problem(
            request, 503, "urn:startech:error:banco-indisponivel", "Serviço temporariamente indisponível",
            "Não foi possível acessar o banco de dados. Tente novamente.",
        )
