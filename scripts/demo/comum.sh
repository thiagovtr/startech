# Funções comuns dos scripts de demonstração (carregado com `source`). Não execute direto.
# Variáveis: GATEWAY_HOST_PORT (padrão 8080), KEYCLOAK_HOST_PORT (padrão 8089).
set -euo pipefail
export LC_ALL=C.UTF-8

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$RAIZ"
COMPOSE=(docker compose --profile ia)
GATEWAY="http://localhost:${GATEWAY_HOST_PORT:-8080}"

json() {  # json '<campo.subcampo>' < corpo
  python3 -c 'import json,sys
v=json.load(sys.stdin)
for k in sys.argv[1].split("."):
    v=v[k] if isinstance(v,dict) else v[int(k)]
print(v if not isinstance(v,(dict,list)) else json.dumps(v,ensure_ascii=False))' "$1"
}

bonito() { python3 -c 'import json,sys;print(json.dumps(json.load(sys.stdin),ensure_ascii=False,indent=2))'; }

falha() { echo "FALHA: $*" >&2; exit 1; }

titulo() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

token() {  # token <client> <usuario> <senha>
  curl -s -X POST "$GATEWAY/realms/startech/protocol/openid-connect/token" \
    -d "client_id=$1&grant_type=password&username=$2&password=$3" | json access_token
}
token_doador() { token mobile doador1@startech.local doador123; }
token_operador() { token startech-web operador1@startech.local operador123; }

sql() {  # sql <servico-banco> <usuario> <banco> '<consulta>'
  "${COMPOSE[@]}" exec -T "$1" psql -U "$2" -d "$3" -P pager=off -c "$4"
}
sql_valor() {  # igual a sql, mas só o valor (sem cabeçalho)
  "${COMPOSE[@]}" exec -T "$1" psql -U "$2" -d "$3" -tAc "$4"
}

saga() {  # saga <sagaId> -> JSON completo, direto no orquestrador (rede interna)
  "${COMPOSE[@]}" exec -T ms-orquestrador python -c "
import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8003/api/v1/sagas/$1').read().decode())"
}

aquecer_llm() {  # carrega os modelos direto no Ollama (sem passar pelo circuit breaker) e confirma uma resposta RAG
  local chat="${OLLAMA_MODELO_CHAT:-qwen2.5:3b}" emb="${OLLAMA_MODELO_EMBEDDINGS:-nomic-embed-text}" modo=""
  "${COMPOSE[@]}" exec -T ms-rag python -c "
import json, urllib.request
for path, payload in [
    ('/api/generate', {'model': '$chat', 'prompt': 'ok', 'stream': False}),
    ('/api/embed', {'model': '$emb', 'input': 'aquecer'}),
]:
    r = urllib.request.Request('http://ollama:11434' + path, json.dumps(payload).encode())
    urllib.request.urlopen(r, timeout=120).read()" >/dev/null 2>&1 || true
  echo "   modelos carregados no Ollama; aguardando o circuito do ms-rag fechar (até 30 s)"
  for i in $(seq 1 "${1:-10}"); do
    modo=$(curl -s -X POST "$GATEWAY/api/mobile/assistente" -H "Authorization: Bearer $(token_doador)" \
      -H "Content-Type: application/json" -d '{"pergunta":"Quem fez tatuagem pode doar sangue?"}' | json modo)
    echo "   tentativa $i: $modo"
    [ "$modo" = "RAG" ] && return 0
    sleep 6
  done
  return 1
}
