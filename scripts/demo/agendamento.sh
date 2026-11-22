#!/usr/bin/env bash
# HATEOAS: mostra o agendamento e os links que ele oferece; com `cancelar`, segue o link `cancelar`.
# Uso: scripts/demo/agendamento.sh <agendamentoId> [cancelar]
source "$(dirname "$0")/comum.sh"
[ $# -ge 1 ] || falha "uso: $0 <agendamentoId> [cancelar]"
TOKEN=$(token_doador)

titulo "GET /api/mobile/agendamentos/$1"
ag=$(curl -s "$GATEWAY/api/mobile/agendamentos/$1" -H "Authorization: Bearer $TOKEN")
echo "$ag" | bonito
echo "   links disponíveis: $(echo "$ag" | python3 -c 'import json,sys;print(", ".join(json.load(sys.stdin)["_links"]))')"

if [ "${2:-}" = "cancelar" ]; then
  href=$(echo "$ag" | python3 -c 'import json,sys;print(json.load(sys.stdin)["_links"].get("cancelar",{}).get("href",""))')
  [ -n "$href" ] || falha "o agendamento não oferece o link cancelar (estado: $(echo "$ag" | json status))"
  titulo "POST $href (link cancelar)"
  resp=$(curl -s -X POST "$GATEWAY$href" -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" -d '{"motivo":"Imprevisto pessoal"}')
  echo "$resp" | bonito
  echo "   links agora: $(echo "$resp" | python3 -c 'import json,sys;print(", ".join(json.load(sys.stdin)["_links"]))')"
  titulo "cancelar de novo (esperado 409)"
  curl -s -w '\n   HTTP %{http_code}\n' -X POST "$GATEWAY$href" -H "Authorization: Bearer $TOKEN"
fi
