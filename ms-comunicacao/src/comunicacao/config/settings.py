from datetime import timedelta
from functools import lru_cache

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COMUNICACAO_")

    app_name: str = "ms-comunicacao"
    port: int = 8004

    # Credenciais NÃO têm valor padrão no código: vêm do ambiente (.env no Compose, Secret no Kubernetes).
    # Sem elas o serviço não sobe (falha rápida, em vez de rodar silenciosamente com senha conhecida).

    # PostgreSQL próprio (lembretes, histórico, inbox e Outbox) - URL SQLAlchemy com driver asyncpg
    postgres_url: str

    # RabbitMQ - URL AMQP com usuário e senha
    rabbitmq_url: str
    rabbitmq_exchange: str = "startech.events.exchange"
    rabbitmq_exchange_type: str = "topic"
    # True: declara a exchange (idempotente, exige mesmo tipo). False: apenas verifica que ela já existe.
    rabbitmq_declarar_exchange: bool = True
    # True: declara filas e bindings (idempotente; exige os mesmos argumentos de quem já declarou).
    rabbitmq_declarar_filas: bool = True

    # Comandos da SAGA (contratos §2.1). O ms-orquestrador também declara esta fila: durável e SEM argumentos
    # extras. Não acrescente DLX aqui, ou a redeclaração falha com PRECONDITION_FAILED.
    fila_comandos: str = "comunicacao.saga.comandos"
    binding_comandos: str = "saga.comando.comunicacao.*"
    routing_key_programar: str = "saga.comando.comunicacao.programar-lembrete"
    routing_key_cancelar: str = "saga.comando.comunicacao.cancelar-lembrete"
    # Respostas do passo 3 (consumidas pelo ms-orquestrador em `orquestrador.saga.respostas`)
    routing_key_programado: str = "comunicacao.lembrete.programado"
    routing_key_falhou: str = "comunicacao.lembrete.falhou"

    # Notificações de eventos de domínio (desfecho da SAGA, novas campanhas). Fila própria, com DLQ.
    notificacoes_habilitadas: bool = True
    fila_notificacoes: str = "comunicacao.notificacoes"
    # Lista separada por vírgula
    bindings_notificacoes: str = "saga.agendamento.*,hemocentros.campanha.criada"
    rabbitmq_dlx_exchange: str = "startech.events.dlx"
    fila_notificacoes_dlq: str = "comunicacao.notificacoes.dlq"
    routing_key_notificacoes_dlq: str = "comunicacao.notificacoes.dead"

    # Consumidores
    consumidor_habilitado: bool = True
    consumidor_prefetch: int = 10
    consumidor_reconexao: float = 5.0  # segundos entre tentativas de conexão ao RabbitMQ
    consumidor_espera_erro: float = 2.0  # segundos antes de devolver à fila uma mensagem com erro transitório

    # Lembrete: enviado `lembrete_antecedencia` antes do início do agendamento (D-1). Na demonstração, use
    # alguns segundos (formato ISO 8601, ex.: COMUNICACAO_LEMBRETE_ANTECEDENCIA=PT10S) para vê-lo disparar ao vivo.
    lembrete_antecedencia: timedelta = timedelta(days=1)
    lembretes_habilitado: bool = True
    lembretes_intervalo: float = 1.0  # segundos entre consultas quando não há lembrete vencido
    lembretes_lote: int = 50

    # Só para demonstração/E2E: doadores (separados por vírgula) cujo passo 3 responde FALHOU,
    # para mostrar a compensação disparada pelo ms-comunicacao. Vazio em produção.
    simular_falha_doadores: str = ""

    # Publicador do Outbox (polling)
    outbox_worker_habilitado: bool = True
    outbox_intervalo: float = 0.2
    outbox_lote: int = 50
    # Retenção: mensagens já publicadas são removidas após `outbox_retencao_dias` (as pendentes nunca são)
    outbox_limpeza_habilitada: bool = True
    outbox_retencao_dias: float = 7.0
    outbox_limpeza_intervalo: float = 3600.0
    outbox_limpeza_lote: int = 1000

    # False: a API não roda nenhum worker (consumidores, publicador do Outbox, disparo de lembretes).
    api_executa_workers: bool = True

    # Tempo máximo, em segundos, para checar a conectividade do banco
    db_check_timeout: float = 2.0

    @property
    def doadores_com_falha_simulada(self) -> set[str]:
        return {d.strip() for d in self.simular_falha_doadores.split(",") if d.strip()}

    @property
    def lista_bindings_notificacoes(self) -> list[str]:
        return [b.strip() for b in self.bindings_notificacoes.split(",") if b.strip()]


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
            + " (Compose: arquivo .env, ver .env.example; Kubernetes: Secret)."
        ) from None
