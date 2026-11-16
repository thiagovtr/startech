"""Worker de recuperação: retentativas agendadas, prazo da resposta do passo 3 e SAGAs interrompidas.

A cada ciclo, seleciona as SAGAs em andamento com `next_attempt_at` vencido (`FOR UPDATE SKIP LOCKED`,
já reservando-as) e as leva adiante com o executor. É a rede de segurança do fluxo: o `POST` dispara o
executor na hora, mas se o processo cair no meio de um passo, é aqui que a SAGA é retomada.
"""

import asyncio
import logging
from datetime import UTC, datetime

from fastapi import FastAPI

from orquestrador.repositories import sagas as repo
from orquestrador.saga.executor import Executor

logger = logging.getLogger(__name__)


async def executar_ciclo(executor: Executor, sessoes, agora: datetime, prazo_s: float, lote: int) -> int:
    """Processa um lote de SAGAs vencidas; devolve quantas foram selecionadas."""
    ids = await repo.selecionar_pendentes(sessoes, agora, prazo_s, lote)
    resultados = await asyncio.gather(
        *[executor.avancar(saga_id, reivindicada=True) for saga_id in ids], return_exceptions=True
    )
    for saga_id, resultado in zip(ids, resultados, strict=True):
        if isinstance(resultado, Exception):
            logger.error("Recuperação da SAGA %s falhou: %r (nova tentativa após o prazo)", saga_id, resultado)
    return len(ids)


async def executar_recuperacao(app: FastAPI) -> None:
    """Laço do worker. Nunca derruba o serviço (banco fora: registra e tenta de novo)."""
    s = app.state.settings
    while True:
        try:
            n = await executar_ciclo(
                app.state.executor, app.state.session_factory, datetime.now(UTC),
                s.prazo_reivindicacao, s.recuperacao_lote,
            )
            if n == 0:
                await asyncio.sleep(s.recuperacao_intervalo)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Worker de recuperação: %s. Nova tentativa em %.0fs", exc, s.recuperacao_intervalo * 3)
            await asyncio.sleep(s.recuperacao_intervalo * 3)
