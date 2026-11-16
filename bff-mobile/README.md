# bff-mobile

Backend for Frontend (Python 3.12 / FastAPI), sem banco e sem estado. App móvel do doador. `GET /bff-mobile/home` agrega o perfil (`ms-doadores`) e as campanhas vigentes do tipo sanguíneo (`ms-hemocentros`), com **degradação graciosa**: se um serviço cair, responde 200 com `status: degradado`.

## Executar

Pela raiz: `docker compose up -d --build` (porta 8001). Localmente:

```bash
cd bff-mobile
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
BFF_MOBILE_HEMOCENTROS_URL=http://127.0.0.1:8000 .venv/bin/uvicorn bff_mobile.main:app --app-dir src --port 8001
```

## Configuração (`BFF_MOBILE_*`)

| Variável | Padrão | Observação |
| --- | --- | --- |
| `HEMOCENTROS_URL` | `http://ms-hemocentros:8000` | |
| `DOADORES_URL` | `http://ms-doadores:8081` | Timeout curto (`DOADORES_TIMEOUT`) para degradar rápido. |
| `TIPO_SANGUINEO_FALLBACK` | vazio | Sem tipo conhecido, lista todas as vigentes (`campanhasPersonalizadas: false`). |
| `EXIGIR_PAPEL` / `PAPEL_EXIGIDO` | `false` / `doador` | Checagem de `X-User-Roles` (ligar quando o Gateway injetar o cabeçalho). |

O BFF confia em `X-User-Id` (e `X-User-Roles`) injetados pelo Gateway e propaga `X-Request-Id` às chamadas internas. Logs em JSON (`LOG_FORMAT=texto` para texto).

`GET /health` e `GET /ready` respondem sempre 200; `GET /docs` traz o OpenAPI.

## Testes

```bash
scripts/test-docker.sh bff-mobile   # na raiz: ruff + mypy + pytest em python:3.12
```
