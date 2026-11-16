#!/usr/bin/env bash
# E2E da SAGA de agendamento pela borda pública (Gateway -> BFF Mobile -> ms-orquestrador -> participantes),
# com PostgreSQL, Outbox e RabbitMQ reais. ms-agendamentos/ms-doadores são substituídos por participantes
# simulados (scripts/e2e-saga/participantes_fake.py) enquanto os endpoints reais não existem.
#   1. Caminho feliz:   slot-futuro  -> CONFIRMADO (passos 1, 2, 3 via Outbox e 4)
#   2. Compensação:     slot-proximo -> doador inapto (RN01, 422) -> vaga liberada -> CANCELADO
#   3. Recusa:          slot-lotado  -> 409 no passo 1 -> RECUSADO, sem compensação
#   + Idempotency-Key repetida devolve a mesma SAGA; comandos do passo 3 ficam na fila do ms-comunicacao.
#
# Uso: scripts/e2e-saga.sh            (MANTER=1 deixa a stack no ar ao final, para a demonstração)
set -euo pipefail
export LC_ALL=C

export GATEWAY_HOST_PORT="${GATEWAY_HOST_PORT:-18080}"
export KEYCLOAK_HOST_PORT="${KEYCLOAK_HOST_PORT:-18089}"
export RABBITMQ_AMQP_PORT="${RABBITMQ_AMQP_PORT:-15672}"
export RABBITMQ_MGMT_PORT="${RABBITMQ_MGMT_PORT:-25672}"
cd "$(dirname "$0")/.."
COMPOSE=(docker compose -f compose.yaml -f scripts/e2e-saga/compose.e2e.yaml)

cleanup() {
  [ "${MANTER:-0}" = "1" ] && { echo ">> stack mantida no ar (MANTER=1); para derrubar: ${COMPOSE[*]} down -v"; return; }
  "${COMPOSE[@]}" down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

json() {  # json '<campo.subcampo>' < corpo
  python3 -c 'import json,sys
v=json.load(sys.stdin)
for k in sys.argv[1].split("."):
    v=v[k] if isinstance(v,dict) else v[int(k)]
print(v if not isinstance(v,(dict,list)) else json.dumps(v,ensure_ascii=False))' "$1"
}
falha() { echo "FALHA: $*"; exit 1; }

echo ">> subindo a stack com os participantes simulados"
"${COMPOSE[@]}" up -d --build --wait >/dev/null

GATEWAY="http://localhost:${GATEWAY_HOST_PORT}"
TOKEN=$(curl -s -X POST "$GATEWAY/realms/startech/protocol/openid-connect/token" \
  -d "client_id=mobile&grant_type=password&username=doador1&password=doador123" | json access_token)
[ -n "$TOKEN" ] || falha "token do doador vazio"
AUTH=(-H "Authorization: Bearer $TOKEN")

solicitar() {  # solicitar <slot> [idempotency-key] -> imprime "status corpo"
  local chave=${2:-$(python3 -c 'import uuid;print(uuid.uuid4())')}
  curl -s -w '\n%{http_code}' -X POST "$GATEWAY/api/mobile/agendamentos" "${AUTH[@]}" \
    -H "Content-Type: application/json" -H "Idempotency-Key: $chave" -d "{\"slotId\":\"$1\"}"
}

aguardar() {  # aguardar <sagaId> -> imprime o corpo final do GET (situação final)
  local corpo
  for _ in $(seq 1 60); do
    corpo=$(curl -s "$GATEWAY/api/mobile/sagas/$1" "${AUTH[@]}")
    [ "$(echo "$corpo" | json finalizada)" = "True" ] && { echo "$corpo"; return; }
    sleep 0.5
  done
  falha "SAGA $1 não terminou em 30 s: $corpo"
}

passos() {  # trilha de auditoria completa, direto no orquestrador (rede interna)
  "${COMPOSE[@]}" exec -T ms-orquestrador python -c "
import json, urllib.request
d = json.load(urllib.request.urlopen('http://127.0.0.1:8003/api/v1/sagas/$1'))
print('   status final:', d['status'])
for p in d['passos']:
    print(f\"   {p['passo']:5} {p['direcao']:10} {p['resultado']}\")"
}

estado_fake() { "${COMPOSE[@]}" exec -T participantes-fake python -c \
  "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:9000/fake/estado').read().decode())"; }

# ----------------------------------------------------------------------------------------------- 1
echo ">> 1. caminho feliz (slot-futuro: doador apto)"
CHAVE="e2e-$(date +%s)"
resp=$(solicitar slot-futuro "$CHAVE"); status=$(echo "$resp" | tail -1); corpo=$(echo "$resp" | head -1)
[ "$status" = "202" ] || falha "POST esperado 202, veio $status: $corpo"
SAGA1=$(echo "$corpo" | json sagaId); AG1=$(echo "$corpo" | json agendamentoId)
final=$(aguardar "$SAGA1")
[ "$(echo "$final" | json situacao)" = "CONFIRMADO" ] || falha "esperado CONFIRMADO: $final"
passos "$SAGA1"
[ "$(estado_fake | json "agendamentos.$AG1.status")" = "CONFIRMADO" ] || falha "agendamento não confirmado no participante"
echo "   ok: CONFIRMADO; agendamento $AG1 confirmado em ms-agendamentos (simulado)"

echo ">> idempotência: mesma Idempotency-Key devolve a mesma SAGA"
resp=$(solicitar slot-futuro "$CHAVE")
[ "$(echo "$resp" | head -1 | json sagaId)" = "$SAGA1" ] || falha "Idempotency-Key repetida criou outra SAGA"
echo "   ok: sagaId $SAGA1"

# ----------------------------------------------------------------------------------------------- 2
echo ">> 2. compensação (slot-proximo: doou há 10 dias, RN01 exige 60)"
antes=$(estado_fake | json slots.slot-proximo.ocupadas)
resp=$(solicitar slot-proximo); status=$(echo "$resp" | tail -1); corpo=$(echo "$resp" | head -1)
[ "$status" = "202" ] || falha "POST esperado 202, veio $status: $corpo"
SAGA2=$(echo "$corpo" | json sagaId); AG2=$(echo "$corpo" | json agendamentoId)
final=$(aguardar "$SAGA2")
[ "$(echo "$final" | json situacao)" = "CANCELADO" ] || falha "esperado CANCELADO: $final"
echo "   motivo exibido no app: $(echo "$final" | json motivo)"
passos "$SAGA2"
estado=$(estado_fake)
[ "$(echo "$estado" | json "agendamentos.$AG2.status")" = "CANCELADO_COMPENSACAO_SAGA" ] || falha "agendamento não compensado"
[ "$(echo "$estado" | json slots.slot-proximo.ocupadas)" = "$antes" ] || falha "a vaga não foi liberada"
echo "   ok: CANCELADO; vaga devolvida (ocupadas=$antes) e agendamento CANCELADO_COMPENSACAO_SAGA"

# ----------------------------------------------------------------------------------------------- 3
echo ">> 3. recusa sem compensação (slot-lotado: 409 no passo 1)"
SAGA3=$(solicitar slot-lotado | head -1 | json sagaId)
final=$(aguardar "$SAGA3")
[ "$(echo "$final" | json situacao)" = "RECUSADO" ] || falha "esperado RECUSADO: $final"
passos "$SAGA3"
echo "   ok: RECUSADO"

# ----------------------------------------------------------------------------------------------- Outbox
echo ">> Outbox -> RabbitMQ: comandos do passo 3 aguardando o ms-comunicacao"
filas=$("${COMPOSE[@]}" exec -T rabbitmq rabbitmqctl -q list_queues name messages)
echo "$filas" | grep -E "comunicacao.saga.comandos|saga.compensations.dlq|orquestrador.saga.respostas" | sed 's/^/   /'
n=$(echo "$filas" | awk '$1=="comunicacao.saga.comandos"{print $2}')
[ "${n:-0}" -ge 1 ] || falha "nenhum comando na fila comunicacao.saga.comandos"
echo ">> E2E da SAGA OK"
