"""Processo só de workers, sem API HTTP: `python -m hemocentros.worker`.

Uso típico (Kubernetes/Compose): um Deployment da API com `HEMOCENTROS_API_EXECUTA_WORKERS=false`,
escalado pela carga de leitura, e um Deployment deste worker (1 réplica basta; mais é seguro).
Aplica as migrações na partida (advisory lock evita corrida com a API) e encerra limpo em SIGTERM.
"""

import asyncio
import logging
import signal

from fastapi import FastAPI

from hemocentros.config import get_settings
from hemocentros.db.mongo import create_client
from hemocentros.db.postgres import create_engine, create_session_factory, criar_esquema
from hemocentros.observabilidade import configurar_logs
from hemocentros.services.workers import iniciar_workers, parar_workers

logger = logging.getLogger("hemocentros.worker")


async def executar(parada: asyncio.Event | None = None) -> None:
    settings = get_settings()
    # Os workers só usam `app.state`; um FastAPI vazio serve de contêiner, sem servir HTTP.
    contexto = FastAPI()
    contexto.state.settings = settings
    contexto.state.pg_engine = create_engine(settings)
    contexto.state.session_factory = create_session_factory(contexto.state.pg_engine)
    contexto.state.mongo_client = create_client(settings)
    parada = parada or asyncio.Event()
    loop = asyncio.get_running_loop()
    for sinal in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sinal, parada.set)
        except (NotImplementedError, RuntimeError):  # fora da thread principal (ex.: testes)
            pass
    try:
        await criar_esquema(contexto.state.pg_engine)
    except Exception as exc:
        logger.warning("Migrações não aplicadas na partida do worker: %s", exc)
    tarefas = iniciar_workers(contexto)
    logger.info("Worker ativo: %s", ", ".join(t.get_name() for t in tarefas) or "nenhuma tarefa habilitada")
    try:
        await parada.wait()
    finally:
        logger.info("Encerrando worker")
        await parar_workers(tarefas)
        await contexto.state.pg_engine.dispose()
        await contexto.state.mongo_client.close()


def main() -> None:
    configurar_logs()
    asyncio.run(executar())


if __name__ == "__main__":
    main()
