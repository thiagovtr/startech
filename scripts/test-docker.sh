#!/usr/bin/env bash
# Roda as suítes do Dev 3 (ms-hemocentros, bff-mobile, bff-web) dentro de python:3.12-slim,
# a mesma versão dos Dockerfiles, contra PostgreSQL, MongoDB e RabbitMQ descartáveis.
# Falha se algum teste for ignorado (skip), para que a falta de um serviço de apoio não passe "verde".
#
# Uso: scripts/test-docker.sh [servico ...]   (padrão: os três)
set -euo pipefail
cd "$(dirname "$0")/.."

IMG="${PYTHON_IMAGE:-python:3.12-slim}"
SUFIXO="$$"
REDE="startech-test-$SUFIXO"
SERVICOS=("$@"); [ ${#SERVICOS[@]} -gt 0 ] || SERVICOS=(ms-hemocentros bff-mobile bff-web)

cleanup() {
  docker rm -f "t-pg-$SUFIXO" "t-mongo-$SUFIXO" "t-rmq-$SUFIXO" >/dev/null 2>&1 || true
  docker network rm "$REDE" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker network create "$REDE" >/dev/null
echo ">> subindo PostgreSQL, MongoDB e RabbitMQ descartáveis"
docker run -d --rm --name "t-pg-$SUFIXO" --network "$REDE" --network-alias pg \
  -e POSTGRES_USER=hemocentros -e POSTGRES_PASSWORD=hemocentros -e POSTGRES_DB=hemocentros \
  --health-cmd "pg_isready -U hemocentros" --health-interval 1s --health-retries 30 postgres:16-alpine >/dev/null
docker run -d --rm --name "t-mongo-$SUFIXO" --network "$REDE" --network-alias mongo mongo:7 >/dev/null
docker run -d --rm --name "t-rmq-$SUFIXO" --network "$REDE" --network-alias rmq \
  --health-cmd "rabbitmq-diagnostics -q ping" --health-interval 2s --health-retries 30 rabbitmq:3.13-alpine >/dev/null

for c in "t-pg-$SUFIXO" "t-rmq-$SUFIXO"; do
  until [ "$(docker inspect -f '{{.State.Health.Status}}' "$c")" = healthy ]; do sleep 1; done
done

for svc in "${SERVICOS[@]}"; do
  echo ">> testes de $svc ($IMG)"
  # o código é montado somente leitura e copiado: nada (venv, .egg-info, caches) é escrito no repositório
  docker run --rm --network "$REDE" -v "$PWD/$svc:/src:ro" \
    -e HEMOCENTROS_TEST_POSTGRES_URL="postgresql+asyncpg://hemocentros:hemocentros@pg:5432/hemocentros" \
    -e HEMOCENTROS_TEST_MONGO_URL="mongodb://mongo:27017" \
    -e HEMOCENTROS_TEST_RABBITMQ_URL="amqp://guest:guest@rmq:5672/" \
    "$IMG" bash -c '
      set -euo pipefail
      cp -r /src /work && cd /work && rm -rf .venv
      export PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
      pip install -q --root-user-action=ignore ".[dev]"
      python --version
      pytest -q -rs -p no:cacheprovider | tee /tmp/saida.txt
      if grep -qiE "[0-9]+ skipped" /tmp/saida.txt; then echo "FALHA: há testes ignorados (skip)"; exit 1; fi
    '
done
echo ">> OK: todas as suítes passaram em $IMG sem skips"
