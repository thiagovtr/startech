#!/usr/bin/env bash
# Estado de uma SAGA em cada participante: trilha do orquestrador (db-orquestrador), vaga e agendamento
# (db-agendamentos), trava de elegibilidade (passo 2) e notificações/lembrete (db-comunicacao).
# Uso: scripts/demo/evidencia-saga.sh <sagaId>
source "$(dirname "$0")/comum.sh"
[ $# -eq 1 ] || falha "uso: $0 <sagaId>"

s=$(saga "$1")
AG=$(echo "$s" | json agendamentoId); SLOT=$(echo "$s" | json slotId)

titulo "ms-orquestrador: SAGA $1 ($(echo "$s" | json status))"
echo "$s" | python3 -c '
import json, sys
d = json.load(sys.stdin)
for p in d["passos"]:
    print("   %-5s %-11s %s" % (p["passo"], p["direcao"], p["resultado"]))
if d.get("recusa"):
    print("   motivo:", d["recusa"].get("detail") or d["recusa"].get("title"))'
sql db-orquestrador orquestrador orquestrador \
  "SELECT step, acao, resultado, criado_em FROM saga_step_log WHERE saga_id = '$1' ORDER BY id"
sql db-orquestrador orquestrador orquestrador \
  "SELECT routing_key, published, created_at FROM outbox_events WHERE aggregate_id = '$1' ORDER BY created_at"

titulo "ms-agendamentos (db-agendamentos): agendamento $AG e slot $SLOT"
sql db-agendamentos agendamentos agendamentos \
  "SELECT id, status, data_cancelamento, motivo_cancelamento FROM agendamentos WHERE id = '$AG'"
sql db-agendamentos agendamentos agendamentos \
  "SELECT id, capacidade, vagas_ocupadas FROM slots WHERE id = '$SLOT'"

titulo "passo 2 (ms-doadores, simulado): trava de elegibilidade"
"${COMPOSE[@]}" exec -T participantes-fake python -c "
import json, urllib.request
d = json.load(urllib.request.urlopen('http://127.0.0.1:9000/fake/estado'))
t = d['travas'].get('$AG')
print('   trava:', t if t else 'nenhuma (não criada ou removida pela compensação)')"

titulo "ms-comunicacao (db-comunicacao): lembrete e notificações"
sql db-comunicacao comunicacao comunicacao \
  "SELECT status, data_hora_inicio, programado_para, enviado_em FROM lembretes WHERE agendamento_id = '$AG'"
DOADOR=$(echo "$s" | json doadorId)
"${COMPOSE[@]}" exec -T ms-comunicacao python -c "
import json, urllib.request
d = json.load(urllib.request.urlopen('http://127.0.0.1:8004/api/v1/comunicacao/historico/$DOADOR?tamanho=100'))
tipos = [n['tipo'] for n in reversed(d['itens']) if n['agendamentoId'] == '$AG']
print('   notificações:', ' '.join(tipos) or 'nenhuma')"
