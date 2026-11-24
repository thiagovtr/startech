# bff-web

Backend for Frontend (Python 3.12 / FastAPI), sem banco e sem estado. Painel web dos hemocentros. `POST` e `GET /bff-web/campanhas` repassam ao `ms-hemocentros` (criação com Read-Your-Own-Writes e listagem paginada), traduzindo falhas internas em `problem+json` (503/504/502).

## Executar

Na raiz, execute `docker compose up -d --build`. A porta 8002 é interna ao Compose. O cliente usa o Gateway em `http://localhost:8080/api/web/campanhas` com o token correspondente. Para iniciar o BFF isoladamente:

```bash
cd bff-web
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
BFF_WEB_HEMOCENTROS_URL=http://127.0.0.1:8000 .venv/bin/uvicorn bff_web.main:app --app-dir src --port 8002
```

## Configuração (`BFF_WEB_*`)

| Variável | Padrão | Observação |
| --- | --- | --- |
| `HEMOCENTROS_URL` | `http://ms-hemocentros:8000` | |
| `EXIGIR_PAPEL` / `PAPEL_EXIGIDO` | `false` / `operador` | No Compose, a checagem está habilitada e o Gateway fornece `X-User-Roles`. |

O BFF confia em `X-User-Id` (e `X-User-Roles`) injetados pelo Gateway e propaga `X-Request-Id` às chamadas internas. Logs em JSON (`LOG_FORMAT=texto` para texto).

`GET /health` e `GET /ready` respondem sempre 200; `GET /docs` traz o OpenAPI.

## Testes

```bash
scripts/test-docker.sh bff-web   # na raiz: ruff + mypy + pytest em python:3.12
```
