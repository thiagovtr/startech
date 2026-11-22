# Roteiro da demonstração (Parte 4)

Cada critério da seção 6 do enunciado tem um passo reproduzível, com o comando e o resultado esperado. Os
comandos rodam na raiz do repositório. Os scripts de `scripts/demo/` passam pelo Gateway, como os clientes, e
leem o estado direto nos bancos de cada serviço para servir de evidência.

Todos os participantes da SAGA são os reais: `ms-agendamentos` (passos 1 e 4), `ms-doadores` (passo 2, RN01),
`ms-comunicacao` (passo 3, via Outbox e RabbitMQ) e o `ms-orquestrador`.

## 0. Preparação (antes da apresentação)

```bash
cp .env.example .env           # só na primeira vez
scripts/demo/preparar.sh       # sobe tudo, recria a grade de horários, cria uma campanha e aquece o LLM
```

O script pode ser rodado de novo entre ensaios: ele zera os agendamentos e as travas do passo 2 e recria a
grade de horários. Com o perfil `demo`, o `ms-agendamentos` cria a grade e o `ms-doadores` deixa o `doador1`
(homem, intervalo de 60 dias) com a última doação há 10 dias, ambos relativos à data da subida:

| Slot | Quando | Capacidade | Uso na demonstração |
| --- | --- | --- | --- |
| `slot-futuro`, `slot-futuro-2`, `slot-futuro-3` | daqui a 90+ dias | 5, 5, 3 | caminho feliz (doador apto) |
| `slot-proximo` | daqui a 7 dias | 5 | falha no passo 2: RN01 (última doação há 10 dias, intervalo de 60) |
| `slot-lotado` | daqui a 30 dias | 0 | recusa no passo 1 (não aparece na listagem) |

Usuários de teste (realm `startech`): `doador1` / `doador123` (app) e `operador1` / `operador123` (painel).
Para usar outras portas no host: `GATEWAY_HOST_PORT=28080 KEYCLOAK_HOST_PORT=28089 scripts/demo/...`.

## 1. Fluxo de ponta a ponta (6.1)

Login no app do doador e no painel web, pelo Keycloak e pelo Gateway (#14 e #15). No app: home, horários
(`GET /api/mobile/slots`), agendamento e acompanhamento. No painel: lista e criação de campanhas.

Caminho de cada requisição: cliente → `gateway` (valida o JWT, o papel e a audiência e injeta `X-User-Id`) →
BFF → serviços de domínio. Sem o app, o mesmo caminho pelo terminal:

```bash
scripts/demo/agendar.sh slot-futuro
```

Esperado: `202` com o link `acompanhar`. A situação vai de `EM_ANDAMENTO` a `CONFIRMADO`, e a resposta final
traz o link `agendamento`.

## 2. BFF Mobile × BFF Web (4.4)

```bash
scripts/demo/comparar-bffs.sh
```

Esperado:
- **BFF Mobile** (`/api/mobile/home`): um único objeto agregado, com o perfil do doador (`ms-doadores`) e as
  campanhas filtradas pelo tipo sanguíneo dele (`ms-hemocentros`). Traz também `status`,
  `servicosIndisponiveis` e `campanhasPersonalizadas`, porque degrada sem quebrar a tela se um dos serviços cair.
  Uma requisição por tela, pensada para a rede móvel.
- **BFF Web** (`/api/web/campanhas`): a lista de campanhas para gestão, sem dados do doador, mais a criação de
  campanhas (`POST`) com leitura imediata da própria escrita.

## 3. SAGA: caminho feliz e falha com compensação (6.1)

**Caminho feliz:** agendar no app um `slot-futuro*` (ou `scripts/demo/agendar.sh slot-futuro`). Depois:

```bash
scripts/demo/evidencia-saga.sh <sagaId>
```

Esperado em cada participante:
- `ms-orquestrador` (`db-orquestrador`): `STEP1 OK`, `STEP2 OK`, `STEP3 PUBLICADO` e `OK`, `STEP4 OK` no
  `saga_step_log`, e no `outbox_events` o comando `programar-lembrete` e o evento `saga.agendamento.confirmado`,
  publicados;
- `ms-agendamentos` (`db-agendamentos`): agendamento `CONFIRMADO` e uma vaga a mais ocupada no slot;
- `ms-doadores` (`db-doadores`): a última doação do doador e a trava de elegibilidade criada;
- `ms-comunicacao` (`db-comunicacao`): lembrete `PROGRAMADO` para D-1 e as notificações `CONFIRMACAO` e `DESFECHO`.

**Falha provocada ao vivo, opção A (passo 2, RN01):** agendar o `slot-proximo`.
Esperado: a situação `CANCELADO` e, no app, o motivo calculado pelo `ms-doadores` com a Portaria MS nº 5/2017
("A última doação foi em …, a próxima doação de sangue total é permitida a partir de … (60 dias de intervalo
para o sexo masculino)"). No `evidencia-saga.sh`: `STEP1 OK`, `STEP2 RECUSADO`, `STEP1 COMPENSATE OK`, agendamento
`CANCELADO_COMPENSACAO_SAGA`, vaga devolvida (`vagas_ocupadas` volta ao valor anterior), nenhuma trava e só a
notificação `DESFECHO`.

**Falha provocada ao vivo, opção B (passo 3, compensações 3 → 2 → 1):**

```bash
COMUNICACAO_SIMULAR_FALHA_DOADORES=11111111-1111-1111-1111-111111111111 \
  docker compose --profile ia up -d ms-comunicacao
scripts/demo/agendar.sh slot-futuro-2
scripts/demo/evidencia-saga.sh <sagaId>
docker compose --profile ia up -d ms-comunicacao  # volta ao normal
```

Esperado: `STEP3 PUBLICADO` e `STEP3 RECUSADO` (o `ms-comunicacao` respondeu `FALHOU`), seguidos das
compensações em ordem inversa: `STEP3 COMPENSATE PUBLICADO` (o `cancelar-lembrete` vai pelo Outbox),
`STEP2 COMPENSATE OK` e `STEP1 COMPENSATE OK`. O agendamento fica `CANCELADO_COMPENSACAO_SAGA`, a vaga é devolvida
e a trava é removida do `db-doadores`.

**Recusa sem compensação:** `scripts/demo/agendar.sh slot-lotado` → `RECUSADO`, só `STEP1 RECUSADO` e nenhum
agendamento criado.

Toda chamada aos participantes leva `Idempotency-Key: saga-{id}-step{n}`. Falha técnica é retentada com backoff
e jitter; recusa de negócio (404, 409, 422) não é retentada.

## 4. HATEOAS no agendamento (4.2)

```bash
scripts/demo/agendamento.sh <agendamentoId>            # confirmado: links self e cancelar
scripts/demo/agendamento.sh <agendamentoId> cancelar   # segue o link cancelar
```

Esperado: confirmado com os links `self` e `cancelar`. Depois de seguir `cancelar`, o agendamento fica
`CANCELADO_DOADOR`, com `self` e `novo-agendamento` (sem ações sobre o cancelado), a vaga volta ao slot e
cancelar de novo responde `409 agendamento-ja-cancelado`. No app, o botão de cancelar aparece ou some conforme o
link. Regras completas na especificação de contratos (§3).

> O cancelamento pelo doador não cancela o lembrete no `ms-comunicacao` (não há evento definido para isso;
> ver contratos §2). Só a compensação da SAGA cancela o lembrete.

## 5. CQRS (6.1)

Criar uma campanha no painel web e mostrá-la no app. Pelo terminal:

```bash
scripts/demo/cqrs.sh
```

Esperado: o tempo até a campanha aparecer na home do app (em torno de 0,5 s). A campanha aparece no modelo de
escrita (`campanhas` no PostgreSQL, com a linha do `outbox_events` publicada) e no modelo de leitura
(`campanhas_view` no MongoDB, com a mesma `versao`). O `scripts/e2e-cqrs.sh` mede a mediana e o máximo em várias
escritas.

## 6. Bancos separados por serviço (1.1 e 4.5)

```bash
scripts/demo/evidencia-bancos.sh
```

Esperado: um contêiner e um volume por banco (`db-doadores`, `db-agendamentos`, `db-hemocentros` + `mongo`,
`db-orquestrador`, `db-comunicacao` e `db-keycloak`), as tabelas próprias de cada um e cada serviço apontando só
para o seu banco. O `ms-hemocentros` tem dois bancos por causa do CQRS.

## 7. RAG e LangChain (6.2)

```bash
scripts/demo/assistente.sh "Fiz tatuagem há 3 meses, posso doar?"                 # RAG
scripts/demo/assistente.sh "Quais campanhas estão abertas para o meu tipo sanguíneo?" # tool com dados reais
```

Esperado: `modo: RAG`, com as fontes da Portaria de Consolidação MS nº 5/2017. Depois, `modo: FERRAMENTA`, com
as campanhas vigentes vindas do `ms-hemocentros`, incluindo a criada no passo 5. A avaliação com 5 perguntas,
com e sem recuperação, está em [`docs/ia/avaliacao-rag.md`](./ia/avaliacao-rag.md) e é gerada por
`scripts/avaliar-rag.py`.

## 8. LLM como serviço distribuído (6.2)

```bash
scripts/demo/derrubar-llm.sh   # para o Ollama e faz 5 perguntas
scripts/demo/religar-llm.sh    # religa, aquece o modelo e espera o circuito fechar
```

Esperado ao derrubar: todas as respostas em `FALLBACK` (`degradado: true`), em poucos milissegundos, com o
trecho da Portaria recuperado no lugar da resposta gerada. Depois de 3 falhas o circuito abre e o `ms-rag` nem
tenta o Ollama. Ao religar: o circuito fica aberto por 30 s, a chamada de teste (meio-aberto) fecha o circuito, e
a pergunta seguinte volta a `RAG`, em cerca de 2,5 s.

Latência medida e custo estimado por operação em escala: [`docs/ia/avaliacao-rag.md`](./ia/avaliacao-rag.md)
(seções "Latência e tokens" e "Projeção de custo").

## Plano B

| Problema | O que fazer |
| --- | --- |
| App ou painel não abre | Mesmos passos pelo terminal: `agendar.sh`, `agendamento.sh`, `cqrs.sh`, `assistente.sh` (passam pelo Gateway, como os clientes). |
| Primeira pergunta ao assistente cai em `FALLBACK` por timeout | O modelo esfriou: `scripts/demo/religar-llm.sh` (aquece direto no Ollama). |
| Porta 8080 ou 8089 ocupada | `GATEWAY_HOST_PORT=28080 KEYCLOAK_HOST_PORT=28089 scripts/demo/preparar.sh` (e o mesmo prefixo nos outros scripts). |
| `409 agendamento-ativo` ao agendar | O doador já tem um agendamento confirmado (RN09): cancele-o com `agendamento.sh <id> cancelar` ou rode `preparar.sh`. |
| Grade sem vagas depois de vários ensaios | `scripts/demo/preparar.sh`. |
