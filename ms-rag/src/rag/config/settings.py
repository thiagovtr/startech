from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAG_")

    app_name: str = "ms-rag"
    port: int = 8005

    # Ollama (LLM local) e modelos
    ollama_url: str = "http://ollama:11434"
    modelo_chat: str = "qwen2.5:1.5b"
    modelo_embeddings: str = "nomic-embed-text"
    temperatura: float = 0.0  # determinístico
    num_predict: int = 200  # limita o tamanho da resposta (e a latência)
    num_ctx: int = 2048
    # Threads de CPU do Ollama por requisição. O padrão do Ollama (todos os núcleos) é ~6x mais lento em CPUs
    # híbridas (núcleos P + E): medido num Core Ultra 9 285K, 8 threads = ~58 tokens/s contra ~10 com 24.
    # Ajuste para o nº de núcleos de desempenho da máquina; 0 = deixa o Ollama decidir.
    num_thread: int = 8

    # Resiliência (plano Dev 4, Bloco 18): sem resposta do LLM em `timeout_llm` s -> fallback amigável.
    # Calibrado para rodar com folga em VMs de 4 vCPUs sem GPU, mantendo fallback rápido se o Ollama travar.
    timeout_llm: float = 25.0
    # Busca (embedding da pergunta): orçamento próprio. Total no pior caso = timeout_busca + timeout_llm (30 s),
    # abaixo dos 32 s do BFF Mobile e dos 35 s do Gateway (response-timeout).
    timeout_busca: float = 5.0
    # Circuit breaker: `cb_falhas` falhas seguidas abrem o circuito por `cb_aberto_segundos`; depois, uma
    # chamada de teste (meio-aberto) decide se fecha de novo.
    cb_falhas: int = 3
    cb_aberto_segundos: float = 30.0
    # Carrega o modelo na subida (o primeiro request a frio leva ~10 s e estouraria o timeout).
    aquecer_modelo: bool = True

    # Recuperação (RAG)
    top_k: int = 2  # 3 trechos distraíam o modelo de 1,5B (escolhia a regra de outra seção)
    indice_retentativa: float = 10.0  # s entre tentativas de montar o índice com o Ollama fora

    # Ferramenta "Onde posso doar hoje?" (ms-hemocentros, leitura CQRS no MongoDB)
    hemocentros_url: str = "http://ms-hemocentros:8000"
    hemocentros_timeout: float = 2.0
    max_campanhas: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
