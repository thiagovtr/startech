# **Especificação de Contratos de API e HATEOAS — StarTech**

* **Versão:** 1.0.0  
* **Data da Última Revisão:** 2026-10-21  
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
| **BFF Web** | `POST` | `/bff-web/campanhas` | `201 Created` | Recebe cadastro de campanha do painel React Web e repassa comando ao serviço `hemocentros`. Permite imediato RYOW (Read-Your-Own-Writes). |
| **1\. doadores** | `GET` | `/api/v1/doadores/{id}` | `200 OK` | Retorna dados cadastrais, tipo sanguíneo (`O-`, `A+`, etc.) e status atual do ciclo de elegibilidade. `404 Not Found` se inexistente. |
| **1\. doadores** | `POST` | `/api/v1/doadores/{id}/reservas-elegibilidade` | `200 OK` | Valida a RN01 (60/90 dias e quarentenas) e aplica trava temporal para a SAGA. Retorna `422 Unprocessable Entity` se inapto. |
| **2\. hemocentros** | `POST` | `/api/v1/campanhas` | `201 Created` | Grava nova campanha e evento Outbox no **PostgreSQL** (Command Store). Retorna `400 Bad Request` se payload inválido. |
| **2\. hemocentros** | `GET` | `/api/v1/campanhas?tipo_sanguineo=O-` | `200 OK` | **Leitura Direta (Query CQRS)** na view desnormalizada do **MongoDB** filtrada por tipo sanguíneo. |
| **3\. agendamentos** | `POST` | `/api/v1/agendamentos` | `202 Accepted` | Inicia a SAGA Orquestrada de agendamento. Retorna `409 Conflict` se slot esgotado ou doador já possuir agendamento ativo (RN09). |
| **3\. agendamentos** | `POST` | `/api/v1/agendamentos/{id}/cancelamento` | `200 OK` | Cancela agendamento confirmado, libera vaga no slot e publica evento de cancelamento no RabbitMQ. |
| **4\. comunicacao** | `GET` | `/api/v1/comunicacao/historico/{doadorId}` | `200 OK` | Consulta histórico auditável de notificações e lembretes enviados ao doador. |

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

      "href": "/api/v1/agendamentos",

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
