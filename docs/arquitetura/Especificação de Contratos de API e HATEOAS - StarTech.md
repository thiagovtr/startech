# **Especificação de Contratos de API e HATEOAS — StarTech**

* **Versão:** 2.0.0  
* **Data da Última Revisão:** 2026-11-21 (SAGA completa com participantes reais, HATEOAS no agendamento e especificação OpenAPI 3.0)  
* **Especificação OpenAPI / Swagger UI:** [`openapi.yaml`](./openapi.yaml) *(abra em [editor.swagger.io](https://editor.swagger.io/) para navegação interativa de rotas, DTOs e exemplos RFC 7807)*  
* **Responsável:** Equipe StarTech (Diovani da Cruz, Ezequiel Dominguez, Matheus Freire Costa Pimenta, Thiago Vinícius)  
* **Status:** Homologado

# **1\. Visão Geral e Padrões de Comunicação**

Este documento estabelece os contratos RESTful de comunicação entre os clientes (App Mobile e Painel Web), a camada de borda (API Gateway / BFFs) e os microsserviços de domínio da arquitetura **StarTech**.

## **1.1 Estratégia de Versionamento**

Todos os microsserviços adotam versionamento explícito na URI (`/api/v1/`). Isso garante roteamento determinístico no API Gateway e previne quebra de compatibilidade em versões legadas de clientes móveis.

## **1.2 Tratamento Padronizado de Erros (RFC 7807\)**

Todas as respostas de erro HTTP (4xx e 5xx) seguem o padrão `application/problem+json` (Problem Details for HTTP APIs). Isso fornece uma semântica rica para tratamento de exceções de negócio no frontend.

**Exemplo de Resposta de Erro (Regra de Negócio Violada):**{

  "type": "urn:startech:error:intervalo-biologico-violado",

  "title": "Violação de Intervalo Biológico Regulamentar",

  "status": 422,

  "detail": "O doador do sexo masculino realizou doação em 2026-09-15. Conforme a Portaria MS nº 5/2017, a data mínima para nova doação de sangue total é 2026-11-14 (60 dias de intervalo).",

  "instance": "/api/v1/agendamentos/solicitacoes/req-99182",

  "invalidParams": \[

    {

      "name": "dataHoraAgendamento",

      "reason": "A data pretendida (2026-10-25) é inferior à data de liberação calculada (2026-11-14)."

    }

  \]

}

# 

# **2\. Contratos Principais dos Microsserviços e BFFs**

Abaixo estão detalhados os endpoints críticos que suportam os fluxos de mobilização, autenticação e a transação SAGA de agendamento.

| Componente / Serviço | Método | Endpoint | Status Sucesso | Descrição Semântica e Tratamento |
| :---- | :---- | :---- | :---- | :---- |
| **Keycloak (Auth)** | `POST` | `/realms/startech/protocol/openid-connect/token` | `200 OK` | Autentica o usuário (Doador ou Operador) e emite o token JWT assinado (RS256). Retorna `401 Unauthorized` se inválido. |
| **BFF Mobile** | `GET` | `/bff-mobile/home` | `200 OK` | Agrega perfil do doador (`doadores`) e campanhas compatíveis com seu tipo sanguíneo (`hemocentros`). Opera com Graceful Degradation. |
| **BFF Mobile** | `POST` | `/bff-mobile/agendamentos` | `202 Accepted` | Recebe a solicitação de agendamento do doador (`X-User-Id` do Gateway) e a repassa ao `ms-orquestrador`, devolvendo `sagaId`, `agendamentoId` e o link de acompanhamento. Repassa `409 Conflict` (RN09). |
| **BFF Mobile** | `GET` | `/bff-mobile/sagas/{sagaId}` | `200 OK` | Consulta o andamento da solicitação de agendamento no `ms-orquestrador` (usado pelo app para acompanhar até `CONFIRMED`, `REJECTED` ou `COMPENSATED`). Confirmada, traz o link `agendamento` (`/api/mobile/agendamentos/{agendamentoId}`). |
| **BFF Mobile** | `GET` | `/bff-mobile/slots` | `200 OK` | Horários disponíveis do `agendamentos`, com o link `agendar` reescrito para `POST /api/mobile/agendamentos`. `503` se o `agendamentos` estiver fora. |
| **BFF Mobile** | `GET` | `/bff-mobile/agendamentos` | `200 OK` | Agendamentos do doador autenticado (`X-User-Id`), repassados do `agendamentos` com os links reescritos para as rotas públicas do Gateway (`/api/mobile/...`). |
| **BFF Mobile** | `GET` | `/bff-mobile/agendamentos/{id}` | `200 OK` | Recurso Agendamento (§3) com links públicos. Agendamento de outro doador responde `404`, sem revelar que existe. |
| **BFF Mobile** | `POST` | `/bff-mobile/agendamentos/{id}/cancelamento` | `200 OK` | Confere o dono e repassa o cancelamento ao `agendamentos`; devolve o recurso com os links novos. Repassa `409 Conflict`. |
| **BFF Mobile** | `POST` | `/bff-mobile/assistente` | `200 OK` | Assistente do doador: corpo `{pergunta}`. Busca o tipo sanguíneo do doador no perfil (`doadores`) e repassa a pergunta ao `ms-rag`. Devolve `{resposta, modo, fontes, degradado}`. Com o `ms-rag` fora, responde `200` com mensagem de fallback (`degradado: true`). |
| **BFF Web** | `POST` | `/bff-web/campanhas` | `201 Created` | Recebe cadastro de campanha do painel React Web e repassa comando ao serviço `hemocentros`. Permite imediato RYOW (Read-Your-Own-Writes). |
| **1\. doadores** | `GET` | `/api/v1/doadores/{id}` | `200 OK` | Retorna dados cadastrais, tipo sanguíneo (`O-`, `A+`, etc.) e status atual do ciclo de elegibilidade. `404 Not Found` se inexistente. |
| **1\. doadores** | `POST` | `/api/v1/doadores/{id}/reservas-elegibilidade` | `200 OK` | Corpo `{agendamentoId, dataSlot}`. Valida a RN01 (60 dias para homens e 90 para mulheres, contados da última doação) e aplica trava temporal para a SAGA. Retorna `422 Unprocessable Entity` (`urn:startech:error:intervalo-minimo-nao-cumprido`) se inapto, com `detail` para o app, `liberadoAPartirDe`, `intervaloDias` e `invalidParams` (`dataSlot`). `404` se o doador não existe; `409` se o `agendamentoId` já trava outro doador. Idempotente pelo `agendamentoId`: repetir devolve a mesma trava. Exige `Idempotency-Key: saga-{sagaId}-step2`. Passo 2 da SAGA. |
| **1\. doadores** | `DELETE` | `/api/v1/doadores/{id}/reservas-elegibilidade/{agendamentoId}` | `204 No Content` | **Compensação do Passo 2:** remove a trava temporal do doador. Idempotente (trava já removida também retorna `204`). |
| **2\. hemocentros** | `POST` | `/api/v1/campanhas` | `201 Created` | Grava nova campanha e evento Outbox no **PostgreSQL** (Command Store). Retorna `400 Bad Request` se payload inválido. |
| **2\. hemocentros** | `GET` | `/api/v1/campanhas?tipo_sanguineo=O-` | `200 OK` | **Leitura Direta (Query CQRS)** na view desnormalizada do **MongoDB** filtrada por tipo sanguíneo. |
| **3\. agendamentos** | `GET` | `/api/v1/slots?postoId=&de=&ate=` | `200 OK` | Grade de horários: só slots futuros com vaga, do mais próximo para o mais distante (`{itens: [{slotId, postoId, dataHoraInicio, dataHoraFim, vagasDisponiveis, _links.agendar}]}`). O link `agendar` aponta para `POST /api/v1/sagas/agendamento` com o corpo `{slotId}`. |
| **3\. agendamentos** | `POST` | `/api/v1/slots/{slotId}/reservas` | `201 Created` | **Passo 1 da SAGA:** cria o agendamento `CRIADO_PROVISORIO` (com o `agendamentoId` gerado pelo orquestrador) e ocupa uma vaga do slot com lock otimista. Corpo `{agendamentoId, doadorId}`. Retorna `404 Not Found` se o slot não existe e `409 Conflict` se ele está esgotado (`slot-esgotado`), se o horário já passou (`slot-encerrado`) ou se o doador já possui agendamento ativo (`agendamento-ativo`, RN09). Duas reservas na última vaga são serializadas (slot travado com `SELECT ... FOR UPDATE`). Idempotente pelo `agendamentoId`: repetir devolve o mesmo corpo sem ocupar outra vaga (o mesmo id com outro slot ou doador responde `409 reserva-divergente`). Exige `Idempotency-Key: saga-{sagaId}-step1`. Corpo da resposta: `{agendamentoId, slotId, dataHoraInicio, dataHoraFim, status}` (o orquestrador usa `dataHoraInicio` como `dataSlot` no Passo 2 e no lembrete do Passo 3). |
| **3\. agendamentos** | `DELETE` | `/api/v1/slots/{slotId}/reservas/{agendamentoId}` | `204 No Content` | **Compensação do Passo 1:** libera a vaga e marca o agendamento como `CANCELADO_COMPENSACAO_SAGA`. Idempotente. |
| **3\. agendamentos** | `POST` | `/api/v1/agendamentos/{id}/confirmacao` | `200 OK` | **Passo 4 (final) da SAGA:** muda o agendamento de `CRIADO_PROVISORIO` para `CONFIRMADO` e devolve o recurso do §3. Idempotente (`Idempotency-Key: saga-{sagaId}-step4`): já confirmado responde `200`. `409` se o agendamento foi cancelado e `404` se não existe. |
| **3\. agendamentos** | `GET` | `/api/v1/agendamentos/{id}` | `200 OK` | Recurso Agendamento com HATEOAS (§3): os links de ação mudam com o estado. `404 Not Found` se inexistente. |
| **3\. agendamentos** | `GET` | `/api/v1/agendamentos?doadorId={id}` | `200 OK` | Agendamentos do doador (`{itens: [...], _links}`), do horário mais recente para o mais antigo, cada um na representação do §3. `400` sem `doadorId`. |
| **3\. agendamentos** | `POST` | `/api/v1/agendamentos/{id}/cancelamento` | `200 OK` | Corpo opcional `{motivo}`. Cancela agendamento `CONFIRMADO` até 2 h antes do início: muda para `CANCELADO_DOADOR`, libera a vaga no slot e devolve o recurso com os links novos. `409 Conflict` se já cancelado (`agendamento-ja-cancelado`), ainda `CRIADO_PROVISORIO` (`agendamento-nao-cancelavel`) ou fora do prazo (`prazo-cancelamento-expirado`); `404` se inexistente. Não há evento no RabbitMQ: o lembrete só é cancelado pela compensação da SAGA (o `ms-comunicacao` ainda não consome cancelamento pelo doador). |
| **4\. comunicacao** | `GET` | `/api/v1/comunicacao/historico/{doadorId}` | `200 OK` | Consulta histórico auditável de notificações enviadas ao doador (`CONFIRMACAO`, `LEMBRETE`, `CANCELAMENTO`, `DESFECHO`), da mais recente para a mais antiga, paginado por `pagina` e `tamanho` (máx. 100). Doador sem histórico devolve lista vazia. Uso interno (rede `startech-net-api`). |
| **6\. rag** | `POST` | `/api/v1/rag/perguntas` | `200 OK` | Corpo `{pergunta, usarRag?, tipoSanguineo?}`. Resposta `{resposta, modo, fontes[{secao, fonte, trecho}], latenciaMs, uso{tokensEntrada, tokensSaida}, motivoFallback}`. `modo` é `RAG` (Portaria MS nº 5/2017), `FERRAMENTA` (campanhas vigentes do `hemocentros`), `FORA_DO_ESCOPO` (recusa sem LLM), `SEM_RAG` (só para avaliação) ou `FALLBACK` (timeout de 4 s, erro ou circuit breaker aberto). Nunca devolve 5xx por causa do LLM; `400` com payload inválido (ADR-007). |
| **5\. orquestrador** | `POST` | `/api/v1/sagas/agendamento` | `202 Accepted` | Inicia a SAGA Orquestrada de agendamento (corpo `{doadorId, slotId}`), gerando `sagaId` e `agendamentoId`. Retorna `Location: /api/v1/sagas/{sagaId}`. `409 Conflict` se o doador já possuir SAGA em andamento (RN09). |
| **5\. orquestrador** | `GET` | `/api/v1/sagas/{sagaId}` | `200 OK` | Estado atual da SAGA, passos executados (ação positiva e compensações) e, quando recusada ou compensada, o motivo em `application/problem+json`. `404 Not Found` se inexistente. |

## **2.1 Mensagens Assíncronas da SAGA (RabbitMQ, exchange `startech.events.exchange`)**

O Passo 3 (comunicacao) e sua compensação são comandos assíncronos publicados pelo `ms-orquestrador` via Transactional Outbox (ADR-003 e ADR-006). Todas as mensagens são JSON (`content_type: application/json`), persistentes, e trazem nas propriedades AMQP o `message_id` (chave de deduplicação no consumidor) e o `correlation_id` (`X-Request-Id` de origem).

| Routing key | Produtor → Consumidor | Fila | `message_id` | Significado |
| :---- | :---- | :---- | :---- | :---- |
| `saga.comando.comunicacao.programar-lembrete` | orquestrador → comunicacao | `comunicacao.saga.comandos` | `saga-{sagaId}-step3` | Passo 3: grava o lembrete D-1 e dispara a confirmação ao doador. |
| `saga.comando.comunicacao.cancelar-lembrete` | orquestrador → comunicacao | `comunicacao.saga.comandos` | `saga-{sagaId}-step3-comp` | Compensação do Passo 3: cancela o lembrete. Idempotente, inclusive se o lembrete não existir. Não tem resposta: o Outbox garante a entrega. |
| `comunicacao.lembrete.programado` / `comunicacao.lembrete.falhou` | comunicacao → orquestrador | `orquestrador.saga.respostas` | `saga-{sagaId}-step3-resposta` | Resposta do Passo 3. `falhou`, ou nenhuma resposta em 30 s, dispara as compensações. |
| `saga.agendamento.confirmado` / `saga.agendamento.compensado` | orquestrador → interessados | — | `saga-{sagaId}-desfecho` | Evento de desfecho da SAGA. |
| `saga.compensacao.falhou` | orquestrador → operação | `saga.compensations.dlq` | `saga-{sagaId}-comp-falhou` | Compensação que falhou mais de 5 vezes (Exponential Backoff + Jitter); requer intervenção manual. |

**Corpos das mensagens:**

```json
// saga.comando.comunicacao.programar-lembrete
{"tipo": "ProgramarLembreteEConfirmar", "sagaId": "…", "agendamentoId": "…", "doadorId": "…",
 "slotId": "…", "dataHoraInicio": "2026-11-25T14:00:00Z", "emitidoEm": "2026-11-17T10:00:00Z"}

// saga.comando.comunicacao.cancelar-lembrete
{"tipo": "CancelarLembreteAgendado", "sagaId": "…", "agendamentoId": "…", "doadorId": "…",
 "emitidoEm": "…"}

// comunicacao.lembrete.programado | comunicacao.lembrete.falhou
{"sagaId": "…", "agendamentoId": "…", "resultado": "PROGRAMADO" | "FALHOU",
 "motivo": "texto opcional quando FALHOU", "emitidoEm": "…"}

// saga.agendamento.confirmado | saga.agendamento.compensado | saga.compensacao.falhou
{"sagaId": "…", "agendamentoId": "…", "doadorId": "…", "status": "CONFIRMED" | "COMPENSATED" | "COMPENSATION_FAILED",
 "detalhe": "…", "emitidoEm": "…"}
```

**Topologia (declaração idempotente por quem usa, sem arquivo central de definições):**

> * Exchange `startech.events.exchange` (topic, durável): declarada por todo serviço que publica ou consome;  
> * Cada consumidor declara a própria fila e o binding. O `ms-orquestrador` declara `orquestrador.saga.respostas` (binding `comunicacao.lembrete.*`, com dead-letter para `orquestrador.saga.respostas.dlq` via `startech.events.dlx`) e `saga.compensations.dlq` (binding `saga.compensacao.falhou`);  
> * O `ms-orquestrador` **também** declara `comunicacao.saga.comandos` (durável, **sem argumentos extras**, binding `saga.comando.comunicacao.*`) para que nenhum comando se perca se o `ms-comunicacao` ainda não estiver no ar. O `ms-comunicacao` deve declarar essa fila com exatamente os mesmos argumentos (o RabbitMQ recusa redeclaração divergente com `PRECONDITION_FAILED`).  
> * O `ms-comunicacao` declara `comunicacao.saga.comandos` (sem DLQ, pela regra acima; comandos ilegíveis vão para a tabela `mensagens_rejeitadas` e, se o `sagaId` for legível mas os dados não, ele responde `comunicacao.lembrete.falhou`, para a SAGA compensar sem esperar o timeout) e a fila própria `comunicacao.notificacoes` (bindings `saga.agendamento.*` e `hemocentros.campanha.criada`, com dead-letter para `comunicacao.notificacoes.dlq` via `startech.events.dlx`). A resposta do Passo 3 é gravada no Outbox do `ms-comunicacao` na mesma transação do lembrete e do inbox (`processed_messages`).

# 

# **3\. Especificação de Recurso com HATEOAS (Richardson \- Nível 3\)**

O recurso **Agendamento de Doação** (`/api/v1/agendamentos/{id}`) exportado pelo microsserviço `agendamentos` e consumido pelo `BFF Mobile` implementa o *Hypermedia as the Engine of Application State* (HATEOAS).

Nesse modelo, os links de ação (dentro da propriedade `_links`) mudam dinamicamente conforme a máquina de estados do agendamento avança. Isso isenta os clientes (App React Native) de codificarem lógica condicional pesada.

| Estado | Links | Observação |
| :---- | :---- | :---- |
| `CRIADO_PROVISORIO` | `self` | A SAGA ainda está em andamento; quem desfaz é a compensação do Passo 1. |
| `CONFIRMADO`, até 2 h antes do início | `self`, `cancelar` | |
| `CONFIRMADO`, a menos de 2 h do início | `self` | Fora do prazo de cancelamento. |
| `CONFIRMADO`, horário encerrado | `self` | `concluido: true`. |
| `CANCELADO_DOADOR` / `CANCELADO_COMPENSACAO_SAGA` | `self`, `novo-agendamento` | Nenhuma ação sobre o agendamento cancelado. |

O `BFF Mobile` reescreve os links para as rotas públicas do Gateway: `/api/v1/agendamentos/{id}...` vira `/api/mobile/agendamentos/{id}...` e `/api/v1/sagas/agendamento` (nova SAGA) vira `POST /api/mobile/agendamentos`. Links sem rota pública correspondente são descartados. Os exemplos abaixo mostram a resposta do `agendamentos`.

## **3.1 Estado: Agendamento `CONFIRMADO`**

Neste estado, o doador possui uma vaga garantida e ainda está em tempo hábil para cancelar.

**Requisição:** `GET /api/v1/agendamentos/appt-88412`

**Resposta (200 OK):**

```json
{
  "id": "appt-88412",
  "status": "CONFIRMADO",
  "concluido": false,
  "doadorId": "123",
  "slot": {
    "slotId": "slot-20261025-1400",
    "postoId": "posto-central-lavras",
    "dataHoraInicio": "2026-10-25T14:00:00Z",
    "dataHoraFim": "2026-10-25T14:20:00Z"
  },
  "disclaimerLegal": "A confirmação deste agendamento organiza o fluxo no posto e não garante a doação. A aptidão final depende da triagem clínica presencial.",
  "_links": {
    "self": {
      "href": "/api/v1/agendamentos/appt-88412",
      "method": "GET",
      "title": "Consultar dados do agendamento"
    },
    "cancelar": {
      "href": "/api/v1/agendamentos/appt-88412/cancelamento",
      "method": "POST",
      "title": "Efetuar cancelamento e liberar vaga para outros doadores",
      "conditions": "Permitido até 2 horas antes do horário agendado"
    }
  }
}
```

## **3.2 Estado: Agendamento `CANCELADO_DOADOR`**

Neste estado, as ações mutáveis são removidas dinamicamente do payload pela API. Em vez disso, o sistema sugere que o doador inicie um novo agendamento do zero.

**Requisição:** `POST /api/v1/agendamentos/appt-88412/cancelamento` com `{"motivo": "Imprevisto pessoal autodeclarado pelo doador"}` (ou `GET /api/v1/agendamentos/appt-88412` depois do cancelamento)

**Resposta (200 OK):**

```json
{
  "id": "appt-88412",
  "status": "CANCELADO_DOADOR",
  "concluido": false,
  "doadorId": "123",
  "slot": {
    "slotId": "slot-20261025-1400",
    "postoId": "posto-central-lavras",
    "dataHoraInicio": "2026-10-25T14:00:00Z",
    "dataHoraFim": "2026-10-25T14:20:00Z"
  },
  "dataCancelamento": "2026-10-24T10:15:00Z",
  "motivo": "Imprevisto pessoal autodeclarado pelo doador",
  "slotLiberado": "slot-20261025-1400",
  "_links": {
    "self": {
      "href": "/api/v1/agendamentos/appt-88412",
      "method": "GET",
      "title": "Consultar dados do agendamento"
    },
    "novo-agendamento": {
      "href": "/api/v1/sagas/agendamento",
      "method": "POST",
      "title": "Solicitar um novo agendamento"
    }
  }
}
```

Cancelar de novo responde `409 Conflict` (`application/problem+json`):

```json
{
  "type": "urn:startech:error:agendamento-ja-cancelado",
  "title": "Agendamento já cancelado",
  "status": 409,
  "detail": "O agendamento appt-88412 já está CANCELADO_DOADOR.",
  "instance": "/api/v1/agendamentos/appt-88412/cancelamento"
}
```
