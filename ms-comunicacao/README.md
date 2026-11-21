# ms-comunicacao

Serviço de **notificações e lembretes** (Python 3.12 / FastAPI, PostgreSQL próprio, porta 8004). É o participante do **Passo 3 da SAGA de agendamento** coordenada pelo [`ms-orquestrador`](../ms-orquestrador/README.md) (ADR-006, contratos §2.1): programa o lembrete pré-doação (D-1), confirma o agendamento ao doador e responde ao orquestrador pelo **Transactional Outbox**.

## Passo 3 da SAGA

| Comando (fila `comunicacao.saga.comandos`) | O que faz, numa única transação | Resposta (via Outbox) |
| --- | --- | --- |
| `saga.comando.comunicacao.programar-lembrete` (`ProgramarLembreteEConfirmar`) | inbox (`message_id`) + lembrete `PROGRAMADO` para `dataHoraInicio − antecedência` + notificação `CONFIRMACAO` | `comunicacao.lembrete.programado`, ou `.falhou` com `motivo` |
| `saga.comando.comunicacao.cancelar-lembrete` (`CancelarLembreteAgendado`) | inbox + lembrete `CANCELADO` + notificação `CANCELAMENTO` | — (compensação sem resposta) |

- **Idempotência:** o `message_id` entra em `processed_messages` na mesma transação. Uma reentrega (*at-least-once*) não gera um segundo lembrete nem uma segunda resposta.
- **Sem dual write:** a resposta (`message_id = saga-{sagaId}-step3-resposta`, com o `correlation_id` do comando) é gravada no `outbox_events` junto do lembrete e publicada depois pelo worker de polling (`FOR UPDATE SKIP LOCKED`, *publisher confirms*). Com o broker fora, ela espera no Outbox.
- **Quando responde `FALHOU`:**
  - `doadorId` ou `dataHoraInicio` ausente ou inválido;
  - `dataHoraInicio` no passado;
  - lembrete já cancelado por uma compensação que chegou antes;
  - comando emitido há mais de `VALIDADE_COMANDO` (30 s): o orquestrador já compensou por timeout, então o doador não é avisado;
  - doador listado em `COMUNICACAO_SIMULAR_FALHA_DOADORES` (só para demonstração).
  
  Nesses casos a SAGA compensa na hora, sem esperar o timeout de 30 s.
- **Compensação antes do comando:** se o `cancelar` chegar antes do `programar`, fica registrado um lembrete `CANCELADO`, e o `programar` atrasado não o reativa.
- **Fila sem DLQ:** o orquestrador também declara `comunicacao.saga.comandos`, durável e **sem argumentos**. Uma DLX aqui daria `PRECONDITION_FAILED`. Comandos ilegíveis (JSON quebrado, sem `sagaId` ou `agendamentoId`) vão para a tabela `mensagens_rejeitadas` e recebem *ack*.
- **Erro transitório** (banco fora): espera `CONSUMIDOR_ESPERA_ERRO` segundos e devolve a mensagem à fila.

## Lembretes e outras notificações

- **Lembrete D-1:** um worker envia os lembretes `PROGRAMADO` vencidos (`SKIP LOCKED`, seguro com réplicas), marca-os `ENVIADO` e registra `LEMBRETE` no histórico. Lembrete cancelado nunca é enviado. Se o D-1 já passou na hora da programação, o lembrete sai logo.
- **Fila `comunicacao.notificacoes`** (com DLQ `comunicacao.notificacoes.dlq`):
  - `saga.agendamento.confirmado` e `saga.agendamento.compensado` geram `DESFECHO` para o doador;
  - `hemocentros.campanha.criada` gera `CAMPANHA`, um aviso geral.
- **Canal:** o envio real (push, e-mail, SMS) está fora do escopo. O canal `LOG` registra cada envio em log JSON, sempre depois do commit.

## Endpoints

| Rota | Descrição |
| --- | --- |
| `GET /api/v1/comunicacao/historico/{doadorId}?pagina=1&tamanho=20` | Histórico auditável do doador, do mais recente para o mais antigo. Doador sem histórico → lista vazia. Parâmetro inválido → `400 problem+json`. |
| `GET /health` / `GET /ready` | Liveness (sempre 200) / readiness (503 com o PostgreSQL fora). |
| `GET /docs` | OpenAPI. |

## Configuração (`COMUNICACAO_*`)

| Variável | Padrão | Observação |
| --- | --- | --- |
| `POSTGRES_URL`, `RABBITMQ_URL` | — | **Obrigatórias** (contêm senha; vêm do `.env` no Compose). Sem elas o processo não sobe. |
| `LEMBRETE_ANTECEDENCIA` | `P1D` | ISO 8601. Na demonstração, ex.: `PT30S`. |
| `SIMULAR_FALHA_DOADORES` | vazio | Lista separada por vírgula; o passo 3 responde `FALHOU` para esses doadores. Só para demonstração. |
| `NOTIFICACOES_HABILITADAS`, `BINDINGS_NOTIFICACOES` | `true`, `saga.agendamento.*,hemocentros.campanha.criada` | Fila de eventos de domínio. |
| `CONSUMIDOR_PREFETCH`, `CONSUMIDOR_ESPERA_ERRO`, `CONSUMIDOR_RECONEXAO` | `10`, `2.0`, `5.0` | Consumidores. |
| `OUTBOX_INTERVALO`, `OUTBOX_RETENCAO_DIAS` | `0.2`, `7` | Publicador e limpeza do Outbox. |
| `API_EXECUTA_WORKERS` | `true` | Consumidores, Outbox e lembretes rodam dentro da API. |

Logs em JSON com `request_id` (o `correlation_id` da mensagem consumida). `LOG_FORMAT=texto` e `LOG_LEVEL` ajustam a saída.

## Executar e testar

Pela raiz: `docker compose up -d --build` (sem porta no host; o serviço é acessado pela rede interna). Localmente:

```bash
cd ms-comunicacao
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
export COMUNICACAO_POSTGRES_URL=postgresql+asyncpg://usuario:senha@127.0.0.1:5432/comunicacao
export COMUNICACAO_RABBITMQ_URL=amqp://usuario:senha@127.0.0.1:5672/
.venv/bin/uvicorn comunicacao.main:app --app-dir src --port 8004
```

```bash
scripts/test-docker.sh ms-comunicacao   # na raiz: ruff + mypy + pytest com PostgreSQL e RabbitMQ reais (falha com skip)
scripts/e2e-saga.sh                     # na raiz: SAGA pelo Gateway, incluindo falha e timeout do passo 3
```

As migrações Alembic são aplicadas na subida, com *advisory lock*. O teste `test_migracoes_correspondem_aos_modelos` falha se o ORM e as migrações divergirem.

## Operação

- **Credenciais:** `COMUNICACAO_POSTGRES_URL` e `COMUNICACAO_RABBITMQ_URL` vêm do `.env`.
- **Saúde:** liveness em `/health`, readiness em `/ready`, porta 8004.
- **Banco próprio:** `db-comunicacao` (PostgreSQL 16).
- **Réplicas:** seguras. A fila tem consumidores concorrentes com inbox idempotente; Outbox e lembretes usam `SKIP LOCKED`.
- Com este serviço no ar, usar `ORQUESTRADOR_PASSO3_AGUARDAR_RESPOSTA=true` no orquestrador.
