# bff-mobile

Backend for Frontend (Python 3.12 / FastAPI), sem banco e sem estado. App móvel do doador. `GET /bff-mobile/home` agrega o perfil (`ms-doadores`) e as campanhas vigentes do tipo sanguíneo (`ms-hemocentros`), com **degradação graciosa**: se um serviço cair, responde 200 com `status: degradado`. Usuário sem cadastro de doador (404 no `ms-doadores`) não é falha: `status: ok`, perfil mínimo com `cadastrado: false` e campanhas sem filtro de tipo.

## Executar

Na raiz, execute `docker compose up -d --build`. A porta 8001 é interna ao Compose. O cliente usa o Gateway em `http://localhost:8080/api/mobile/home` com o token correspondente. Para iniciar o BFF isoladamente:

```bash
cd bff-mobile
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
BFF_MOBILE_HEMOCENTROS_URL=http://127.0.0.1:8000 .venv/bin/uvicorn bff_mobile.main:app --app-dir src --port 8001
```

O app salva o perfil com `PUT /api/mobile/perfil`. O BFF usa a identidade recebida do Gateway para encaminhar o cadastro ou atualização ao `ms-doadores`. A consulta seguinte da tela inicial pode então usar o tipo sanguíneo cadastrado.

## Agendamento (SAGA)

- `POST /bff-mobile/agendamentos` `{slotId}`: inicia a SAGA no `ms-orquestrador` com o doador autenticado (`X-User-Id`) e repassa a `Idempotency-Key`. Responde `202` com `Location` para acompanhar; repassa `409` (agendamento em andamento) e `422`; orquestrador fora → `503`. Requisição inválida (sem `slotId`, campos longos) → `400 problem+json` com `invalidParams`, sem chamar o orquestrador.
- `GET /bff-mobile/sagas/{sagaId}`: situação para o app (`EM_ANDAMENTO`, `CONFIRMADO`, `RECUSADO`, `CANCELADO`, `ERRO`), data do slot e motivo da recusa. SAGA de outro doador → `404`. Confirmada, traz o link `agendamento` para o recurso abaixo.

## Agendamento (recurso com HATEOAS)

Repassa o recurso do `ms-agendamentos` (contratos §3), reescrevendo os links internos para as rotas públicas do Gateway (`/api/mobile/...`). Agendamento de outro doador → `404`; `ms-agendamentos` fora → `503`.

- `GET /bff-mobile/agendamentos`: agendamentos do doador autenticado, do mais recente para o mais antigo.
- `GET /bff-mobile/agendamentos/{id}`: `self` sempre; `cancelar` só se `CONFIRMADO` e até 2 h antes; `novo-agendamento` depois de cancelado; nenhum link de ação em provisório, fora do prazo ou concluído.
- `GET /bff-mobile/slots` `?postoId=&de=&ate=`: horários futuros com vaga do `ms-agendamentos`, cada um com o link `agendar` (`POST /api/mobile/agendamentos`, corpo `{slotId}`).
- `POST /bff-mobile/agendamentos/{id}/cancelamento` `{motivo?}`: confere o dono, cancela e devolve o agendamento com os links novos. Repassa `409` (já cancelado, ainda provisório ou fora do prazo).

## Configuração (`BFF_MOBILE_*`)

| Variável | Padrão | Observação |
| --- | --- | --- |
| `HEMOCENTROS_URL` | `http://ms-hemocentros:8000` | |
| `DOADORES_URL` | `http://ms-doadores:8081` | Timeout curto (`DOADORES_TIMEOUT`) para degradar rápido. |
| `ORQUESTRADOR_URL` | `http://ms-orquestrador:8003` | SAGA de agendamento (`ORQUESTRADOR_TIMEOUT`, padrão 3 s). |
| `AGENDAMENTOS_URL` | `http://ms-agendamentos:8082` | Recurso Agendamento (`AGENDAMENTOS_TIMEOUT`, padrão 3 s). |
| `PREFIXO_PUBLICO` | `/api/mobile` | Prefixo dos links devolvidos ao app (rota pública no Gateway). |
| `TIPO_SANGUINEO_FALLBACK` | vazio | Sem tipo conhecido, lista todas as vigentes (`campanhasPersonalizadas: false`). |
| `EXIGIR_PAPEL` / `PAPEL_EXIGIDO` | `false` / `doador` | No Compose, a checagem está habilitada e o Gateway fornece `X-User-Roles`. |

O BFF confia em `X-User-Id` (e `X-User-Roles`) injetados pelo Gateway e propaga `X-Request-Id` às chamadas internas. Logs em JSON (`LOG_FORMAT=texto` para texto).

`GET /health` e `GET /ready` respondem sempre 200; `GET /docs` traz o OpenAPI.

## Testes

```bash
scripts/test-docker.sh bff-mobile   # na raiz: ruff + mypy + pytest em python:3.12
```
