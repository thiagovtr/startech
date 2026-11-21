#!/usr/bin/env bash
# Plano B do app: agenda pelo Gateway como o app faria, seguindo os links, e acompanha a SAGA até o fim.
# Uso: scripts/demo/agendar.sh <slotId>       (ex.: slot-futuro, slot-proximo, slot-lotado)
source "$(dirname "$0")/comum.sh"
[ $# -eq 1 ] || falha "uso: $0 <slotId>"
TOKEN=$(token_doador)

titulo "POST /api/mobile/agendamentos {slotId: $1}"
resp=$(curl -s -X POST "$GATEWAY/api/mobile/agendamentos" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -H "Idempotency-Key: demo-$(date +%s%N)" -d "{\"slotId\":\"$1\"}")
echo "$resp" | bonito
link=$(echo "$resp" | json _links.acompanhar.href)

titulo "acompanhando $link"
for _ in $(seq 1 120); do
  corpo=$(curl -s "$GATEWAY$link" -H "Authorization: Bearer $TOKEN")
  echo "   situação: $(echo "$corpo" | json situacao)"
  [ "$(echo "$corpo" | json finalizada)" = "True" ] && break
  sleep 0.5
done
echo "$corpo" | bonito
echo
echo "evidências em cada participante: scripts/demo/evidencia-saga.sh $(echo "$corpo" | json sagaId)"
