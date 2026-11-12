#!/usr/bin/env bash
# E2E do CQRS (Dev 3), pela borda dos BFFs, com serviços reais:
#   POST bff-web -> ms-hemocentros -> PostgreSQL+Outbox -> RabbitMQ -> consumidor -> MongoDB -> GET bff-web/bff-mobile
# Mede o atraso escrita->leitura (meta: < 2 s). Usa um RabbitMQ descartável enquanto o do Dev 1
# não estiver no compose.yaml; se o compose já tiver o serviço `rabbitmq`, ele é usado (EXTERNAL_RABBIT=1).
#
# Uso: scripts/e2e-cqrs.sh [N_AMOSTRAS]    (padrão: 20)
set -euo pipefail
export LC_ALL=C  # separador decimal "." em printf/sort/bc

N="${1:-20}"
export HEMOCENTROS_HOST_PORT="${HEMOCENTROS_HOST_PORT:-18000}"
export BFF_MOBILE_HOST_PORT="${BFF_MOBILE_HOST_PORT:-18001}"
export BFF_WEB_HOST_PORT="${BFF_WEB_HOST_PORT:-18002}"
RABBIT_NAME="startech-e2e-rabbitmq"
LIMITE=2.0
cd "$(dirname "$0")/.."

cleanup() {
  [ "${EXTERNAL_RABBIT:-0}" = "1" ] || docker stop "$RABBIT_NAME" >/dev/null 2>&1 || true
  docker compose down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo ">> subindo a stack"
docker compose up -d --build --wait >/dev/null
if [ "${EXTERNAL_RABBIT:-0}" != "1" ]; then
  echo ">> subindo RabbitMQ descartável na rede startech-net-api (alias: rabbitmq)"
  docker run -d --rm --name "$RABBIT_NAME" --network startech-net-api --network-alias rabbitmq \
    rabbitmq:3.13-alpine >/dev/null
fi

BODY='{"titulo":"E2E %s","hemocentro":"Lavras","tipo_sanguineo":"O-","urgencia":"CRITICO","data_inicio":"2026-11-10","data_fim":"2026-11-30"}'
WEB="localhost:${BFF_WEB_HOST_PORT}"
agora() { date +%s.%N; }

echo ">> aguardando os workers conectarem ao RabbitMQ (aquecimento)"
ok=0
for _ in $(seq 1 40); do
  id=$(curl -s -X POST "$WEB/bff-web/campanhas" -H 'content-type: application/json' -d "$(printf "$BODY" warmup)" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p')
  sleep 1
  if curl -s "$WEB/bff-web/campanhas?tipo_sanguineo=O-" | grep -q "$id"; then ok=1; break; fi
done
[ "$ok" = 1 ] || { echo "FALHA: a campanha não chegou ao MongoDB (RabbitMQ/consumidor indisponível?)"; exit 1; }

echo ">> medindo $N escritas"
lat=()
for i in $(seq 1 "$N"); do
  t0=$(agora)
  id=$(curl -s -X POST "$WEB/bff-web/campanhas" -H 'content-type: application/json' -d "$(printf "$BODY" "$i")" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p')
  [ -n "$id" ] || { echo "FALHA: POST sem id"; exit 1; }
  until curl -s "$WEB/bff-web/campanhas?tipo_sanguineo=O-" | grep -q "$id"; do
    [ "$(echo "$(agora) - $t0 > 10" | bc)" = 1 ] && { echo "FALHA: $id não apareceu em 10 s"; exit 1; }
    sleep 0.02
  done
  lat+=("$(echo "$(agora) - $t0" | bc)")
done

sorted=($(printf '%s\n' "${lat[@]}" | sort -n))
med=${sorted[$((N / 2))]}; max=${sorted[$((N - 1))]}
printf ">> latência POST->visível no GET (via BFF Web): n=%s mediana=%.3fs max=%.3fs (limite %.1fs)\n" "$N" "$med" "$max" "$LIMITE"
[ "$(echo "$max < $LIMITE" | bc)" = 1 ] || { echo "FALHA: acima de ${LIMITE}s"; exit 1; }

echo ">> BFF Mobile (sem ms-doadores): degradação graciosa"
curl -s "localhost:${BFF_MOBILE_HOST_PORT}/bff-mobile/home" -H 'X-User-Id: 123' | grep -q '"status":"degradado"' \
  && echo "   ok: 200 degradado, sem erro 500"
echo ">> E2E OK"
