#!/usr/bin/env bash
# BFF Mobile x BFF Web (4.4): a mesma campanha servida a cada cliente, lado a lado.
# O app recebe a home agregada (perfil + campanhas do tipo sanguíneo do doador, com degradação); o painel
# recebe a lista de campanhas do hemocentro para gestão.
source "$(dirname "$0")/comum.sh"

mobile=$(curl -s "$GATEWAY/api/mobile/home" -H "Authorization: Bearer $(token_doador)")
web=$(curl -s "$GATEWAY/api/web/campanhas" -H "Authorization: Bearer $(token_operador)")

titulo "BFF Mobile: GET /api/mobile/home (doador1)"
echo "$mobile" | bonito
titulo "BFF Web: GET /api/web/campanhas (operador1), primeiros 2 itens"
echo "$web" | python3 -c 'import json,sys;print(json.dumps(json.load(sys.stdin)[:2],ensure_ascii=False,indent=2))'

titulo "diferença"
python3 - "$mobile" "$web" <<'PY'
import json, sys
m, w = json.loads(sys.argv[1]), json.loads(sys.argv[2])
print("   BFF Mobile, chaves de topo:", ", ".join(m))
print("   BFF Web, formato: lista de", len(w), "campanhas")
cm = (m.get("campanhas") or [{}])[0]
cw = (w or [{}])[0]
print("   campos de uma campanha no mobile:", ", ".join(cm))
print("   campos de uma campanha no web:   ", ", ".join(cw))
so_web = sorted(set(cw) - set(cm)); so_mobile = sorted(set(cm) - set(cw))
print("   só no web:   ", ", ".join(so_web) or "-")
print("   só no mobile:", ", ".join(so_mobile) or "-")
PY
