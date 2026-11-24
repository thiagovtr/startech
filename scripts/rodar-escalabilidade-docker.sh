#!/usr/bin/env bash
# Executa o benchmark comparativo de escalabilidade horizontal no Docker Compose
# (1 réplica vs. 3 réplicas do ms-hemocentros) usando o container oficial grafana/k6.
# Uso (na raiz do repositório): scripts/rodar-escalabilidade-docker.sh
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RAIZ"

rodar_rodada() {
  local replicas="$1"
  local rotulo="${replicas}-replica"
  [ "$replicas" -gt 1 ] && rotulo="${replicas}-replicas"

  printf '\n\033[1m== Rodada: %s (ms-hemocentros=%s)\033[0m\n' "$rotulo" "$replicas"
  docker compose up -d --no-recreate --scale "ms-hemocentros=${replicas}" ms-hemocentros >/dev/null
  sleep 6

  echo "   containers ms-hemocentros ativos:"
  docker compose ps ms-hemocentros --format "table {{.Name}}\t{{.Status}}"

  docker run --rm --network startech-net-api \
    -e "RODADA=${rotulo}" \
    -e "HEMOCENTROS_BASE=http://ms-hemocentros:8000" \
    -e "GATEWAY_BASE=http://gateway:8080" \
    -v "${RAIZ}/scripts:/scripts:ro" \
    grafana/k6:0.54.0 run --quiet /scripts/k6-escalabilidade.js || true

  sleep 3
  local pg_total outbox_pend mongo_total
  pg_total=$(docker compose exec -T db-hemocentros psql -U hemocentros -d hemocentros -tAc "SELECT COUNT(*) FROM campanhas;")
  outbox_pend=$(docker compose exec -T db-hemocentros psql -U hemocentros -d hemocentros -tAc "SELECT COUNT(*) FROM outbox_events WHERE published = false;")
  mongo_total=$(docker compose exec -T mongo mongosh --quiet hemocentros --eval "db.campanhas_view.countDocuments({})" | tr -d '[:space:]')
  echo "=== CONSISTENCIA_CQRS (${rotulo}) === pg=${pg_total} outbox_pendentes=${outbox_pend} mongo=${mongo_total}"
}

trap 'docker compose up -d --no-recreate --scale ms-hemocentros=1 ms-hemocentros >/dev/null 2>&1 || true' EXIT

rodar_rodada 1
rodar_rodada 3

printf '\n\033[1m== Finalizado (ms-hemocentros restaurado para 1 réplica)\033[0m\n'
