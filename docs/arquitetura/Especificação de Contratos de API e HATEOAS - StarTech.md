# **Especificação de Contratos de API e HATEOAS — StarTech**

* **Versão:** 1.1.0  
* **Data da Última Revisão:** 2026-11-16 (SAGA coordenada pelo `ms-orquestrador`, conforme ADR-006)  
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
| **BFF Mobile** | `GET` | `/bff-mobile/sagas/{sagaId}` | `200 OK` | Consulta o andamento da solicitação de agendamento no `ms-orquestrador` (usado pelo app para acompanhar até `CONFIRMED`, `REJECTED` ou `COMPENSATED`). |
| **BFF Web** | `POST` | `/bff-web/campanhas` | `201 Created` | Recebe cadastro de campanha do painel React Web e repassa comando ao serviço `hemocentros`. Permite imediato RYOW (Read-Your-Own-Writes). |
| **1\. doadores** | `GET` | `/api/v1/doadores/{id}` | `200 OK` | Retorna dados cadastrais, tipo sanguíneo (`O-`, `A+`, etc.) e status atual do ciclo de elegibilidade. `404 Not Found` se inexistente. |
| **1\. doadores** | `POST` | `/api/v1/doadores/{id}/reservas-elegibilidade` | `200 OK` | Valida a RN01 (60/90 dias e quarentenas) e aplica trava temporal para a SAGA. Retorna `422 Unprocessable Entity` se inapto. Exige `Idempotency-Key: saga-{sagaId}-step2`. Passo 2 da SAGA. |
| **1\. doadores** | `DELETE` | `/api/v1/doadores/{id}/reservas-elegibilidade/{agendamentoId}` | `204 No Content` | **Compensação do Passo 2:** remove a trava temporal do doador. Idempotente (trava já removida também retorna `204`). |
| **2\. hemocentros** | `POST` | `/api/v1/campanhas` | `201 Created` | Grava nova campanha e evento Outbox no **PostgreSQL** (Command Store). Retorna `400 Bad Request` se payload inválido. |
| **2\. hemocentros** | `GET` | `/api/v1/campanhas?tipo_sanguineo=O-` | `200 OK` | **Leitura Direta (Query CQRS)** na view desnormalizada do **MongoDB** filtrada por tipo sanguíneo. |
| **3\. agendamentos** | `POST` | `/api/v1/slots/{slotId}/reservas` | `201 Created` | **Passo 1 da SAGA:** cria o agendamento `CRIADO_PROVISORIO` (com o `agendamentoId` gerado pelo orquestrador) e ocupa uma vaga do slot com lock otimista. Retorna `409 Conflict` se slot esgotado ou doador já possuir agendamento ativo (RN09). Exige `Idempotency-Key: saga-{sagaId}-step1`. Corpo da resposta: `{agendamentoId, slotId, dataHoraInicio, dataHoraFim, status}` (o orquestrador usa `dataHoraInicio` como `dataSlot` no Passo 2 e no lembrete do Passo 3). |
| **3\. agendamentos** | `DELETE` | `/api/v1/slots/{slotId}/reservas/{agendamentoId}` | `204 No Content` | **Compensação do Passo 1:** libera a vaga e marca o agendamento como `CANCELADO_COMPENSACAO_SAGA`. Idempotente. |
| **3\. agendamentos** | `POST` | `/api/v1/agendamentos/{id}/confirmacao` | `200 OK` | **Passo 4 (final) da SAGA:** muda o agendamento de `CRIADO_PROVISORIO` para `CONFIRMADO`. Idempotente (`Idempotency-Key: saga-{sagaId}-step4`). |
| **3\. agendamentos** | `POST` | `/api/v1/agendamentos/{id}/cancelamento` | `200 OK` | Cancela agendamento confirmado, libera vaga no slot e publica evento de cancelamento no RabbitMQ. |
| **4\. comunicacao** | `GET` | `/api/v1/comunicacao/historico/{doadorId}` | `200 OK` | Consulta histórico auditável de notificações e lembretes enviados ao doador. |
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

# 

# **3\. Especificação de Recurso com HATEOAS (Richardson \- Nível 3\)**

O recurso **Agendamento de Doação** (`/api/v1/agendamentos/{id}`) exportado pelo microsserviço `agendamentos` e consumido pelo `BFF Mobile` implementa o *Hypermedia as the Engine of Application State* (HATEOAS).

Nesse modelo, os links de ação (dentro da propriedade `_links`) mudam dinamicamente conforme a máquina de estados do agendamento avança. Isso isenta os clientes (App React Native) de codificarem lógica condicional pesada.

## **3.1 Estado: Agendamento `CONFIRMADO`**

Neste estado, o doador possui uma vaga garantida e ainda está em tempo hábil para cancelar, reagendar ou baixar seu comprovante em PDF.

**Requisição:**  
`GET /api/v1/agendamentos/appt-88412`

**Resposta (200 OK):**n  
{  
"id": "appt-88412",  
"protocolo": "ST-2026-88412",  
"status": "CONFIRMADO",  
"doadorId": "123",  
"posto": {  
"postoId": "posto-central-lavras",  
"nome": "Posto Avançado Hemominas Lavras",  
"endereco": "Rua Dr. Milton Viana, 410 \- Lavras/MG"  
},  
"slot": {  
"slotId": "slot-20261025-1400",  
"dataHoraInicio": "2026-10-25T14:00:00Z",  
"dataHoraFim": "2026-10-25T14:20:00Z"  
},  
"disclaimerLegal": "A confirmação deste agendamento organiza o fluxo no posto e não garante a doação. A aptidão final depende da triagem clínica presencial.",  
"\_links": {  
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
},  
"reagendar": {  
"href": "/api/v1/agendamentos/appt-88412/reagendamento",  
"method": "PUT",  
"title": "Alterar dia ou horário do agendamento atual"  
},  
"campanhas-compativeis": {  
"href": "/api/v1/campanhas?tipo\_sanguineo=O-",  
"method": "GET",  
"title": "Ver campanhas ativas para o seu tipo sanguíneo"  
},  
"comprovante-pdf": {  
"href": "/api/v1/agendamentos/appt-88412/comprovante",  
"method": "GET",  
"type": "application/pdf",  
"title": "Baixar comprovante de agendamento em PDF"  
}  
}  
}

## **3.2 Estado: Agendamento \`CANCELADO\_DOADOR\`**

Neste estado, as ações mutáveis são removidas dinamicamente do payload pela API. Em vez disso, o sistema sugere que o doador busque novas campanhas ou inicie um novo agendamento do zero.

**Requisição:**

\`GET /api/v1/agendamentos/appt-88412\`

**Resposta (200 OK):**

\`\`\`json

{

  "id": "appt-88412",

  "protocolo": "ST-2026-88412",

  "status": "CANCELADO\_DOADOR",

  "dataCancelamento": "2026-10-24T10:15:00Z",

  "motivo": "Imprevisto pessoal autodeclarado pelo doador",

  "slotLiberado": "slot-20261025-1400",

  "\_links": {

    "self": {

      "href": "/api/v1/agendamentos/appt-88412",

      "method": "GET"

    },

    "novo-agendamento": {

      "href": "/api/v1/sagas/agendamento",

      "method": "POST",

      "title": "Consultar grade de postos e solicitar novo agendamento"

    },

    "campanhas-ativas": {

      "href": "/api/v1/campanhas?tipo\_sanguineo=O-",

      "method": "GET",

      "title": "Visualizar campanhas vigentes na sua região"

    }

  }

}  
