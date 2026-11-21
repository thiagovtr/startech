#!/usr/bin/env bash
# CQRS: cria uma campanha pelo BFF Web (escrita no PostgreSQL + Outbox) e mede quando ela aparece na home do
# app (leitura no MongoDB, projetada pelo consumidor do RabbitMQ). Mostra a campanha nos dois bancos.
source "$(dirname "$0")/comum.sh"
TITULO="Demonstração CQRS $(date +%H:%M:%S)"
hoje=$(date +%F); fim=$(date -d '+30 days' +%F)

titulo "POST /api/web/campanhas \"$TITULO\""
inicio=$(date +%s.%N)
id=$(curl -s -X POST "$GATEWAY/api/web/campanhas" -H "Authorization: Bearer $(token_operador)" \
  -H "Content-Type: application/json" \
  -d "{\"titulo\":\"$TITULO\",\"hemocentro\":\"Hemominas Lavras\",\"tipo_sanguineo\":\"O-\",\"urgencia\":\"CRITICO\",\"data_inicio\":\"$hoje\",\"data_fim\":\"$fim\"}" \
  | json id)
echo "   id: $id"

TOKEN=$(token_doador)
for _ in $(seq 1 100); do
  curl -s "$GATEWAY/api/mobile/home" -H "Authorization: Bearer $TOKEN" | grep -q "$id" && break
  sleep 0.1
done
fim_s=$(date +%s.%N)
printf '   visível na home do app em %.3f s\n' "$(echo "$fim_s - $inicio" | bc)"

titulo "modelo de escrita (db-hemocentros, PostgreSQL) e outbox"
sql db-hemocentros hemocentros hemocentros "SELECT id, titulo, tipo_sanguineo, versao FROM campanhas WHERE id = '$id'"
sql db-hemocentros hemocentros hemocentros \
  "SELECT routing_key, published, published_at - created_at AS atraso FROM outbox_events WHERE aggregate_id = '$id'"
titulo "modelo de leitura (mongo)"
"${COMPOSE[@]}" exec -T mongo mongosh --quiet hemocentros --eval \
  "db.getCollectionNames().forEach(c => { const d = db[c].findOne({\$or: [{_id: '$id'}, {id: '$id'}]}); if (d) printjson({colecao: c, documento: d}); })"
