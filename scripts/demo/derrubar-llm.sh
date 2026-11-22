#!/usr/bin/env bash
# LLM como dependência falível: para o Ollama e faz perguntas seguidas. Com o Ollama parado a conexão é recusada na
# hora (sem esperar o timeout de 4 s), o circuit breaker abre depois de 3 falhas e as seguintes saem pelo fallback
# sem nem tentar o Ollama (motivo "circuito aberto"). Religue com religar-llm.sh.
source "$(dirname "$0")/comum.sh"
titulo "docker compose stop ollama"
"${COMPOSE[@]}" stop ollama >/dev/null
for i in 1 2 3 4 5; do
  "$(dirname "$0")/assistente.sh" "Quanto tempo depois de fazer tatuagem posso doar? ($i)" | grep "modo:"
done
