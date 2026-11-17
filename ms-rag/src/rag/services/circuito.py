"""Circuit breaker com timeout para as chamadas ao LLM (e à ferramenta de campanhas).

FECHADO: chamadas passam; cada falha/timeout conta, e `limite` seguidas abrem o circuito.
ABERTO: chamadas falham na hora (sem esperar o timeout) até passar `aberto_por` segundos.
MEIO_ABERTO: uma única chamada de teste passa; sucesso fecha, falha reabre.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")

FECHADO, ABERTO, MEIO_ABERTO = "FECHADO", "ABERTO", "MEIO_ABERTO"


class CircuitoAberto(RuntimeError):
    pass


class Circuito:
    def __init__(self, nome: str, limite: int, aberto_por: float, timeout: float,
                 relogio: Callable[[], float] = time.monotonic):
        self.nome, self.limite, self.aberto_por, self.timeout = nome, limite, aberto_por, timeout
        self._relogio = relogio
        self._falhas = 0
        self._aberto_em: float | None = None
        self._teste_em_andamento = False

    @property
    def estado(self) -> str:
        if self._aberto_em is None:
            return FECHADO
        if self._relogio() - self._aberto_em >= self.aberto_por:
            return MEIO_ABERTO
        return ABERTO

    async def chamar(self, fn: Callable[[], Awaitable[T]], timeout: float | None = None) -> T:
        estado = self.estado
        if estado == ABERTO or (estado == MEIO_ABERTO and self._teste_em_andamento):
            raise CircuitoAberto(f"circuito {self.nome} aberto")
        self._teste_em_andamento = estado == MEIO_ABERTO
        try:
            resultado = await asyncio.wait_for(fn(), timeout or self.timeout)
        except Exception as exc:
            self._registrar_falha(exc)
            raise
        finally:
            self._teste_em_andamento = False
        if self._aberto_em is not None:
            logger.info("Circuito %s fechado novamente", self.nome)
        self._falhas, self._aberto_em = 0, None
        return resultado

    def _registrar_falha(self, exc: BaseException) -> None:
        self._falhas += 1
        motivo = "timeout" if isinstance(exc, TimeoutError) else type(exc).__name__
        if self.estado == MEIO_ABERTO or self._falhas >= self.limite:
            self._aberto_em = self._relogio()
            logger.warning("Circuito %s ABERTO por %.0fs (%s; %d falhas)", self.nome, self.aberto_por, motivo,
                           self._falhas)
        else:
            logger.warning("Falha no circuito %s (%s; %d/%d)", self.nome, motivo, self._falhas, self.limite)
