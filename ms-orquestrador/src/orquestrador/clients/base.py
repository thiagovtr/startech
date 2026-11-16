"""Chamadas HTTP aos participantes síncronos da SAGA e classificação das respostas.

Toda chamada leva `Idempotency-Key` (`saga-{sagaId}-stepN`, contratos §2) e `X-Request-Id` (correlation id
da SAGA, inclusive quando quem chama é o worker de recuperação, fora de uma requisição).

Classificação (o executor converte o resultado em evento da máquina de estados):
- 2xx                                   -> Sucesso
- 409 / 422 / 404 na ação positiva      -> Recusa (regra de negócio; não se tenta de novo)
- 404 na compensação                    -> Sucesso (já não existe: compensação idempotente)
- demais 4xx                            -> Falha (erro de contrato; registrado como erro)
- 5xx, timeout, falha de conexão        -> Falha (técnica; a máquina retenta com backoff)
"""

import logging
from dataclasses import dataclass, field
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

PROBLEM_JSON = "application/problem+json"
_RECUSAS_DE_NEGOCIO = {404, 409, 422}


@dataclass(frozen=True)
class Sucesso:
    dados: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Recusa:
    problema: dict


@dataclass(frozen=True)
class Falha:
    motivo: str


Resultado = Sucesso | Recusa | Falha


def _problema(resposta: httpx.Response) -> dict:
    """Corpo problem+json do participante (ou um equivalente mínimo, se ele não enviar)."""
    try:
        corpo = resposta.json()
    except ValueError:
        corpo = None
    if isinstance(corpo, dict):
        return {"status": resposta.status_code, **corpo}
    return {"status": resposta.status_code, "title": resposta.reason_phrase or "Recusado pelo participante"}


def _corpo(resposta: httpx.Response) -> dict:
    if not resposta.content:
        return {}
    try:
        corpo = resposta.json()
    except ValueError:
        return {}
    return corpo if isinstance(corpo, dict) else {}


class ClienteParticipante:
    def __init__(self, http: httpx.AsyncClient, nome: str):
        self._http = http
        self.nome = nome

    async def chamar(
        self,
        metodo: Literal["POST", "DELETE"],
        caminho: str,
        *,
        idempotency_key: str,
        correlation_id: str | None,
        corpo: dict | None = None,
        compensacao: bool = False,
    ) -> Resultado:
        headers = {"Idempotency-Key": idempotency_key}
        if correlation_id:
            headers["X-Request-Id"] = correlation_id
        try:
            resposta = await self._http.request(metodo, caminho, json=corpo, headers=headers)
        except httpx.TimeoutException:
            return Falha(f"{self.nome}: timeout")
        except httpx.TransportError as exc:
            return Falha(f"{self.nome}: indisponível ({type(exc).__name__})")

        codigo = resposta.status_code
        if 200 <= codigo < 300:
            return Sucesso(_corpo(resposta))
        if compensacao and codigo == 404:
            return Sucesso()
        if not compensacao and codigo in _RECUSAS_DE_NEGOCIO:
            return Recusa(_problema(resposta))
        if 400 <= codigo < 500:
            logger.error("%s respondeu %d a %s %s: divergência de contrato?", self.nome, codigo, metodo, caminho)
        return Falha(f"{self.nome}: HTTP {codigo}")


def chave(saga_id: object, passo: int, compensacao: bool = False) -> str:
    """Idempotency-Key de um passo da SAGA (contratos §2)."""
    return f"saga-{saga_id}-step{passo}" + ("-comp" if compensacao else "")
