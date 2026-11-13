"""Tradução de falhas dos serviços internos para application/problem+json (RFC 7807)."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from bff_web.clients.hemocentros import RespostaDoServico, ServicoIndisponivel

PROBLEM_JSON = "application/problem+json"


def _problem(request: Request, status: int, type_: str, title: str, detail: str) -> JSONResponse:
    body = {"type": type_, "title": title, "status": status, "detail": detail, "instance": request.url.path}
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)


def register(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validacao(request: Request, exc: RequestValidationError):
        # Mesmo formato (400 + invalidParams) do ms-hemocentros, para o painel tratar um só erro.
        params = [
            {"name": ".".join(str(p) for p in e["loc"] if p not in ("body", "query")), "reason": e["msg"]}
            for e in exc.errors()
        ]
        corpo = {"type": "urn:startech:error:payload-invalido", "title": "Payload inválido", "status": 400,
                 "detail": "A requisição contém campos ausentes ou inválidos.", "instance": request.url.path,
                 "invalidParams": params}
        return JSONResponse(corpo, status_code=400, media_type=PROBLEM_JSON)

    @app.exception_handler(ServicoIndisponivel)
    async def _indisponivel(request: Request, exc: ServicoIndisponivel):
        if exc.timeout:
            return _problem(request, 504, "urn:startech:error:servico-timeout", "Tempo de resposta excedido",
                            f"O serviço {exc.servico} não respondeu a tempo.")
        return _problem(request, 503, "urn:startech:error:servico-indisponivel", "Serviço indisponível",
                        f"Não foi possível contatar o serviço {exc.servico}.")

    @app.exception_handler(RespostaDoServico)
    async def _resposta(request: Request, exc: RespostaDoServico):
        r = exc.response
        if r.status_code < 500:
            # Erros do cliente (ex.: 400 de validação) são repassados como vieram do serviço.
            try:
                body = r.json()
            except ValueError:
                body = {"title": "Erro na requisição", "status": r.status_code}
            return JSONResponse(body, status_code=r.status_code, media_type=PROBLEM_JSON)
        return _problem(request, 502, "urn:startech:error:servico-com-falha", "Falha no serviço interno",
                        f"O serviço {exc.servico} respondeu com erro {r.status_code}.")
