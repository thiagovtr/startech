"""Workers em segundo plano (publicador do Outbox, limpeza de retenção, consumidor da projeção).

Rodam dentro da API (modo padrão) ou num processo próprio (`python -m hemocentros.worker`), o que
permite escalar leitura (API) e processamento de eventos de forma independente. Rodar várias cópias
é seguro: o publicador e a limpeza usam `SKIP LOCKED` e a projeção é idempotente e versionada.
"""

import asyncio

from fastapi import FastAPI

from hemocentros.services.outbox_limpeza import executar_limpeza
from hemocentros.services.outbox_publisher import executar_publicador
from hemocentros.services.projecao import executar_consumidor


def iniciar_workers(app: FastAPI) -> list[asyncio.Task]:
    """Cria as tarefas habilitadas nas configurações (`app.state.settings`)."""
    s = app.state.settings
    tarefas = []
    if s.outbox_worker_habilitado:
        tarefas.append(asyncio.create_task(executar_publicador(app), name="outbox-publicador"))
    if s.outbox_limpeza_habilitada:
        tarefas.append(asyncio.create_task(executar_limpeza(app), name="outbox-limpeza"))
    if s.consumidor_habilitado:
        tarefas.append(asyncio.create_task(executar_consumidor(app), name="projecao-consumidor"))
    return tarefas


async def parar_workers(tarefas: list[asyncio.Task]) -> None:
    for t in tarefas:
        t.cancel()
    await asyncio.gather(*tarefas, return_exceptions=True)
