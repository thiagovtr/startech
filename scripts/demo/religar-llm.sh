#!/usr/bin/env bash
# Religa o Ollama. O circuito fica aberto por 30 s; depois a chamada de teste (meio-aberto) fecha o circuito.
source "$(dirname "$0")/comum.sh"
titulo "docker compose start ollama"
"${COMPOSE[@]}" start ollama >/dev/null
echo "   o modelo é recarregado do zero; o circuito do ms-rag fecha na primeira chamada bem-sucedida depois de 30 s"
aquecer_llm 10 || falha "o modelo não voltou a responder com RAG"
"$(dirname "$0")/assistente.sh" "Quanto tempo depois de fazer tatuagem posso doar?"
