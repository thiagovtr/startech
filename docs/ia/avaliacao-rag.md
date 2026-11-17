# Avaliação do assistente RAG — StarTech

Gerado por `scripts/avaliar-rag.py` em 2026-11-17. Cada pergunta foi feita 5 vezes em cada modo, com o modelo já carregado. Modelo de chat `qwen2.5:1.5b` e embeddings `nomic-embed-text`, via Ollama em CPU, com `temperature=0`, timeout de 4 s e circuit breaker.

**Critério de acerto:** a resposta contém os valores exatos da Portaria de Consolidação MS nº 5/2017, Anexo IV (por exemplo, `50 kg`, `60 dias` e `90 dias`). Para a pergunta 5, o acerto é citar o hemocentro de uma campanha real, criada no `ms-hemocentros` antes da medição.

## Resultados por pergunta

| Pergunta | RAG | Modo | Acertos | Latência média (ms) | p95 (ms) | Fallbacks |
| --- | --- | --- | --- | --- | --- | --- |
| Qual o peso mínimo para doar sangue? | sem | SEM_RAG | 0/5 | 708 | 746 | 0 |
| Qual o peso mínimo para doar sangue? | com | RAG | 5/5 | 653 | 1543 | 0 |
| Qual o intervalo mínimo entre doações para homens e para mulheres? | sem | SEM_RAG | 0/5 | 405 | 564 | 0 |
| Qual o intervalo mínimo entre doações para homens e para mulheres? | com | RAG | 5/5 | 1026 | 1882 | 0 |
| Fiz uma tatuagem recentemente. Quanto tempo preciso esperar para doar sangue? | sem | SEM_RAG | 0/5 | 577 | 697 | 0 |
| Fiz uma tatuagem recentemente. Quanto tempo preciso esperar para doar sangue? | com | RAG | 5/5 | 541 | 1656 | 0 |
| Estou gripado. Quanto tempo depois posso doar sangue? | sem | SEM_RAG | 0/5 | 439 | 599 | 0 |
| Estou gripado. Quanto tempo depois posso doar sangue? | com | RAG | 5/5 | 980 | 1954 | 0 |
| Onde posso doar hoje? | sem | SEM_RAG | 0/5 | 1642 | 1828 | 0 |
| Onde posso doar hoje? | com | FERRAMENTA | 5/5 | 2 | 5 | 0 |

## Respostas (primeira repetição)

- **Sem RAG — Qual o peso mínimo para doar sangue?** (esperado: 50 kg)  
  > O peso mínimo para doar sangue varia dependendo da localização e pode ser entre 50 a 100 gramas.
- **Com RAG — Qual o peso mínimo para doar sangue?** (esperado: 50 kg)  
  > O peso mínimo para doar sangue é de 50 kg. [Peso mínimo]
- **Sem RAG — Qual o intervalo mínimo entre doações para homens e para mulheres?** (esperado: 60 dias, 90 dias)  
  > O intervalo mínimo entre duas doações é de 30 dias para ambos os sexos.
- **Com RAG — Qual o intervalo mínimo entre doações para homens e para mulheres?** (esperado: 60 dias, 90 dias)  
  > Para homens: mínimo de 60 dias entre duas doações. Para mulheres: mínimo de 90 dias entre duas doagens. [Intervalo entre doações e frequência anual]
- **Sem RAG — Fiz uma tatuagem recentemente. Quanto tempo preciso esperar para doar sangue?** (esperado: 12 meses)  
  > Deve esperar pelo menos seis meses após a tatuagem antes de fazer o procedimento de doação de sangue.
- **Com RAG — Fiz uma tatuagem recentemente. Quanto tempo preciso esperar para doar sangue?** (esperado: 12 meses)  
  > 12 meses [Título: Tatuagem]
- **Sem RAG — Estou gripado. Quanto tempo depois posso doar sangue?** (esperado: 7 dias)  
  > Deve esperar pelo menos duas semanas após ter feito exames para diagnóstico da gripe.
- **Com RAG — Estou gripado. Quanto tempo depois posso doar sangue?** (esperado: 7 dias)  
  > Deverá esperar 7 dias após o desaparecimento dos sintomas da gripe para doar sangue. [Gripe, resfriado e febre]
- **Sem RAG — Onde posso doar hoje?** (esperado: Hemocentro Regional de Lavras)  
  > Peço desculpas pela confusão, mas como assistente de doação de sangue, não tenho acesso a informações atualizadas sobre locais próximos para doações de sangue. Sugiro que você consulte o site da Fundação Hemominas (hemominas.org.br) ou entre em contato com os centros de doação mais próximos por meio dos telefones disponíveis no site.
- **Com RAG — Onde posso doar hoje?** (esperado: Hemocentro Regional de Lavras)  
  > Campanhas ativas para o tipo O-: - Estoque crítico O- (avaliação RAG) — Hemocentro Regional de Lavras (tipo O-, urgência CRITICO, até 2026-12-17)

## Latência e tokens

| Modo | Média (ms) | Mediana (ms) | p95 (ms) | Tokens de entrada (média) | Tokens de saída (média) |
| --- | --- | --- | --- | --- | --- |
| Sem RAG | 754 | 564 | 1662 | 57 | 40 |
| Com RAG | 641 | 472 | 1882 | 372 | 29 |

## Projeção de custo

- **Local (Ollama em CPU):** cerca de 5620 perguntas/h por instância, atendendo em série com média de 0.64 s. Com uma máquina de US$ 0.20/h, o custo é de ~US$ 0.036 por 1.000 perguntas, se a instância estiver ocupada o tempo todo. O custo é fixo por hora: escalar exige mais réplicas do Ollama, cada uma com ~2 GB de RAM.
- **API paga (comparação):** com 372 tokens de entrada e 29 de saída por pergunta, a US$ 1.00 e US$ 5.00 por milhão de tokens, o custo seria de ~US$ 0.515 por 1.000 perguntas. O custo é variável e cresce linearmente com o uso, sem servidor dedicado.
- Os preços são **parâmetros da projeção**, não cotações. Ajuste `PRECO_HORA_SERVIDOR`, `PRECO_API_ENTRADA` e `PRECO_API_SAIDA` com valores atuais antes de apresentar.

## Resiliência: Ollama derrubado durante o uso

Medido com `docker compose stop ollama` e o `ms-rag` no ar (circuit breaker: 3 falhas abrem o circuito por 30 s).

| # | Pergunta | Modo | Motivo | Latência (ms) | Circuito da busca depois |
| --- | --- | --- | --- | --- | --- |
| 1 | Qual o peso mínimo para doar? | FALLBACK | busca: ConnectionError | 30 | FECHADO |
| 2 | Estou gripado, quando posso doar? | FALLBACK | busca: ConnectionError | 21 | FECHADO |
| 3 | Qual o intervalo entre doações? | FALLBACK | busca: ConnectionError | 22 | ABERTO |
| 4 | Tatuagem: quanto tempo esperar para doar? | FALLBACK | busca: circuito aberto | 1 | ABERTO |
| 5 | Fiz endoscopia, quando posso doar? | FALLBACK | busca: circuito aberto | 1 | ABERTO |
| 6 | Onde posso doar hoje? | FERRAMENTA | — | 5 | ABERTO |

- Nenhuma resposta 5xx. As três primeiras falhas respondem o fallback em ~20–30 ms (conexão recusada). Com o Ollama travado em vez de parado, o limite é o timeout: 1,5 s na busca e 4 s na geração.
- Com o circuito aberto, o fallback sai em ~1 ms, sem tentar o Ollama. A ferramenta de campanhas continua funcionando, porque não depende do LLM.
- Depois de `docker compose start ollama` e dos 30 s do circuito aberto, a chamada de teste (meio-aberto) teve sucesso, o circuito fechou e a pergunta seguinte foi respondida com RAG em 2,5 s (o modelo foi recarregado após o reinício).

## Decisões e limitações observadas

- **Modelo:** `qwen2.5:1.5b`. O `qwen2.5:3b` acertou mais perguntas situacionais, mas a frio levou de 2,3 a 5,6 s em CPU, o que estoura o limite de 4 s.
- **Threads:** `RAG_NUM_THREAD=8`. Em CPUs híbridas (núcleos de desempenho e de eficiência), o padrão do Ollama (todos os núcleos) gerou ~10 tokens/s; com 8 threads, ~58 tokens/s (Core Ultra 9 285K). Sem esse ajuste, quase todas as respostas caíam no timeout.
- **Escopo da resposta:** o prompt pede a regra exata da Portaria e não decide se a pessoa está apta. Isso segue o escopo do projeto (a aptidão é da triagem clínica). Além disso, o modelo de 1,5B erra esse tipo de raciocínio: diante de "tatuagem há 3 meses", às vezes respondeu "pode doar".
- **Recusa fora do domínio:** é feita antes do LLM, por um filtro de termos de doação de sangue. Instruído a recusar, o modelo respondeu "Paris" para "Qual a capital da França?". Com a frase de recusa no prompt, passou a recusar também perguntas cobertas pela base.
- **Base de conhecimento:** 12 trechos curados do Anexo IV, indexados em memória na subida do serviço (~1 s com o Ollama aquecido). Os trechos resumem o texto oficial e devem ser conferidos com a publicação no DOU antes do uso real.
