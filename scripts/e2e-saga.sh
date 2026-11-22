#!/usr/bin/env bash
# E2E da SAGA de agendamento pela borda pública (Gateway -> BFF Mobile -> ms-orquestrador -> participantes),
# com PostgreSQL, Outbox e RabbitMQ reais. O ms-agendamentos (passos 1 e 4) é o real, com a grade do perfil
# `demo`, e o estado dele é conferido direto no db-agendamentos. Só o passo 2 (ms-doadores, RN01) ainda é
# simulado (scripts/e2e-saga/participantes_fake.py), até o endpoint real existir.
#   0. Grade: GET /api/mobile/slots traz slot-futuro e slot-proximo, com o link agendar; slot-lotado não aparece.
#      As solicitações seguem o link `agendar` da grade, e as vagas disponíveis acompanham reserva e cancelamento
#   1. Caminho feliz:   slot-futuro  -> CONFIRMADO (passos 1, 2, 3 via Outbox e 4)
#   1b. Consulta e cancelamento com HATEOAS: o link `agendamento` da SAGA confirmada leva ao recurso, que tem
#       `cancelar`; cancelar libera a vaga e troca os links (`novo-agendamento`, sem `cancelar`); de novo -> 409
#   2. Compensação:     slot-proximo -> doador inapto (RN01, 422) -> vaga liberada -> CANCELADO
#   3. Recusa:          slot-lotado  -> 409 no passo 1 -> RECUSADO, sem compensação
#   4. Falha no passo 3: ms-comunicacao responde FALHOU (falha simulada) -> compensa 3, 2, 1 -> CANCELADO
#   5. Timeout no passo 3: ms-comunicacao parado -> sem resposta em 30 s -> CANCELADO; ao religar, o
#      programar pendente está expirado (sem confirmação ao doador) e o cancelar é idempotente
#   + Idempotency-Key repetida devolve a mesma SAGA; o ms-comunicacao real programa o lembrete, envia a
#     confirmação e o lembrete (antecedência longa no E2E, para disparar na hora) e registra o histórico.
#
# Uso: scripts/e2e-saga.sh            (MANTER=1 deixa a stack no ar ao final, para a demonstração)
set -euo pipefail
export LC_ALL=C

export GATEWAY_HOST_PORT="${GATEWAY_HOST_PORT:-18080}"
export KEYCLOAK_HOST_PORT="${KEYCLOAK_HOST_PORT:-18089}"
export RABBITMQ_AMQP_PORT="${RABBITMQ_AMQP_PORT:-15672}"
export RABBITMQ_MGMT_PORT="${RABBITMQ_MGMT_PORT:-25672}"
# slot-futuro fica a 90 dias: com 100 dias de antecedência o "D-1" já venceu e o lembrete dispara na hora.
export COMUNICACAO_LEMBRETE_ANTECEDENCIA="${COMUNICACAO_LEMBRETE_ANTECEDENCIA:-P100D}"
export COMUNICACAO_SIMULAR_FALHA_DOADORES=""
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

echo ">> subindo a stack (ms-agendamentos real; passo 2 simulado)"
"${COMPOSE[@]}" up -d --build --wait >/dev/null

GATEWAY="http://localhost:${GATEWAY_HOST_PORT}"
TOKEN=$(curl -s -X POST "$GATEWAY/realms/startech/protocol/openid-connect/token" \
  -d "client_id=mobile&grant_type=password&username=doador1&password=doador123" | json access_token)
[ -n "$TOKEN" ] || falha "token do doador vazio"
AUTH=(-H "Authorization: Bearer $TOKEN")

LINK_AGENDAR="/api/mobile/agendamentos"  # trocado pelo link `agendar` da grade no cenário 0

solicitar() {  # solicitar <slot> [idempotency-key] -> imprime "status corpo"
  local chave=${2:-$(python3 -c 'import uuid;print(uuid.uuid4())')}
  curl -s -w '\n%{http_code}' -X POST "$GATEWAY$LINK_AGENDAR" "${AUTH[@]}" \
    -H "Content-Type: application/json" -H "Idempotency-Key: $chave" -d "{\"slotId\":\"$1\"}"
}

aguardar() {  # aguardar <sagaId> [segundos] -> imprime o corpo final do GET (situação final)
  local corpo
  for _ in $(seq 1 $(( ${2:-30} * 2 ))); do
    corpo=$(curl -s "$GATEWAY/api/mobile/sagas/$1" "${AUTH[@]}")
    [ "$(echo "$corpo" | json finalizada)" = "True" ] && { echo "$corpo"; return; }
    sleep 0.5
  done
  falha "SAGA $1 não terminou em ${2:-30} s: $corpo"
}

DOADOR=$(python3 -c 'import base64,json,sys
p=sys.argv[1].split(".")[1]; p+="="*(-len(p)%4)
print(json.loads(base64.urlsafe_b64decode(p))["sub"])' "$TOKEN")

notificacoes() {  # notificacoes <agendamentoId> -> tipos registrados no histórico do doador, em ordem
  "${COMPOSE[@]}" exec -T ms-comunicacao python -c "
import json, urllib.request
d = json.load(urllib.request.urlopen('http://127.0.0.1:8004/api/v1/comunicacao/historico/$DOADOR?tamanho=100'))
print(' '.join(n['tipo'] for n in reversed(d['itens']) if n['agendamentoId'] == '$1'))"
}

esperar_notificacao() {  # esperar_notificacao <agendamentoId> <tipo>
  for _ in $(seq 1 40); do
    notificacoes "$1" | grep -qw "$2" && return
    sleep 0.5
  done
  falha "notificação $2 do agendamento $1 não registrada: $(notificacoes "$1")"
}

passos() {  # trilha de auditoria completa, direto no orquestrador (rede interna)
  "${COMPOSE[@]}" exec -T ms-orquestrador python -c "
import json, urllib.request
d = json.load(urllib.request.urlopen('http://127.0.0.1:8003/api/v1/sagas/$1'))
print('   status final:', d['status'])
for p in d['passos']:
    print(f\"   {p['passo']:5} {p['direcao']:10} {p['resultado']}\")"
}

sql_agendamentos() {  # sql_agendamentos '<consulta>' -> resultado sem cabeçalho, direto no banco do participante
  "${COMPOSE[@]}" exec -T db-agendamentos psql -U agendamentos -d agendamentos -tAc "$1"
}
vagas() { sql_agendamentos "SELECT vagas_ocupadas FROM slots WHERE id = '$1'"; }
status_agendamento() { sql_agendamentos "SELECT status FROM agendamentos WHERE id = '$1'"; }

estado_fake() { "${COMPOSE[@]}" exec -T participantes-fake python -c \
  "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:9000/fake/estado').read().decode())"; }

# ----------------------------------------------------------------------------------------------- 0
echo ">> 0. grade de horários pelo Gateway"
slots=$(curl -s "$GATEWAY/api/mobile/slots" "${AUTH[@]}")
echo "$slots" | python3 -c '
import json, sys
d = json.load(sys.stdin); ids = [s["slotId"] for s in d["itens"]]
assert "slot-futuro" in ids and "slot-proximo" in ids, ids
assert "slot-lotado" not in ids, ids
assert all(s["_links"]["agendar"] == {"href": "/api/mobile/agendamentos", "method": "POST", "title": s["_links"]["agendar"]["title"]} for s in d["itens"])
' || falha "grade inesperada: $slots"
echo "   ok: $(echo "$slots" | python3 -c 'import json,sys;print(", ".join(s["slotId"]+"("+str(s["vagasDisponiveis"])+")" for s in json.load(sys.stdin)["itens"]))')"
# como o app: escolhe o horário pela grade e segue o link `agendar` dele
slot_da_grade() {  # slot_da_grade <slotId> <campo> -> campo do slot na grade atual
  curl -s "$GATEWAY/api/mobile/slots" "${AUTH[@]}" | python3 -c '
import json, sys
s = next((s for s in json.load(sys.stdin)["itens"] if s["slotId"] == sys.argv[1]), None)
print("" if s is None else (s["_links"]["agendar"]["href"] if sys.argv[2] == "agendar" else s[sys.argv[2]]))' "$1" "$2"
}
LINK_AGENDAR=$(slot_da_grade slot-futuro agendar)
[ "$LINK_AGENDAR" = "/api/mobile/agendamentos" ] || falha "link agendar inesperado: $LINK_AGENDAR"
VAGAS_FUTURO=$(slot_da_grade slot-futuro vagasDisponiveis)

# ----------------------------------------------------------------------------------------------- 1
echo ">> 1. caminho feliz (slot-futuro: doador apto)"
CHAVE="e2e-$(date +%s)"
resp=$(solicitar slot-futuro "$CHAVE"); status=$(echo "$resp" | tail -1); corpo=$(echo "$resp" | head -1)
[ "$status" = "202" ] || falha "POST esperado 202, veio $status: $corpo"
SAGA1=$(echo "$corpo" | json sagaId); AG1=$(echo "$corpo" | json agendamentoId)
final=$(aguardar "$SAGA1")
[ "$(echo "$final" | json situacao)" = "CONFIRMADO" ] || falha "esperado CONFIRMADO: $final"
passos "$SAGA1"
[ "$(status_agendamento "$AG1")" = "CONFIRMADO" ] || falha "agendamento não confirmado no db-agendamentos"
[ "$(slot_da_grade slot-futuro vagasDisponiveis)" = "$(( VAGAS_FUTURO - 1 ))" ] \
  || falha "a grade não refletiu a vaga ocupada (antes $VAGAS_FUTURO)"
echo "   ok: CONFIRMADO; db-agendamentos: agendamento $AG1 CONFIRMADO, slot-futuro com $(vagas slot-futuro) vaga(s) ocupada(s)"
esperar_notificacao "$AG1" LEMBRETE
echo "   ok: ms-comunicacao registrou: $(notificacoes "$AG1")"

echo ">> idempotência: mesma Idempotency-Key devolve a mesma SAGA"
resp=$(solicitar slot-futuro "$CHAVE")
[ "$(echo "$resp" | head -1 | json sagaId)" = "$SAGA1" ] || falha "Idempotency-Key repetida criou outra SAGA"
echo "   ok: sagaId $SAGA1"

echo ">> 1b. consulta e cancelamento do agendamento confirmado (HATEOAS)"
LINK_AG=$(echo "$final" | json _links.agendamento.href)
[ "$LINK_AG" = "/api/mobile/agendamentos/$AG1" ] || falha "link agendamento inesperado: $LINK_AG"
ag=$(curl -s "$GATEWAY$LINK_AG" "${AUTH[@]}")
[ "$(echo "$ag" | json status)" = "CONFIRMADO" ] || falha "esperado CONFIRMADO: $ag"
LINK_CANCELAR=$(echo "$ag" | json _links.cancelar.href)
[ "$LINK_CANCELAR" = "/api/mobile/agendamentos/$AG1/cancelamento" ] || falha "sem link cancelar: $ag"
echo "$ag" | python3 -c 'import json,sys; sys.exit("novo-agendamento" in json.load(sys.stdin)["_links"])' \
  || falha "confirmado não deveria ter novo-agendamento: $ag"
echo "   ok: CONFIRMADO com links $(echo "$ag" | python3 -c 'import json,sys;print(sorted(json.load(sys.stdin)["_links"]))')"
lista=$(curl -s "$GATEWAY/api/mobile/agendamentos" "${AUTH[@]}")
echo "$lista" | python3 -c 'import json,sys; sys.exit(sys.argv[1] not in [i["id"] for i in json.load(sys.stdin)["itens"]])' "$AG1" \
  || falha "agendamento ausente da listagem do doador: $lista"
echo "   ok: listagem do doador traz $AG1"
antes=$(vagas slot-futuro)
resp=$(curl -s -w '\n%{http_code}' -X POST "$GATEWAY$LINK_CANCELAR" "${AUTH[@]}" \
  -H "Content-Type: application/json" -d '{"motivo":"Imprevisto pessoal"}')
status=$(echo "$resp" | tail -1); ag=$(echo "$resp" | head -1)
[ "$status" = "200" ] || falha "cancelamento esperado 200, veio $status: $ag"
[ "$(echo "$ag" | json status)" = "CANCELADO_DOADOR" ] || falha "esperado CANCELADO_DOADOR: $ag"
[ "$(echo "$ag" | json _links.novo-agendamento.href)" = "/api/mobile/agendamentos" ] || falha "sem novo-agendamento: $ag"
echo "$ag" | python3 -c 'import json,sys; sys.exit("cancelar" in json.load(sys.stdin)["_links"])' \
  || falha "cancelado não deveria ter link cancelar: $ag"
[ "$(vagas slot-futuro)" = "$(( antes - 1 ))" ] || falha "a vaga não foi liberada no db-agendamentos"
[ "$(status_agendamento "$AG1")" = "CANCELADO_DOADOR" ] || falha "db-agendamentos não registrou o cancelamento"
ag=$(curl -s "$GATEWAY$LINK_AG" "${AUTH[@]}")
[ "$(echo "$ag" | json status)" = "CANCELADO_DOADOR" ] || falha "consulta após cancelar: $ag"
echo "   ok: CANCELADO_DOADOR, vaga liberada, links $(echo "$ag" | python3 -c 'import json,sys;print(sorted(json.load(sys.stdin)["_links"]))')"
status=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$GATEWAY$LINK_CANCELAR" "${AUTH[@]}")
[ "$status" = "409" ] || falha "cancelar de novo esperado 409, veio $status"
echo "   ok: cancelar de novo -> 409"
[ "$(slot_da_grade slot-futuro vagasDisponiveis)" = "$VAGAS_FUTURO" ] || falha "a vaga cancelada não voltou à grade"
echo "   ok: a vaga voltou à grade (slot-futuro com $VAGAS_FUTURO disponíveis)"

# ----------------------------------------------------------------------------------------------- 2
echo ">> 2. compensação (slot-proximo: doou há 10 dias, RN01 exige 60)"
antes=$(vagas slot-proximo)
resp=$(solicitar slot-proximo); status=$(echo "$resp" | tail -1); corpo=$(echo "$resp" | head -1)
[ "$status" = "202" ] || falha "POST esperado 202, veio $status: $corpo"
SAGA2=$(echo "$corpo" | json sagaId); AG2=$(echo "$corpo" | json agendamentoId)
final=$(aguardar "$SAGA2")
[ "$(echo "$final" | json situacao)" = "CANCELADO" ] || falha "esperado CANCELADO: $final"
echo "   motivo exibido no app: $(echo "$final" | json motivo)"
passos "$SAGA2"
[ "$(status_agendamento "$AG2")" = "CANCELADO_COMPENSACAO_SAGA" ] || falha "agendamento não compensado no db-agendamentos"
[ "$(vagas slot-proximo)" = "$antes" ] || falha "a vaga não foi liberada no db-agendamentos"
estado_fake | python3 -c 'import json,sys; sys.exit(sys.argv[1] in json.load(sys.stdin)["travas"])' "$AG2" \
  || falha "a trava de elegibilidade não deveria existir"
echo "   ok: CANCELADO; db-agendamentos: vaga devolvida (ocupadas=$antes) e agendamento CANCELADO_COMPENSACAO_SAGA"

# ----------------------------------------------------------------------------------------------- 3
echo ">> 3. recusa sem compensação (slot-lotado: 409 no passo 1)"
SAGA3=$(solicitar slot-lotado | head -1 | json sagaId)
final=$(aguardar "$SAGA3")
[ "$(echo "$final" | json situacao)" = "RECUSADO" ] || falha "esperado RECUSADO: $final"
passos "$SAGA3"
[ -z "$(status_agendamento "$(echo "$final" | json agendamentoId)")" ] || falha "slot lotado não deveria criar agendamento"
echo "   ok: RECUSADO; nenhum agendamento criado no db-agendamentos"

# ----------------------------------------------------------------------------------------------- 4
echo ">> 4. falha no passo 3 (ms-comunicacao responde FALHOU para este doador)"
COMUNICACAO_SIMULAR_FALHA_DOADORES="$DOADOR" "${COMPOSE[@]}" up -d --wait ms-comunicacao >/dev/null
SAGA4=$(solicitar slot-futuro | head -1 | json sagaId)
final=$(aguardar "$SAGA4")
[ "$(echo "$final" | json situacao)" = "CANCELADO" ] || falha "esperado CANCELADO: $final"
echo "   motivo exibido no app: $(echo "$final" | json motivo)"
passos "$SAGA4"
AG4=$(echo "$final" | json agendamentoId)
[ "$(status_agendamento "$AG4")" = "CANCELADO_COMPENSACAO_SAGA" ] || falha "agendamento não compensado no db-agendamentos"
estado_fake | python3 -c 'import json,sys; sys.exit(sys.argv[1] in json.load(sys.stdin)["travas"])' "$AG4" \
  || falha "a trava de elegibilidade não foi removida (compensação do passo 2)"
echo "   ok: CANCELADO pela resposta FALHOU, sem esperar o timeout"
"${COMPOSE[@]}" up -d --wait ms-comunicacao >/dev/null  # volta sem a falha simulada

# ----------------------------------------------------------------------------------------------- 5
echo ">> 5. timeout no passo 3 (ms-comunicacao parado)"
"${COMPOSE[@]}" stop ms-comunicacao >/dev/null
SAGA5=$(solicitar slot-futuro | head -1 | json sagaId)
final=$(aguardar "$SAGA5" 60)
[ "$(echo "$final" | json situacao)" = "CANCELADO" ] || falha "esperado CANCELADO: $final"
passos "$SAGA5"
AG5=$(echo "$final" | json agendamentoId)
[ "$(status_agendamento "$AG5")" = "CANCELADO_COMPENSACAO_SAGA" ] || falha "agendamento não compensado no db-agendamentos"
echo "   religando o ms-comunicacao: o programar pendente está expirado e o cancelar não tem o que desfazer"
"${COMPOSE[@]}" up -d --wait ms-comunicacao >/dev/null
esperar_notificacao "$AG5" DESFECHO
sleep 2  # dá tempo de os comandos pendentes serem consumidos
hist=$(notificacoes "$AG5")
echo "$hist" | grep -qw CONFIRMACAO && falha "doador recebeu confirmação de um agendamento já compensado: $hist"
echo "   ok: CANCELADO por timeout; o doador só recebeu o desfecho ($hist)"

# ----------------------------------------------------------------------------------------------- filas
echo ">> filas drenadas (comandos consumidos pelo ms-comunicacao, respostas pelo orquestrador)"
for _ in $(seq 1 20); do
  filas=$("${COMPOSE[@]}" exec -T rabbitmq rabbitmqctl -q list_queues name messages)
  pendentes=$(echo "$filas" | awk '$1=="comunicacao.saga.comandos"||$1=="orquestrador.saga.respostas"{s+=$2} END{print s+0}')
  [ "$pendentes" = "0" ] && break
  sleep 0.5
done
echo "$filas" | grep -E "comunicacao\.|saga.compensations.dlq|orquestrador.saga.respostas" | sed 's/^/   /'
[ "$pendentes" = "0" ] || falha "ainda há $pendentes mensagens pendentes nas filas da SAGA"
[ -z "$(sql_agendamentos "SELECT id FROM agendamentos WHERE doador_id = '$DOADOR' AND status IN ('CRIADO_PROVISORIO', 'CONFIRMADO')")" ] \
  || falha "sobrou agendamento ativo do doador no db-agendamentos"
echo ">> E2E da SAGA OK"
