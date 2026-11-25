import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from langchain_ollama import ChatOllama, OllamaEmbeddings

from rag.api import errors, rotas
from rag.config import get_settings
from rag.observabilidade import RequestIdMiddleware, configurar_logs, propagar_request_id
from rag.services.assistente import Assistente
from rag.services.base_conhecimento import BaseConhecimento
from rag.services.circuito import Circuito

logger = logging.getLogger(__name__)


async def _aquecer(llm: ChatOllama) -> None:
    """Carrega o modelo na memória do Ollama (a primeira geração a frio leva ~10 s)."""
    for _ in range(30):
        try:
            await llm.ainvoke("ok")
            logger.info("Modelo de chat aquecido")
            return
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Aquecimento do modelo: %s", exc)
            await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    threads = s.num_thread or None
    llm = ChatOllama(base_url=s.ollama_url, model=s.modelo_chat, temperature=s.temperatura,
                     num_predict=s.num_predict, num_ctx=s.num_ctx, num_thread=threads, keep_alive="2h")
    embeddings = OllamaEmbeddings(base_url=s.ollama_url, model=s.modelo_embeddings, num_thread=threads,
                                  keep_alive=7200)
    app.state.base = BaseConhecimento(embeddings)
    hemocentros = httpx.AsyncClient(base_url=s.hemocentros_url, timeout=s.hemocentros_timeout,
                                    event_hooks={"request": [propagar_request_id]})
    app.state.circuito_llm = Circuito("llm", s.cb_falhas, s.cb_aberto_segundos, s.timeout_llm)
    app.state.circuito_campanhas = Circuito("campanhas", s.cb_falhas, s.cb_aberto_segundos, s.hemocentros_timeout + 0.5)
    app.state.assistente = Assistente(llm, app.state.base, hemocentros, app.state.circuito_llm,
                                      app.state.circuito_campanhas, s.top_k, s.max_campanhas, s.timeout_busca)
    tarefas = [asyncio.create_task(app.state.base.montar_com_retentativas(s.indice_retentativa))]
    if s.aquecer_modelo:
        tarefas.append(asyncio.create_task(_aquecer(llm)))
    try:
        yield
    finally:
        for t in tarefas:
            t.cancel()
        await asyncio.gather(*tarefas, return_exceptions=True)
        await hemocentros.aclose()


def create_app() -> FastAPI:
    configurar_logs()
    app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
    errors.register(app)
    app.include_router(rotas.router)
    app.add_middleware(RequestIdMiddleware)
    return app


app = create_app()
