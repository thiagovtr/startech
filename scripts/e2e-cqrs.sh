#!/usr/bin/env bash
# E2E da plataforma StarTech pela borda publica do API Gateway (com Keycloak, BFFs, CQRS e RabbitMQ):
#   1. Autentica no Keycloak (doador1 / mobile e operador1 / web) via Gateway (/realms/startech/...)
#   2. Valida bloqueio RBAC/Audience de rota cruzada (403 Forbidden) e Header Stripping
#   3. Mede atraso escrita->leitura CQRS (POST /api/web/campanhas -> PostgreSQL+Outbox -> RabbitMQ -> MongoDB -> GET)
#   4. Valida degradacao graciosa no BFF Mobile (GET /api/mobile/home -> 200 degradado)
#
# Uso: scripts/e2e-cqrs.sh [N_AMOSTRAS]    (padrao: 20)
set -euo pipefail
export LC_ALL=C

N="${1:-20}"
export GATEWAY_HOST_PORT="${GATEWAY_HOST_PORT:-18080}"
export KEYCLOAK_HOST_PORT="${KEYCLOAK_HOST_PORT:-18089}"
export RABBITMQ_AMQP_PORT="${RABBITMQ_AMQP_PORT:-15672}"
export RABBITMQ_MGMT_PORT="${RABBITMQ_MGMT_PORT:-25672}"
LIMITE=2.0
cd "$(dirname "$0")/.."

cleanup() {
  docker compose down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo ">> subindo a stack completa via Docker Compose"
docker compose up -d --build --wait >/dev/null

GATEWAY="http://localhost:${GATEWAY_HOST_PORT}"
TOKEN_URL="${GATEWAY}/realms/startech/protocol/openid-connect/token"
BODY='{"titulo":"E2E %s","hemocentro":"Lavras","tipo_sanguineo":"O-","urgencia":"CRITICO","data_inicio":"2026-11-10","data_fim":"2026-11-30"}'
agora() { date +%s.%N; }

echo ">> obtendo tokens JWT RS256 no Keycloak (via proxy do Gateway)"
RESP_DOADOR=$(curl -s -X POST "$TOKEN_URL" -d "client_id=mobile&grant_type=password&username=doador1&password=doador123")
TOKEN_DOADOR=$(echo "$RESP_DOADOR" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
RESP_OPERADOR=$(curl -s -X POST "$TOKEN_URL" -d "client_id=web&grant_type=password&username=operador1&password=operador123")
TOKEN_OPERADOR=$(echo "$RESP_OPERADOR" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')

[ -n "$TOKEN_DOADOR" ] || { echo "FALHA: token do doador vazio (resposta: $RESP_DOADOR)"; exit 1; }
[ -n "$TOKEN_OPERADOR" ] || { echo "FALHA: token do operador vazio (resposta: $RESP_OPERADOR)"; exit 1; }

echo ">> validando RBAC, Audience e Header Stripping no API Gateway"
status_sem_token=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/api/mobile/home")
[ "$status_sem_token" = "401" ] || { echo "FALHA: esperado 401 sem token, veio $status_sem_token"; exit 1; }

status_cruzado_web=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/api/web/campanhas" \
  -H "Authorization: Bearer $TOKEN_DOADOR" -H "X-User-Roles: operador")
[ "$status_cruzado_web" = "403" ] || { echo "FALHA: doador acessou /api/web (status $status_cruzado_web)"; exit 1; }

status_cruzado_mobile=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/api/mobile/home" \
  -H "Authorization: Bearer $TOKEN_OPERADOR" -H "X-User-Roles: doador")
[ "$status_cruzado_mobile" = "403" ] || { echo "FALHA: operador acessou /api/mobile (status $status_cruzado_mobile)"; exit 1; }
echo "   ok: 401 sem token e 403 em acessos cruzados (mesmo com X-User-Roles forjado)"

echo ">> aguardando os workers conectarem ao RabbitMQ (aquecimento)"
ok=0
for _ in $(seq 1 40); do
  id=$(curl -s -X POST "$GATEWAY/api/web/campanhas" \
    -H "Authorization: Bearer $TOKEN_OPERADOR" \
    -H "Content-Type: application/json" \
    -d "$(printf "$BODY" warmup)" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p')
  sleep 1
  if curl -s "$GATEWAY/api/web/campanhas?tipo_sanguineo=O-" \
    -H "Authorization: Bearer $TOKEN_OPERADOR" | grep -q "$id"; then
    ok=1
    break
  fi
done
[ "$ok" = 1 ] || { echo "FALHA: a campanha não chegou ao MongoDB"; exit 1; }

echo ">> medindo $N escritas via Gateway -> BFF Web -> MS-Hemocentros -> Outbox -> RabbitMQ -> MongoDB"
lat=()
for i in $(seq 1 "$N"); do
  t0=$(agora)
  id=$(curl -s -X POST "$GATEWAY/api/web/campanhas" \
    -H "Authorization: Bearer $TOKEN_OPERADOR" \
    -H "Content-Type: application/json" \
    -d "$(printf "$BODY" "$i")" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p')
  [ -n "$id" ] || { echo "FALHA: POST sem id"; exit 1; }
  until curl -s "$GATEWAY/api/web/campanhas?tipo_sanguineo=O-" \
    -H "Authorization: Bearer $TOKEN_OPERADOR" | grep -q "$id"; do
    [ "$(echo "$(agora) - $t0 > 10" | bc)" = 1 ] && { echo "FALHA: $id não apareceu em 10 s"; exit 1; }
    sleep 0.02
  done
  lat+=("$(echo "$(agora) - $t0" | bc)")
done

sorted=($(printf '%s\n' "${lat[@]}" | sort -n))
med=${sorted[$((N / 2))]}; max=${sorted[$((N - 1))]}
printf ">> latência POST->visível no GET (via Gateway + BFF Web): n=%s mediana=%.3fs max=%.3fs (limite %.1fs)\n" "$N" "$med" "$max" "$LIMITE"
[ "$(echo "$max < $LIMITE" | bc)" = 1 ] || { echo "FALHA: acima de ${LIMITE}s"; exit 1; }

echo ">> BFF Mobile via Gateway com o ms-doadores no ar: home completa (perfil + campanhas)"
resp_mobile=$(curl -s "$GATEWAY/api/mobile/home" -H "Authorization: Bearer $TOKEN_DOADOR")
echo "$resp_mobile" | grep -q '"status":"ok"' || { echo "FALHA: home esperada completa: $resp_mobile"; exit 1; }
echo "$resp_mobile" | grep -q '"tipo_sanguineo":"O-"' || { echo "FALHA: perfil do doador ausente: $resp_mobile"; exit 1; }
echo "   ok: 200 com o perfil do doador e campanhas personalizadas"

echo ">> BFF Mobile via Gateway (ms-doadores parado): degradação graciosa + injeção de X-User-Id do JWT"
docker compose stop ms-doadores >/dev/null
resp_mobile=$(curl -s "$GATEWAY/api/mobile/home" -H "Authorization: Bearer $TOKEN_DOADOR")
docker compose start ms-doadores >/dev/null
echo "$resp_mobile" | grep -q '"status":"degradado"' || { echo "FALHA: BFF Mobile não retornou status degradado"; exit 1; }
echo "$resp_mobile" | grep -q '11111111-1111-1111-1111-111111111111' || { echo "FALHA: X-User-Id (sub do JWT) não propagou ao BFF Mobile"; exit 1; }
echo "   ok: 200 degradado com X-User-Id=11111111-1111-1111-1111-111111111111"
echo ">> E2E OK"
