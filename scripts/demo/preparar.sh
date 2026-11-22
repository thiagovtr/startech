#!/usr/bin/env bash
# Deixa a stack no estado inicial da demonstração. Pode ser rodado de novo entre ensaios.
#   1. sobe tudo (com o perfil `ia`); 2. zera agendamentos e recria a grade de horários do ms-agendamentos;
#   3. zera as travas do passo 2 (ms-doadores); 4. cria uma campanha de exemplo pelo BFF Web.
# Uso: scripts/demo/preparar.sh            (SEM_IA=1 não espera o Ollama baixar os modelos)
source "$(dirname "$0")/comum.sh"

titulo "subindo a stack"
"${COMPOSE[@]}" up -d --build
for _ in $(seq 1 120); do
  [ -n "$(token_doador 2>/dev/null)" ] && break
  sleep 2
done
[ -n "$(token_doador)" ] || falha "Keycloak/Gateway não responderam em 4 min"
echo "   ok: Gateway em $GATEWAY e Keycloak respondendo"

titulo "zerando agendamentos e recriando a grade de horários"
sql_valor db-agendamentos agendamentos agendamentos "DELETE FROM agendamentos; DELETE FROM slots;" >/dev/null
sql_valor db-doadores doadores doadores "DELETE FROM travas_elegibilidade;" >/dev/null
# as duas subidas recriam o estado relativo à data de hoje: a grade e a última doação do doador1
"${COMPOSE[@]}" restart ms-agendamentos ms-doadores >/dev/null
for _ in $(seq 1 60); do
  n=$(curl -s "$GATEWAY/api/mobile/slots" -H "Authorization: Bearer $(token_doador)" \
      | python3 -c 'import json,sys
try: print(len(json.load(sys.stdin)["itens"]))
except Exception: print(0)')
  [ "$n" -gt 0 ] && break
  sleep 2
done
[ "$n" -gt 0 ] || falha "a grade de horários não voltou"
sql db-agendamentos agendamentos agendamentos \
  "SELECT id, posto_id, data_hora_inicio, capacidade, vagas_ocupadas FROM slots ORDER BY data_hora_inicio"

titulo "campanha de exemplo (CQRS)"
hoje=$(date +%F); fim=$(date -d '+30 days' +%F)
curl -s -X POST "$GATEWAY/api/web/campanhas" -H "Authorization: Bearer $(token_operador)" \
  -H "Content-Type: application/json" \
  -d "{\"titulo\":\"Estoque crítico de O-\",\"hemocentro\":\"Hemominas Lavras\",\"tipo_sanguineo\":\"O-\",\"urgencia\":\"CRITICO\",\"data_inicio\":\"$hoje\",\"data_fim\":\"$fim\"}" \
  | json id | sed 's/^/   campanha criada: /'

if [ "${SEM_IA:-0}" != "1" ]; then
  titulo "aguardando o ms-rag (modelos do Ollama; na 1ª vez baixa ~1,3 GB)"
  for _ in $(seq 1 300); do
    "${COMPOSE[@]}" exec -T ms-rag python -c \
      "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8005/ready',timeout=3)" >/dev/null 2>&1 && break
    sleep 2
  done
  "${COMPOSE[@]}" exec -T ms-rag python -c \
    "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8005/ready',timeout=3)" >/dev/null 2>&1 \
    && echo "   ok: ms-rag pronto" || echo "   aviso: ms-rag ainda não está pronto (o assistente responde com fallback)"
  titulo "aquecendo o modelo (a 1ª resposta em CPU passa do timeout de 4 s)"
  aquecer_llm 15 && echo "   ok: modelo carregado" || echo "   aviso: o modelo não respondeu com RAG; rode scripts/demo/religar-llm.sh"
fi

titulo "pronto para a demonstração (roteiro: docs/demonstracao.md)"
