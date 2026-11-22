from functools import lru_cache

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ORQUESTRADOR_")

    app_name: str = "ms-orquestrador"
    port: int = 8003

    # Credenciais NÃO têm valor padrão no código: vêm do ambiente (arquivo .env no Compose).
    # Sem elas o serviço não sobe (falha rápida, em vez de rodar silenciosamente com senha conhecida).

    # PostgreSQL próprio (estado da SAGA, log de passos, Outbox) - URL SQLAlchemy com driver asyncpg
    postgres_url: str

    # RabbitMQ (comandos do passo 3 via Outbox e respostas do ms-comunicacao) - URL AMQP com usuário e senha
    rabbitmq_url: str
    rabbitmq_exchange: str = "startech.events.exchange"
    rabbitmq_exchange_type: str = "topic"
    # True: declara a exchange (idempotente, exige mesmo tipo). False: apenas verifica que ela já existe.
    rabbitmq_declarar_exchange: bool = True
    # True: declara filas e bindings da SAGA (contratos §2.1, "Topologia"). Idempotente; exige os mesmos argumentos.
    rabbitmq_declarar_filas: bool = True
    # Respostas do ms-comunicacao (consumidas pelo orquestrador), com dead-letter para mensagens inválidas
    fila_respostas: str = "orquestrador.saga.respostas"
    binding_respostas: str = "comunicacao.lembrete.*"
    rabbitmq_dlx_exchange: str = "startech.events.dlx"
    fila_respostas_dlq: str = "orquestrador.saga.respostas.dlq"
    routing_key_respostas_dlq: str = "orquestrador.saga.respostas.dead"
    # Comandos para o ms-comunicacao: declarada também aqui para nenhum comando se perder enquanto ele não existe.
    # O ms-comunicacao deve declará-la com os MESMOS argumentos (durável, sem argumentos extras).
    fila_comandos_comunicacao: str = "comunicacao.saga.comandos"
    binding_comandos_comunicacao: str = "saga.comando.comunicacao.*"
    # Compensações que esgotaram as tentativas (ADR-002 §5.3)
    fila_compensacoes_dlq: str = "saga.compensations.dlq"
    binding_compensacoes_dlq: str = "saga.compensacao.falhou"

    # Consumidor das respostas do ms-comunicacao (passo 3)
    consumidor_habilitado: bool = True
    consumidor_prefetch: int = 10
    consumidor_reconexao: float = 5.0  # segundos entre tentativas de conexão ao RabbitMQ
    consumidor_espera_erro: float = 2.0  # segundos antes de devolver à fila uma mensagem com erro transitório

    # Publicador do Outbox (polling)
    outbox_worker_habilitado: bool = True
    outbox_intervalo: float = 0.2  # segundos entre consultas quando não há mensagens (piso da latência)
    outbox_lote: int = 50
    # Retenção: mensagens já publicadas são removidas após `outbox_retencao_dias` (as pendentes nunca são)
    outbox_limpeza_habilitada: bool = True
    outbox_retencao_dias: float = 7.0
    outbox_limpeza_intervalo: float = 3600.0
    outbox_limpeza_lote: int = 1000

    # Participantes síncronos da SAGA (passos 1, 2 e 4)
    agendamentos_url: str = "http://ms-agendamentos:8082"
    doadores_url: str = "http://ms-doadores:8081"
    http_timeout: float = 3.0  # segundos por chamada a um participante

    # Retentativas (ADR-002 §5.3): espera = 2^tentativa * backoff_base_ms (+ jitter), até max_retries
    max_retries: int = 5
    backoff_base_ms: int = 500

    # Passo 3 (ms-comunicacao). True: aguarda a resposta `comunicacao.lembrete.*` até `timeout_passo3` segundos.
    # False: o passo 3 conta como concluído quando o comando é gravado no Outbox, que garante a entrega (enquanto o
    # ms-comunicacao não existir; ver contratos §2.1).
    passo3_aguardar_resposta: bool = True
    timeout_passo3: float = 30.0

    # False: a API não roda nenhum worker (publicador do Outbox, consumidor de respostas, recuperação).
    api_executa_workers: bool = True

    # Reivindicação: por quanto tempo (s) quem executa um passo fica com a SAGA. Se o processo cair, outra
    # réplica a retoma depois disso. Deve passar com folga o tempo de uma chamada HTTP (http_timeout).
    prazo_reivindicacao: float = 15.0
    # Worker de recuperação (retentativas, prazo do passo 3, SAGAs interrompidas)
    recuperacao_habilitada: bool = True
    recuperacao_intervalo: float = 1.0  # segundos entre ciclos quando não há SAGA vencida
    recuperacao_lote: int = 20

    # Tempo máximo, em segundos, para checar a conectividade do banco
    db_check_timeout: float = 2.0


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        prefixo = Settings.model_config["env_prefix"]
        faltando = [f"{prefixo}{e['loc'][0]}".upper() for e in exc.errors() if e["type"] == "missing"]
        if not faltando:
            raise
        raise RuntimeError(
            "Configuração obrigatória ausente: defina as variáveis de ambiente " + ", ".join(faltando)
            + " (Compose: arquivo .env, ver .env.example)."
        ) from None
