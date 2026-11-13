"""Observabilidade: logs estruturados (JSON) com correlation id por requisição.

- O id vem do cabeçalho `X-Request-Id` (o Gateway ou o BFF o envia) ou é gerado aqui; volta na resposta.
- Fica num `ContextVar`, então todo log emitido durante a requisição (inclusive de bibliotecas) o carrega.
- Os BFFs o repassam às chamadas internas (`propagar_request_id`); o ms-hemocentros o leva até o
  evento do Outbox e o consumidor da projeção, fechando o rastro POST -> RabbitMQ -> MongoDB.
- `LOG_FORMAT=texto` troca o JSON por linhas legíveis (útil em desenvolvimento); `LOG_LEVEL` ajusta o nível.
"""

import json
import logging
import os
import re
import time
import uuid
from contextvars import ContextVar

HEADER = "X-Request-Id"
SERVICO = "ms-hemocentros"
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_ID_VALIDO = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")  # evita log injection por cabeçalho forjado

logger = logging.getLogger(f"{SERVICO}.http")


def novo_request_id() -> str:
    return uuid.uuid4().hex


def request_id_valido(valor: str | None) -> str:
    return valor if valor and _ID_VALIDO.match(valor) else novo_request_id()


class _ComRequestId(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class FormatadorJson(logging.Formatter):
    _EXTRAS = ("metodo", "rota", "status", "duracao_ms")

    def format(self, record: logging.LogRecord) -> str:
        dados = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "nivel": record.levelname,
            "servico": SERVICO,
            "logger": record.name,
            "request_id": getattr(record, "request_id", None),
            "msg": record.getMessage(),
        }
        dados.update({k: getattr(record, k) for k in self._EXTRAS if hasattr(record, k)})
        if record.exc_info:
            dados["exc"] = self.formatException(record.exc_info)
        return json.dumps(dados, ensure_ascii=False, default=str)


def configurar_logs() -> None:
    """Configura o logger raiz (idempotente). Chamado na criação do app."""
    raiz = logging.getLogger()
    if any(getattr(h, "_startech", False) for h in raiz.handlers):
        return
    handler = logging.StreamHandler()
    handler._startech = True  # type: ignore[attr-defined]
    handler.addFilter(_ComRequestId())
    if os.getenv("LOG_FORMAT", "json").lower() == "texto":
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"))
    else:
        handler.setFormatter(FormatadorJson())
    raiz.addHandler(handler)
    raiz.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    logging.getLogger("uvicorn.access").disabled = True  # o middleware abaixo já registra cada requisição


class RequestIdMiddleware:
    """Middleware ASGI: define o correlation id, devolve-o na resposta e registra a requisição."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        cabecalhos = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        rid = request_id_valido(cabecalhos.get(HEADER.lower()))
        token = request_id_var.set(rid)
        inicio = time.perf_counter()
        status = 500

        async def _send(msg):
            nonlocal status
            if msg["type"] == "http.response.start":
                status = msg["status"]
                msg.setdefault("headers", []).append((HEADER.lower().encode(), rid.encode()))
            await send(msg)

        try:
            await self.app(scope, receive, _send)
        finally:
            if scope["path"] not in ("/health", "/ready"):  # probes poluiriam o log
                logger.info(
                    "%s %s %s", scope["method"], scope["path"], status,
                    extra={"metodo": scope["method"], "rota": scope["path"], "status": status,
                           "duracao_ms": round((time.perf_counter() - inicio) * 1000, 1)},
                )
            request_id_var.reset(token)


async def propagar_request_id(request) -> None:
    """Event hook do httpx: repassa o correlation id às chamadas internas."""
    rid = request_id_var.get()
    if rid:
        request.headers[HEADER] = rid
