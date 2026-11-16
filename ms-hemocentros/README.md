# ms-hemocentros

Microsserviço de hemocentros e campanhas (Python 3.12 / FastAPI). Aplica **CQRS**: escrita no PostgreSQL com **Transactional Outbox**, publicação no RabbitMQ e projeção para leitura no MongoDB.

## Executar

Pela raiz do repositório (sobe tudo com bancos):

```bash
cp .env.example .env          # opcional: valores de desenvolvimento
docker compose up -d --build
curl localhost:8000/ready     # 200 quando PostgreSQL e MongoDB estão ok
```

Localmente, sem Docker para o serviço:

```bash
cd ms-hemocentros
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
export HEMOCENTROS_POSTGRES_URL=postgresql+asyncpg://hemocentros:hemocentros@127.0.0.1:15432/hemocentros
export HEMOCENTROS_RABBITMQ_URL=amqp://guest:guest@127.0.0.1:15672/
export HEMOCENTROS_MONGO_URL=mongodb://127.0.0.1:17017
.venv/bin/uvicorn hemocentros.main:app --app-dir src --port 8000
```

Só os workers (sem API): `python -m hemocentros.worker`; com `HEMOCENTROS_API_EXECUTA_WORKERS=false` a API não os executa.

## Endpoints

| Rota | Descrição |
| --- | --- |
| `POST /api/v1/campanhas` | Cria campanha + evento no Outbox (mesma transação). |
| `GET /api/v1/campanhas` | Lê do MongoDB; filtros `tipo_sanguineo`, `status`, `vigentes`, paginação `limit`/`offset`, total em `X-Total-Count`. |
| `GET /health` | Liveness (sempre 200; estado dos bancos no corpo). |
| `GET /ready` | Readiness (503 se PostgreSQL ou MongoDB estiver fora). |
| `GET /docs` | OpenAPI. |

## Configuração (`HEMOCENTROS_*`)

| Variável | Padrão | Observação |
| --- | --- | --- |
| `POSTGRES_URL`, `RABBITMQ_URL` | — | **Obrigatórias** (contêm senha; Secret no K8s). |
| `MONGO_URL`, `MONGO_DB` | `mongodb://mongo:27017`, `hemocentros` | |
| `RABBITMQ_EXCHANGE`, `RABBITMQ_QUEUE` | `startech.events.exchange`, `hemocentros.cqrs` | `DECLARAR_EXCHANGE`/`DECLARAR_FILA` controlam quem declara a topologia. |
| `RABBITMQ_DLQ_HABILITADA` | `false` | Dead-letter para mensagens inválidas. |
| `OUTBOX_RETENCAO_DIAS` | `7` | Limpeza de eventos já publicados. |
| `API_EXECUTA_WORKERS` | `true` | |

Logs em JSON com `request_id` (`X-Request-Id`); `LOG_FORMAT=texto` e `LOG_LEVEL` ajustam a saída.

## Esquema do banco

Migrações Alembic em `src/hemocentros/migrations/`, aplicadas automaticamente na partida (API e worker). Para criar uma nova, adicione um arquivo em `versions/` seguindo o padrão `NNNN_descricao.py`; o teste `test_migracoes_correspondem_aos_modelos` falha se o ORM e as migrações divergirem.

## Testes e qualidade

```bash
scripts/test-docker.sh ms-hemocentros   # na raiz: ruff + mypy + pytest em python:3.12 com bancos descartáveis
```

O script (e o CI) falha se algum teste for ignorado por falta de PostgreSQL, MongoDB ou RabbitMQ.
