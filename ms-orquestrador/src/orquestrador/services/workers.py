"""Tarefas em segundo plano do orquestrador (rodam dentro da API)."""

import asyncio

from fastapi import FastAPI

from orquestrador.services.outbox_limpeza import executar_limpeza
from orquestrador.services.outbox_publisher import executar_publicador
from orquestrador.services.recuperacao import executar_recuperacao


def iniciar_workers(app: FastAPI) -> list[asyncio.Task]:
    s = app.state.settings
    tarefas = []
    if s.recuperacao_habilitada:
        tarefas.append(asyncio.create_task(executar_recuperacao(app), name="saga-recuperacao"))
    if s.outbox_worker_habilitado:
        tarefas.append(asyncio.create_task(executar_publicador(app), name="outbox-publicador"))
    if s.outbox_limpeza_habilitada:
        tarefas.append(asyncio.create_task(executar_limpeza(app), name="outbox-limpeza"))
    return tarefas


async def parar_workers(tarefas: list[asyncio.Task]) -> None:
    for t in tarefas:
        t.cancel()
    await asyncio.gather(*tarefas, return_exceptions=True)


def disparar(app: FastAPI, coro) -> None:
    """Executa `coro` em segundo plano, guardando a referência até terminar (e cancelando no desligamento)."""
    tarefa = asyncio.create_task(coro)
    app.state.tarefas_saga.add(tarefa)
    tarefa.add_done_callback(app.state.tarefas_saga.discard)
