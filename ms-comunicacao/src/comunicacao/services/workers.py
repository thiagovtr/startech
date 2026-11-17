"""Tarefas em segundo plano do ms-comunicacao (rodam dentro da API por padrão)."""

import asyncio

from fastapi import FastAPI

from comunicacao.services.comandos import executar_consumidor_comandos
from comunicacao.services.lembretes import executar_lembretes
from comunicacao.services.notificacoes import executar_consumidor_notificacoes
from comunicacao.services.outbox_limpeza import executar_limpeza
from comunicacao.services.outbox_publisher import executar_publicador


def iniciar_workers(app: FastAPI) -> list[asyncio.Task]:
    s = app.state.settings
    tarefas = []
    if s.consumidor_habilitado:
        tarefas.append(asyncio.create_task(executar_consumidor_comandos(app), name="comandos-consumidor"))
        if s.notificacoes_habilitadas:
            tarefas.append(asyncio.create_task(executar_consumidor_notificacoes(app), name="notificacoes-consumidor"))
    if s.outbox_worker_habilitado:
        tarefas.append(asyncio.create_task(executar_publicador(app), name="outbox-publicador"))
    if s.lembretes_habilitado:
        tarefas.append(asyncio.create_task(executar_lembretes(app), name="lembretes"))
    if s.outbox_limpeza_habilitada:
        tarefas.append(asyncio.create_task(executar_limpeza(app), name="outbox-limpeza"))
    return tarefas


async def parar_workers(tarefas: list[asyncio.Task]) -> None:
    for t in tarefas:
        t.cancel()
    await asyncio.gather(*tarefas, return_exceptions=True)
