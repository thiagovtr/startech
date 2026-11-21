# ms-orquestrador

Orquestrador da **SAGA de agendamento** (Python 3.12 / FastAPI), com **PostgreSQL** e **Transactional Outbox** próprios ([ADR-006](../docs/arquitetura/Cat%C3%A1logo%20de%20Decis%C3%B5es%20Arquiteturais%20%28ADRs%29%20-%20StarTech.md)). Coordena `ms-agendamentos`, `ms-doadores` e `ms-comunicacao`; não tem regra de domínio: a vaga é de `ms-agendamentos`, a RN01 é de `ms-doadores` e o lembrete é de `ms-comunicacao`.

## A SAGA

| Passo | Participante | Ação | Compensação | Transporte |
| --- | --- | --- | --- | --- |
| 1 | ms-agendamentos | reserva provisória da vaga | libera a vaga (`CANCELADO_COMPENSACAO_SAGA`) | HTTP, `Idempotency-Key: saga-{id}-step1` |
| 2 | ms-doadores | valida a RN01 e trava o intervalo | remove a trava | HTTP, `saga-{id}-step2` |
| 3 | ms-comunicacao | programa o lembrete D-1 e confirma | cancela o lembrete | RabbitMQ via Outbox, `message_id saga-{id}-step3` |
| 4 | ms-agendamentos | confirma o agendamento | — (passo final) | HTTP, `saga-{id}-step4` |

```
STARTED -1-> SLOT_RESERVED -2-> AWAITING_COMUNICACAO -3-> CONFIRMING -4-> CONFIRMED
   | 409 (vaga esgotada / RN09)        \ 422 (RN01), resposta FALHOU, timeout, falha esgotada
   v                                    v
REJECTED                          COMPENSATING (desfaz 3 -> 2 -> 1) -> COMPENSATED | COMPENSATION_FAILED (DLQ)
```

- **Recusa de negócio** (409/422/404 na ação) não é retentada: vai direto para a compensação (no passo 1, para `REJECTED`).
- **Falha técnica** (timeout, 5xx, rede) é retentada com *backoff* exponencial + *jitter* (500 ms, 1 s, 2 s, 4 s, 8 s); esgotadas as tentativas, a SAGA desfaz inclusive o passo de resultado incerto (as compensações são idempotentes).
- **Compensação que falha** é retentada do mesmo jeito e, esgotada, termina em `COMPENSATION_FAILED` com mensagem em `saga.compensations.dlq`.
- **Atomicidade:** cada transição grava, numa única transação, o estado, a linha do `saga_step_log` e as mensagens do Outbox (comando do passo 3, cancelamento, desfecho). Não há *dual write*.
- **Retomada:** o estado é gravado antes de cada chamada e quem executa um passo "reivindica" a SAGA por `PRAZO_REIVINDICACAO` segundos. Se o processo cair, o worker de recuperação a retoma depois desse prazo, repetindo a chamada idempotente.

Código: `saga/maquina.py` (máquina de estados pura, sem IO), `saga/executor.py` (liga máquina, participantes e banco), `repositories/sagas.py` (transições atômicas), `services/` (workers).

## Endpoints

| Rota | Descrição |
| --- | --- |
| `POST /api/v1/sagas/agendamento` | `{doadorId, slotId}` → `202` + `Location`; a SAGA começa em segundo plano. `Idempotency-Key` repetida devolve a mesma SAGA (`422` se reutilizada com outro doador/slot); `409` se o doador já tem SAGA em andamento (RN09). |
| `GET /api/v1/sagas/{sagaId}` | Status, passo atual, tentativas, data do slot, recusa (`problem+json` do participante), última falha e a **trilha de passos** (ações e compensações). |
| `GET /health` / `GET /ready` | Liveness (sempre 200) / readiness (503 se o PostgreSQL estiver fora). O RabbitMQ fica de fora: sem ele as SAGAs continuam e as mensagens esperam no Outbox. |
| `GET /docs` | OpenAPI. |

O app chega aqui pelo `bff-mobile` (`POST /bff-mobile/agendamentos`, `GET /bff-mobile/sagas/{id}`), via Gateway (`/api/mobile/...`).

## Mensageria (contratos §2.1)

Exchange `startech.events.exchange` (topic). O orquestrador declara, de forma idempotente:

| Fila | Binding | Uso |
| --- | --- | --- |
| `comunicacao.saga.comandos` | `saga.comando.comunicacao.*` | Comandos do passo 3 para o ms-comunicacao. Declarada aqui para nada se perder enquanto ele não existe; o ms-comunicacao deve declará-la **durável e sem argumentos extras**. |
| `orquestrador.saga.respostas` | `comunicacao.lembrete.*` | Respostas `PROGRAMADO`/`FALHOU` (deduplicadas por `message_id`); inválidas vão para `orquestrador.saga.respostas.dlq` (DLX `startech.events.dlx`). |
| `saga.compensations.dlq` | `saga.compensacao.falhou` | Compensações que esgotaram as tentativas. |

Eventos de desfecho: `saga.agendamento.confirmado` e `saga.agendamento.compensado`.

## Configuração (`ORQUESTRADOR_*`)

| Variável | Padrão | Observação |
| --- | --- | --- |
| `POSTGRES_URL`, `RABBITMQ_URL` | — | **Obrigatórias** (contêm senha; vêm do `.env` no Compose). |
| `AGENDAMENTOS_URL`, `DOADORES_URL` | `http://ms-agendamentos:8082`, `http://ms-doadores:8081` | Participantes HTTP; `HTTP_TIMEOUT` (3 s) por chamada. |
| `PASSO3_AGUARDAR_RESPOSTA` | `true` | Com `true` (usado no Compose), aguarda a resposta do `ms-comunicacao` por `TIMEOUT_PASSO3` (30 s). `false` faz o passo 3 concluir ao gravar o comando no Outbox (útil sem o `ms-comunicacao` no ar). |
| `MAX_RETRIES`, `BACKOFF_BASE_MS` | `5`, `500` | Retentativas por passo (ADR-002 §5.3). |
| `PRAZO_REIVINDICACAO` | `15` | Segundos que um processo fica com a SAGA durante um passo (maior que `HTTP_TIMEOUT`). |
| `RECUPERACAO_INTERVALO`, `OUTBOX_INTERVALO` | `1.0`, `0.2` | Polling dos workers (recuperação e publicador do Outbox). |
| `OUTBOX_RETENCAO_DIAS` | `7` | Limpeza das mensagens já publicadas. |
| `API_EXECUTA_WORKERS` | `true` | Os workers rodam dentro da API; **não desligue** (não há processo de worker separado). |

Logs em JSON com `request_id` (o `X-Request-Id` da requisição vira o `correlation_id` da SAGA e das mensagens); `LOG_FORMAT=texto` e `LOG_LEVEL` ajustam a saída.

## Executar

Pela raiz: `docker compose up -d --build` (sem porta no host; acesso pelo Gateway → `bff-mobile`). Localmente:

```bash
cd ms-orquestrador
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
export ORQUESTRADOR_POSTGRES_URL=postgresql+asyncpg://usuario:senha@127.0.0.1:5432/orquestrador
export ORQUESTRADOR_RABBITMQ_URL=amqp://usuario:senha@127.0.0.1:5672/
.venv/bin/uvicorn orquestrador.main:app --app-dir src --port 8003
```

Migrações Alembic (`src/orquestrador/migrations/versions/NNNN_*.py`) são aplicadas na subida; `test_migracoes_correspondem_aos_modelos` falha se ORM e migrações divergirem.

## Operação

- **Credenciais:** `ORQUESTRADOR_POSTGRES_URL` e `ORQUESTRADOR_RABBITMQ_URL` vêm do `.env` (sem padrão no código: sem elas o processo não sobe).
- **Saúde:** `/health` (liveness) e `/ready` (readiness), porta 8003.
- **Banco próprio:** `db-orquestrador` (PostgreSQL 16) com volume persistente; nenhum outro serviço o acessa.
- **Réplicas:** seguras. A migração usa *advisory lock*; o worker de recuperação e o publicador usam `FOR UPDATE SKIP LOCKED`; as transições têm lock otimista; a reivindicação impede duas réplicas de executarem o mesmo passo.
- **Rede:** só precisa alcançar `db-orquestrador`, RabbitMQ, `ms-agendamentos` e `ms-doadores`; é chamado só pelo `bff-mobile`.

## Testes e qualidade

```bash
scripts/test-docker.sh ms-orquestrador   # na raiz: ruff + mypy + pytest em python:3.12 com bancos descartáveis
scripts/e2e-saga.sh                      # na raiz: E2E pelo Gateway (caminho feliz, compensação RN01, recusa)
MANTER=1 scripts/e2e-saga.sh             # idem, deixando a stack no ar para a demonstração
```

Os testes usam o banco `orquestrador_test` (criado automaticamente) no PostgreSQL de teste (`ORQUESTRADOR_TEST_POSTGRES_URL`) e um RabbitMQ real (`ORQUESTRADOR_TEST_RABBITMQ_URL`). O script e o CI falham se algum teste for ignorado.

O E2E usa participantes simulados (`scripts/e2e-saga/participantes_fake.py`) no lugar de `ms-agendamentos`/`ms-doadores` enquanto os endpoints reais da SAGA (contratos §2) não existem: `slot-futuro` confirma, `slot-proximo` é recusado pela RN01 (doação há 10 dias) e compensado, `slot-lotado` é recusado no passo 1.
