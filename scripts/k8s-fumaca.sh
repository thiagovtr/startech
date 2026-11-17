#!/usr/bin/env bash
# Teste de fumaça da stack no Kubernetes, pela borda (Ingress -> Gateway), como um cliente real:
#   token do doador no Keycloak -> GET /api/mobile/home -> solicita agendamento (SAGA) -> acompanha até o fim.
# Sem participantes Java completos (endpoints da SAGA do Dev 2), a SAGA termina recusada/compensada: o teste
# verifica que ela TERMINA (fluxo distribuído íntegro), e mostra o desfecho.
#
# Uso: scripts/k8s-fumaca.sh                     (usa o Ingress em http://startech.local)
#      BASE=http://localhost:8080 scripts/k8s-fumaca.sh   (com kubectl -n startech port-forward svc/gateway 8080)
set -euo pipefail
BASE="${BASE:-http://startech.local}"

json() { python3 -c 'import json,sys
v=json.load(sys.stdin)
for k in sys.argv[1].split("."): v=v[k]
print(v)' "$1"; }

echo ">> token do doador (Keycloak via Gateway)"
TOKEN=$(curl -fsS -X POST "$BASE/realms/startech/protocol/openid-connect/token" \
  -d "client_id=mobile&grant_type=password&username=doador1&password=doador123" | json access_token)
AUTH=(-H "Authorization: Bearer $TOKEN")

echo ">> GET /api/mobile/home"
curl -fsS "$BASE/api/mobile/home" "${AUTH[@]}" | head -c 400; echo

echo ">> POST /api/mobile/agendamentos (SAGA)"
corpo=$(curl -fsS -X POST "$BASE/api/mobile/agendamentos" "${AUTH[@]}" -H "Content-Type: application/json" \
  -H "Idempotency-Key: fumaca-$(date +%s)" -d '{"slotId":"slot-fumaca"}')
SAGA=$(echo "$corpo" | json sagaId)
for _ in $(seq 1 90); do
  estado=$(curl -fsS "$BASE/api/mobile/sagas/$SAGA" "${AUTH[@]}")
  [ "$(echo "$estado" | json finalizada)" = "True" ] && { echo "   SAGA $SAGA: $(echo "$estado" | json situacao)"; break; }
  sleep 1
done
[ "$(echo "$estado" | json finalizada)" = "True" ] || { echo "FALHA: SAGA não terminou: $estado"; exit 1; }
echo ">> fumaça OK"
