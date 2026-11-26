#!/usr/bin/env bash
# Assistente do doador (RAG + LangChain): pergunta pelo BFF Mobile e mostra modo, fontes e latência.
# Uso: scripts/demo/assistente.sh "<pergunta>"
source "$(dirname "$0")/comum.sh"
[ $# -eq 1 ] || falha "uso: $0 \"<pergunta>\""
pergunta=$(python3 -c 'import json,sys;print(json.dumps({"pergunta":sys.argv[1]},ensure_ascii=False))' "$1")
titulo "POST /api/mobile/assistente: $1"
curl -s -w '\n%{time_total}\n' -X POST "$GATEWAY/api/mobile/assistente" -H "Authorization: Bearer $(token_doador)" \
  -H "Content-Type: application/json" -d "$pergunta" | python3 -c '
import json, sys
corpo, tempo = sys.stdin.read().strip().rsplit("\n", 1)
d = json.loads(corpo)
m = d.get("motivo")
motivo = f" | motivo: {m}" if m else ""
print("   modo:", d.get("modo"), "| degradado:", d.get("degradado"), "| tempo:", round(float(tempo) * 1000), "ms" + motivo)
print("   resposta:", d.get("resposta"))
for f in d.get("fontes") or []: print("   fonte:", f.get("fonte"), "/", f.get("secao"))'
