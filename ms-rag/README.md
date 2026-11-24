# ms-rag

Assistente do doador com **RAG** sobre a Portaria de Consolidação MS nº 5/2017, Anexo IV (Python 3.12 / FastAPI, **LangChain** e **Ollama** local, porta 8005). Responde dúvidas sobre critérios de doação citando a Portaria e responde "Onde posso doar hoje?" com as campanhas ativas do `ms-hemocentros`. Usa limites de tempo por etapa, circuit breaker e fallback. Avaliação com e sem RAG: [`docs/ia/avaliacao-rag.md`](../docs/ia/avaliacao-rag.md).

## Fluxo de uma pergunta

| Situação | Caminho | `modo` |
| --- | --- | --- |
| "Onde posso doar hoje?", "campanhas ativas"… (regra de intenção) | LangChain `Tool` `campanhas_vigentes` → `GET ms-hemocentros/api/v1/campanhas?status=ATIVA&vigentes=true&tipo_sanguineo=…` (leitura CQRS), resposta montada sem LLM | `FERRAMENTA` |
| Saudação ou dúvida reconhecida sobre o aplicativo | Resposta local, sem chamada ao modelo | `RAG` |
| Pergunta fora do domínio e dos casos anteriores | recusa padrão, sem LLM | `FORA_DO_ESCOPO` |
| Pergunta sobre critérios de doação | busca dos 2 trechos mais próximos (embeddings `nomic-embed-text`, `InMemoryVectorStore`) → chain LCEL `PROMPT_RAG | ChatOllama` (prompt restrito ao contexto, `qwen2.5:1.5b`, `temperature=0`) | `RAG` |
| `usarRag: false` (só para a avaliação) | pergunta direto ao LLM, sem contexto | `SEM_RAG` |
| Ollama ou `ms-hemocentros` lento, fora ou com o circuito aberto | mensagem amigável; com RAG, inclui o trecho recuperado se a busca funcionou | `FALLBACK` |

- **Prompt:** usa só as regras do contexto, informa a regra exata (prazo, idade, peso) e **não decide aptidão**, porque isso é da triagem clínica e está fora do escopo do projeto. A resposta termina com a seção usada e um aviso fixo de que não substitui a triagem.
- **Resiliência:**
  - timeouts de 3 s na busca e 10 s na geração;
  - três circuitos (busca, LLM e campanhas): 3 falhas seguidas abrem o circuito por 30 s, e depois uma chamada de teste decide se ele fecha;
  - nunca devolve 5xx por causa do LLM.
- **Aquecimento:** o modelo é carregado na subida (a frio, a primeira geração leva ~10 s) e mantido por `keep_alive=30m`.
- **Índice:** os 12 trechos de `src/rag/data/*.md` (um por seção `##`) são indexados em memória na subida, com retentativas enquanto o Ollama não responde. Sem banco vetorial e sem volume.

## Endpoints

| Rota | Descrição |
| --- | --- |
| `POST /api/v1/rag/perguntas` | `{pergunta, usarRag?=true, tipoSanguineo?}` → `{resposta, modo, fontes[{secao, fonte, trecho}], latenciaMs, uso{tokensEntrada, tokensSaida}, motivoFallback}`. Payload inválido → `400 problem+json`. |
| `GET /health`, `GET /ready` | Sempre 200 (o serviço degrada em vez de cair): `status`, `indice` (`pronto`/`pendente`) e estado dos circuitos. |

O app chega aqui pelo `bff-mobile` (`POST /bff-mobile/assistente` {pergunta}, via Gateway em `/api/mobile/assistente`). O BFF injeta o tipo sanguíneo do perfil do doador e, se o `ms-rag` cair, devolve o fallback com 200.

## Configuração (`RAG_*`)

| Variável | Padrão | Observação |
| --- | --- | --- |
| `OLLAMA_URL`, `MODELO_CHAT`, `MODELO_EMBEDDINGS` | `http://ollama:11434`, `qwen2.5:1.5b`, `nomic-embed-text` | Modelos baixados pelo serviço `ollama-pull` do Compose. |
| `NUM_THREAD` | `8` | **Ajuste para o nº de núcleos de desempenho da CPU.** Em CPUs híbridas, o padrão do Ollama (todos os núcleos) foi ~6x mais lento. `0` deixa o Ollama decidir. |
| `TIMEOUT_LLM`, `TIMEOUT_BUSCA` | `10`, `3` | O BFF espera até 14 s pelo RAG e o Gateway espera até 15 s pela resposta. |
| `CB_FALHAS`, `CB_ABERTO_SEGUNDOS` | `3`, `30` | Circuit breaker. |
| `TOP_K`, `NUM_PREDICT` | `2`, `200` | Trechos no contexto e limite de tokens da resposta. |
| `HEMOCENTROS_URL`, `MAX_CAMPANHAS` | `http://ms-hemocentros:8000`, `5` | Ferramenta de campanhas. |
| `AQUECER_MODELO` | `true` | Carrega o modelo na subida. |

## Executar, testar e avaliar

Na raiz do repositório, inicie a stack com o perfil de IA e consulte a prontidão do índice:

```sh
docker compose --profile ia up -d --build
docker compose --profile ia exec -T ms-rag python -c "import json, urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8005/ready')))"
```

Quando o índice estiver `pronto` e o status for `ok`, execute a avaliação no ambiente de testes:

```sh
docker compose --profile ia exec -T ms-rag python - < scripts/avaliar-rag.py
```

O script cria uma campanha de teste, compara cinco perguntas com e sem RAG e imprime o relatório no terminal. Latência e quantidade de fallbacks podem variar com a CPU, o aquecimento do modelo e os limites configurados.

Para executar lint, checagem de tipos e testes isolados, use `scripts/test-docker.sh ms-rag`. A suíte simula o LLM, os embeddings e o serviço de hemocentros.

Os testes cobrem a recuperação da seção certa, o circuit breaker (abre, falha rápido, meio-aberto, fecha), o timeout com fallback contendo o trecho, a recusa fora do domínio, a ferramenta (filtros e vigência) e a API sem Ollama.
