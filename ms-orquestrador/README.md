# ms-orquestrador

Orquestrador da SAGA de agendamento (Python 3.12 / FastAPI), com banco PostgreSQL e Transactional Outbox próprios (ADR-006). Coordena `ms-agendamentos`, `ms-doadores` e `ms-comunicacao`; não tem regras de domínio.

> Em construção: estrutura inicial (health, configuração, Docker e CI). A SAGA é implementada nos próximos blocos.

## Executar

```bash
cd ms-orquestrador
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
export ORQUESTRADOR_POSTGRES_URL=postgresql+asyncpg://usuario:senha@127.0.0.1:15432/orquestrador
export ORQUESTRADOR_RABBITMQ_URL=amqp://usuario:senha@127.0.0.1:15672/
.venv/bin/uvicorn orquestrador.main:app --app-dir src --port 8003
```

## Testes e qualidade

```bash
scripts/test-docker.sh ms-orquestrador   # na raiz: ruff + mypy + pytest em python:3.12 com bancos descartáveis
```

Os testes usam o banco `orquestrador_test` (criado automaticamente) no mesmo servidor PostgreSQL de teste do `ms-hemocentros`, apontado por `ORQUESTRADOR_TEST_POSTGRES_URL`.
