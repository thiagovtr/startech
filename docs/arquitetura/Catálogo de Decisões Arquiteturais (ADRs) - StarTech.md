# **Architecture Decision Records (ADRs) — StarTech**

---

Este documento consolida os Registros de Decisão Arquitetural (**ADRs 001 a 005**) do projeto **StarTech**, documentando formalmente as escolhas de engenharia, o alinhamento ao protótipo oficial da equipe, a análise de trade-offs (*"Por que fizemos desta forma e não de outra?"*) e a conformidade integral com os requisitos da disciplina **GCC129 — Sistemas Distribuídos (UFLA 2026/2 — Parte 2: Arquitetura)**.

> * **Projeto:** StarTech — Plataforma Distribuída de Mobilização e Fidelização de Doadores de Sangue  
> * **Disciplina:** GCC129 — Sistemas Distribuídos (UFLA 2026/2)  
> * **Autores:** Diovani da Cruz, Ezequiel Dominguez, Matheus Freire Costa Pimenta, Thiago Vinícius  
> * **Data de Consolidação:** 2026-10-21

## **Índice Oficial de Decisões Arquiteturais**

| ADR | Título da Decisão | Status | Data | Componentes e Stack Envolvidos | Requisito GCC129   |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **ADR-001** | Decomposição em 4 Microsserviços de Domínio e Padronização de Stack em Java (Spring Boot) e Python (FastAPI) | Aceito | 2026-10-21 | doadores (Java), hemocentros (Python), agendamentos (Java), comunicacao (Python) \+ IA com RAG (Parte 4\) | Decomposição em Microsserviços (Item 4.1) |
| **ADR-002** | Adoção de SAGA Orquestrada no Serviço agendamentos Integrada via RabbitMQ | Aceito | 2026-10-21 | agendamentos (Orquestrador Java), doadores (Java), comunicacao (Python) e RabbitMQ | Padrão SAGA Distribuído (Item 4.6) |
| **ADR-003** | Database per Service e Prevenção de Dual-Write com Transactional Outbox Polling e RabbitMQ | Aceito | 2026-10-21 | PostgreSQL (todos os serviços), MongoDB (hemocentros) e RabbitMQ | Database per Service & Outbox (Item 4.5) |
| **ADR-004** | Aplicação do Padrão CQRS no Serviço hemocentros (PostgreSQL Command/Outbox \+ RabbitMQ \+ MongoDB Query View) | Aceito | 2026-10-21 | hemocentros (Python FastAPI \+ PostgreSQL \+ RabbitMQ \+ MongoDB) | Padrão CQRS (Item 4.7) |
| **ADR-005** | Adoção de Keycloak para Auth, API Gateway e 2 BFFs em Python (FastAPI) para Clientes React | Aceito | 2026-10-21 | Keycloak, API Gateway, BFF Mobile (FastAPI), BFF Web (FastAPI) e Frontends em React | Gateway & BFF (Itens 4.3 e 4.4) |

# ---

**ADR-001: Decomposição em 4 Microsserviços de Domínio e Padronização de Stack em Java (Spring Boot) e Python (FastAPI)**

> * ---

>   **Status:** Aceito  
> * **Data:** 2026-10-21  
> * **Autores:** Diovani da Cruz, Ezequiel Dominguez, Matheus Freire Costa Pimenta, Thiago Vinícius  
> * **Contexto da Disciplina:** GCC129 — Sistemas Distribuídos (Parte 2 — Arquitetura, Seção 4.1)  
> * **Microsserviço(s) Afetado(s):** Sistema Global (doadores, hemocentros, agendamentos, comunicacao, BFF Mobile, BFF Web e módulo futuro IA com RAG)

## **1\. Contexto e Problema**

A StarTech atua no ecossistema de hemoterapia brasileiro com a missão de manter uma mobilização contínua e direcionada de doadores de sangue, reduzindo a volatilidade dos estoques públicos e conveniados (Portaria de Consolidação MS nº 5/2017 e alertas recorrentes de estoques críticos, como o da Fundação Hemominas em agosto de 2026).  
O sistema precisa lidar com fluxos operacionais com características arquiteturais heterogêneas:

> 1. **Picos intensos de leitura pública filtrada por tipo sanguíneo:** Divulgação de alertas de sangue O- em nível crítico dispara milhares de consultas simultâneas de campanhas ativas (GET hemocentros/api/v1/campanhas?tipo\_sanguineo=O-).  
> 2. **Alta concorrência com consistência estrita de recursos finitos:** A reserva de horários em postos de coleta (slots no serviço agendamentos) demanda concorrência controlada para evitar *overbooking* de cadeiras de atendimento.  
> 3. **Privacidade e regras biológicas estritas:** Dados cadastrais, tipo sanguíneo e intervalos biológicos mínimos (60 dias para homens, 90 dias para mulheres no serviço doadores) exigem integridade relacional sob a LGPD (Lei nº 13.709/2018).  
> 4. **Comunicação assíncrona orientada a eventos:** Notificações de campanhas e confirmações/lembretes de agendamento (no serviço comunicacao) dependem de processamento desacoplado via **Fila Message Broker RabbitMQ**.

A disciplina GCC129 (Seção 4.1) exige a decomposição em **ao menos 4 microsserviços de domínio independentes**, com justificativa formal de suas fronteiras e semântica de comunicação. Além disso, a equipe definiu como diretriz de engenharia a **padronização da stack de backend exclusivamente em Java (Spring Boot) e Python (FastAPI)**, eliminando linguagens adicionais (como Go e Node.js/TypeScript) para maximizar a produtividade e o domínio técnico do time.

## **2\. Forças e Critérios de Decisão (Drivers Arquiteturais)**

> * **Fidelidade ao Protótipo Arquitetural:** Refletir fielmente os serviços desenhados pela equipe (doadores, hemocentros, agendamentos, comunicacao, além do Keycloak, API Gateway, BFF Mobile, BFF Web e a extensão IA com RAG da Parte 4).  
> * **Simplicidade Cognitiva e Domínio da Stack:** Utilizar exclusivamente **Java (Spring Boot)** e **Python (FastAPI)** no backend, e **React** no frontend (Mobile e Web).  
> * **Escalabilidade Assimétrica e Isolamento de Falhas:** Capacidade de escalar a leitura de campanhas no serviço hemocentros (via CQRS com MongoDB) sem afetar o banco relacional de agendamentos ou doadores.  
> * **Coesão de Bounded Contexts vs. Microsserviços Físicos:** Evitar nano-serviços excessivos que introduzam chamadas RPC desnecessárias em validações biológicas atômicas.

## **3\. Alternativas Consideradas**

### **Opção 1: 4 Microsserviços de Domínio em Java (Spring Boot) e Python (FastAPI) com Identidade no Keycloak (Opção Escolhida)**

> * **Descrição Técnica:** O domínio é particionado em **4 microsserviços de domínio independentes** para a Parte 2 (além da camada de borda e da extensão de IA da Parte 4):  
  1. **doadores (Donor Service — Java 21 / Spring Boot 3 \+ PostgreSQL):** Consolida os contextos de *Doadores & Contas* e *Fidelização & Histórico*. Gerencia dados cadastrais, tipo sanguíneo (O-, A+, etc.) e o motor de cálculo dos ciclos de elegibilidade biológica da Portaria MS nº 5/2017 (RN01, RN03);  
  2. **hemocentros (Campaign & Need Service — Python 3.12 / FastAPI \+ PostgreSQL & MongoDB):** Gerencia hemocentros, publicação de campanhas e alertas de estoque com arquitetura **CQRS** (grava Command/Outbox no PostgreSQL, publica no RabbitMQ e atualiza a *view* de leitura direta no MongoDB);  
  3. **agendamentos (Appointment Service — Java 21 / Spring Boot 3 \+ PostgreSQL):** Gerencia grades horárias, capacidade física por slot e atua como **Orquestrador da SAGA** de agendamento;  
  4. **comunicacao (Communication Service — Python 3.12 / FastAPI \+ PostgreSQL):** Consome eventos do **RabbitMQ** para disparar notificações (Push, E-mail, SMS) e gerenciar lembretes pré-doação (D-1) e de fim de quarentena (D-7/D-0).  
  * **Camada de Borda e Identidade:** **Keycloak** (com banco próprio para gestão de usuários, permissões e emissão de JWT), **API Gateway** (validação de JWT) e **2 BFFs (BFF Mobile e BFF Web)** em **Python (FastAPI)**.  
  * **Extensão Parte 4:** Serviço **IA com RAG** (Python FastAPI \+ LangChain) conectado ao **VectorDB**, consumido pelo BFF Mobile.  
> * **Vantagens (Prós):**  
  * **Stack 100% dominada pela equipe:** Java/Spring Boot garante robustez transacional e tipagem forte nos serviços relacionais críticos (doadores e agendamentos), enquanto Python/FastAPI entrega alta produtividade assíncrona nos BFFs, no CQRS (hemocentros), na mensageria (comunicacao) e na futura IA (IA com RAG);  
  * **Eficiência na RN01:** Consolidar perfil do doador e ciclo de elegibilidade em doadores evita chamadas de rede extras para obter SexoBiologico e DataNascimento durante a SAGA;  
  * **Desacoplamento de Auth:** O Keycloak assume toda a complexidade de login, sessões e OIDC (/realms/login/clientId=mobile e web).  
> * **Desvantagens (Contras / Trade-offs aceitos):**  
  * O serviço doadores exige organização modular interna limpa (pacotes profile e eligibility e tabelas separadas donors e eligibility\_cycles).

### **Opção 2: Poliglotismo Extremo (Go \+ Node.js/TypeScript \+ Java \+ Python)**

> * **Descrição Técnica:** Utilizar 4 linguagens diferentes para os 4 microsserviços.  
> * **Desvantagens (Contras):** Elevada sobrecarga cognitiva para manter 4 toolchains, gerenciadores de pacotes, linters e imagens Docker distintas nas Partes 3 e 4\.  
> * **Motivo do Descarte:** Complexidade acidental desnecessária sem ganho arquitetural prático frente à dupla Java \+ Python.

### **Opção 3: Monolito Modular**

> * **Motivo do Descarte:** Gargalo de escalabilidade sob picos de campanhas e não atendimento ao requisito mínimo de 4 microsserviços independentes (Seção 4.1).

## **4\. Decisão Tomada e Justificativa Técnica**

> *Decidimos adotar a Opção 1: Decomposição do sistema nos 4 microsserviços de domínio independentes (doadores, hemocentros, agendamentos e comunicacao), padronizando toda a stack de backend exclusivamente em Java (Spring Boot) e Python (FastAPI), frontend em React (Mobile e Web), autenticação centralizada no Keycloak e mensageria no RabbitMQ.*

> 1. **Por que eliminamos Go e Node.js e padronizamos em Java (Spring Boot) e Python (FastAPI)?**  
>    Em engenharia de sistemas distribuídos reais, o poliglotismo irrestrito aumenta o custo operacional de build, observabilidade e manutenção. Java (Spring Boot) e Python (FastAPI) cobrem todos os requisitos do projeto: Spring Boot oferece maturidade para transações ACID e controle de concorrência JPA/Hibernate (doadores e agendamentos), enquanto FastAPI oferece I/O assíncrono leve para os BFFs, integração nativa com MongoDB/RabbitMQ (hemocentros e comunicacao) e suporte direto a LangChain/RAG para a Parte 4 (IA com RAG).  
> 2. **Por que consolidamos Doadores e Fidelização no serviço doadores?**  
>    A fórmula legal da Portaria MS nº 5/2017 (RN01) (DataMinimaProximaDoacao \= DataUltimaDoacao \+ Delta\_sexo) exige o SexoBiologico (60 dias para homens, 90 dias para mulheres) e a DataNascimento (16 a 69 anos). Manter esses dados juntos no PostgreSQL de doadores permite validar a elegibilidade em uma única consulta local durante a SAGA.  
> 3. **Por que delegar a Autenticação ao Keycloak?**  
>    O **Keycloak** gerencia usuários em banco próprio, concede permissões e emite tokens JWT (/realms/login/clientId=mobile e clientId=web). Isso evita reimplementar mecanismos de segurança dentro do serviço doadores e permite que o **API Gateway** valide o JWT na borda antes de a requisição chegar aos BFFs.

## **5\. Consequências e Impactos**

> * **Impactos Positivos:** Produtividade elevada nas Partes 3 e 4 com apenas duas linguagens de backend (Java e Python) e uma biblioteca de frontend (React); fronteiras de domínio claras e desacopladas para os 4 microsserviços obrigatórios.  
> * **Impactos Negativos e Custos Aceitos:** Necessidade de configurar limites de memória (-Xmx256m) nos dois containers Java Spring Boot (doadores e agendamentos) no Docker Compose da Parte 3\.

## **6\. Referências**

> 1. **NEWMAN, Sam.** *Building Microservices: Designing Fine-Grained Systems*. 2\. ed. O'Reilly Media, 2021\.  
> 2. **EVANS, Eric.** *Domain-Driven Design: Tackling Complexity in the Heart of Software*. Addison-Wesley, 2003\.  
> 3. **BRASIL. Ministério da Saúde.** *Portaria de Consolidação nº 5/2017*. Anexo IV: Doação de Sangue e Hemoterapia. Brasília, 2017\.

# ---

**ADR-002: Adoção de SAGA Orquestrada no Serviço agendamentos Integrada via RabbitMQ**

> * ---

>   **Status:** Aceito  
> * **Data:** 2026-10-21  
> * **Autores:** Diovani da Cruz, Ezequiel Dominguez, Matheus Freire Costa Pimenta, Thiago Vinícius  
> * **Contexto da Disciplina:** GCC129 — Sistemas Distribuídos (Parte 2 — Arquitetura, Seção 4.6)  
> * **Microsserviço(s) Afetado(s):** agendamentos (Java Spring Boot — Orquestrador), doadores (Java Spring Boot), comunicacao (Python FastAPI) e RabbitMQ

## **1\. Contexto e Problema**

O processo de agendamento de uma doação de sangue no ecossistema StarTech exige mutações coordenadas em **3 microsserviços independentes**, cada qual com seu próprio banco PostgreSQL isolado (*Database per Service*):

> 1. **Reserva de Vaga no Posto (agendamentos — Java Spring Boot):** Bloqueio provisório de uma cadeira no slot de horário escolhido para evitar *overbooking*;  
> 2. **Validação e Bloqueio de Intervalo Biológico (doadores — Java Spring Boot):** Verificação de conformidade com a Portaria de Consolidação MS nº 5/2017 (RN01: intervalo mínimo de 60 dias para homens e 90 dias para mulheres, teto anual de 4/3 doações e ausência de impedimentos temporários ativos) e criação de trava temporal no ciclo do doador;  
> 3. **Programação de Lembrete e Confirmação (comunicacao — Python FastAPI via RabbitMQ):** Registro do lembrete pré-doação (D-1) no banco de dados de comunicacao e disparo imediato da confirmação de agendamento ao doador.

A disciplina GCC129 (Seção 4.6) exige a escolha formal e justificada entre **SAGA Orquestrada** ou **Coreografada**, a definição exaustiva de todas as transações compensatórias e a modelagem para o caminho feliz e para cenário de falha com compensação efetiva.

## **2\. Forças e Critérios de Decisão (Drivers Arquiteturais)**

> * **Integração Harmônica via RabbitMQ:** Conectar o serviço agendamentos aos serviços doadores e comunicacao aproveitando o Message Broker RabbitMQ da arquitetura.  
> * **Rastreabilidade e Visibilidade do Fluxo:** Em saúde pública, os operadores e o próprio doador precisam saber claramente se o agendamento falhou por inaptidão biológica de intervalo (RN01) ou por erro técnico.  
> * **Resiliência a Quedas (*Crash Recovery*):** O estado da SAGA deve ser persistido no PostgreSQL do serviço agendamentos (saga\_execution\_state).  
> * **Execução Garantida de Compensações:** Caso a Etapa 3 falhe, o sistema deve desfazer a trava temporal em doadores e liberar a cadeira em agendamentos de forma idempotente.  
> * **Prevenção de Condição de Corrida (RN09):** Impedir que o mesmo doador abra dois agendamentos ativos simultâneos.

## **3\. Alternativas Consideradas**

### **Opção 1: SAGA Orquestrada Coordenada pelo Serviço agendamentos (Java Spring Boot) com RabbitMQ (Opção Escolhida)**

> * **Descrição Técnica:** O serviço agendamentos (Java / Spring Boot) atua como o coordenador central (*Saga Orchestrator*):  
  * **Passo 1 (Local em agendamentos):** Persiste o início da SAGA na tabela saga\_execution\_state e reserva provisoriamente a vaga no slot (status \= CRIADO\_PROVISORIO);  
  * **Passo 2 (agendamentos → doadores):** Valida a elegibilidade biológica (RN01) e aplica trava temporal no PostgreSQL de doadores usando chave de idempotência (Idempotency-Key: saga-{sagaId}-step2);  
  * **Passo 3 (agendamentos → RabbitMQ → comunicacao):** Publica comando via Transactional Outbox para a **Fila Message Broker RabbitMQ**, consumido pelo serviço comunicacao (Python FastAPI) para agendar o lembrete D-1 e disparar a confirmação;  
  * Em caso de falha no Passo 2 ou no Passo 3, o orquestrador em agendamentos dispara sequencialmente as transações compensatórias em ordem reversa, com retentativas (*Exponential Backoff*) e Dead Letter Queue (saga.compensations.dlq) no RabbitMQ.  
> * **Vantagens (Prós):** Máquina de estados centralizada e auditável no Spring Boot; alta clareza para demonstrar o rollback distribuído ao vivo na Parte 4\.  
> * **Desvantagens (Contras / Trade-offs aceitos):** O serviço agendamentos gerencia a tabela saga\_execution\_state e a lógica de coordenação.

### **Opção 2: SAGA Coreografada Pura via Eventos Descentralizados**

> * **Desvantagens (Contras):** Espalha a lógica de controle e rollback entre 3 serviços diferentes; dificulta a inspeção centralizada do estado da transação.  
> * **Motivo do Descarte:** Menor rastreabilidade e maior risco de acoplamento implícito de eventos.

### **Opção 3: Two-Phase Commit (2PC / XA)**

> * **Motivo do Descarte:** Antipadrão bloqueante que retém locks entre bancos distintos e degrada a disponibilidade.

## **4\. Decisão Tomada**

*Decidimos adotar a Opção 1: SAGA Orquestrada tendo o serviço agendamentos (Java Spring Boot) como orquestrador formal, coordenando agendamentos (Passo 1), doadores (Passo 2\) e comunicacao via RabbitMQ (Passo 3), com persistência de estado na tabela saga\_execution\_state e compensações idempotentes.*

## **5\. Especificação Técnica Detalhada da SAGA**

### **5.1 Tabela de Persistência de Estado (saga\_execution\_state) e Índice Único (RN09)**

No PostgreSQL do serviço agendamentos:

`CREATE TABLE saga_execution_state (`  
    `saga_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),`  
    `agendamento_id VARCHAR(64) NOT NULL,`  
    `doador_id VARCHAR(64) NOT NULL,`  
    `slot_id VARCHAR(64) NOT NULL,`  
    `current_step VARCHAR(32) NOT NULL,`  
    `status VARCHAR(32) NOT NULL, -- STARTED, SLOT_RESERVED, DONOR_VALIDATED, CONFIRMED, COMPENSATING, COMPENSATED`  
    `payload JSONB NOT NULL,`  
    `retry_count INT DEFAULT 0,`  
    `max_retries INT DEFAULT 5,`  
    `error_detail TEXT,`  
    `created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,`  
    `updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP`  
`);`

`-- Prevenção física de agendamento duplo ativo para o mesmo doador (RN09)`  
`CREATE UNIQUE INDEX idx_unico_agendamento_ativo`   
`ON agendamentos(doador_id)`   
`WHERE status IN ('CRIADO_PROVISORIO', 'CONFIRMADO');`

### **5.2 Matriz Completa de Transações Positivas e Compensatórias**

| Passo | Microsserviço | Ação Positiva (*Forward Action*) | Transação Compensatória (*Compensating Action*) | Garantia de Idempotência   |
| :---- | :---- | :---- | :---- | :---- |
| **1** | **agendamentos** (Java Spring Boot) | ReservarVagaProvisoria(slotId, doadorId): incrementa vagas\_ocupadas no slot com lock otimista e cria registro CRIADO\_PROVISORIO. | LiberarVagaProvisoria(slotId, agendamentoId): decrementa vagas\_ocupadas no slot e marca status como CANCELADO\_COMPENSACAO\_SAGA. | Transação ACID local por saga\_id |
| **2** | **doadores** (Java Spring Boot) | ValidarEBloquearIntervalo(doadorId, dataSlot): valida intervalo de 60/90 dias (RN01) e quarentenas; grava trava temporal vinculada ao agendamentoId. | LiberarTravaTemporal(doadorId, agendamentoId): remove a trava temporal na tabela eligibility\_cycles, liberando o doador. | Idempotency-Key: saga-{sagaId}-step2 |
| **3** | **comunicacao** (Python FastAPI via RabbitMQ) | ProgramarLembreteEConfirmar(agendamentoId, doadorId): consome comando do RabbitMQ, grava lembrete D-1 no PostgreSQL de comunicacao e dispara Push/E-mail. | CancelarLembreteAgendado(agendamentoId): cancela o lembrete D-1 no banco de comunicacao. | message\_id \= saga-{sagaId}-step3 na tabela processed\_events |

### **5.3 Protocolo de Tratamento de Falha na Compensação**

Se a chamada compensatória para doadores ou comunicacao falhar por oscilação de rede:

> 1. O orquestrador mantém status \= 'COMPENSATING' na tabela saga\_execution\_state;  
> 2. Reexecuta a compensação com **Exponential Backoff \+ Jitter** (T \= 2^retry \* 500ms);  
> 3. Graças à chave de idempotência, reenvios nunca causam efeitos colaterais duplicados;  
> 4. Caso exceda 5 tentativas, envia para a Dead Letter Queue (saga.compensations.dlq) no **RabbitMQ**.

## **6\. Referências**

> 1. **RICHARDSON, Chris.** *Microservices Patterns: With examples in Java*. Manning Publications, 2018\. (Capítulo 4: Managing transactions with sagas).  
> 2. **KLEPPMANN, Martin.** *Designing Data-Intensive Applications*. O'Reilly Media, 2017\.  
> 3. **GARCIA-MOLINA, Hector; SALEM, Kenneth.** *Sagas*. In: ACM SIGMOD Record, v. 16, n. 3, p. 249-259, 1987\.

# ---

**ADR-003: Database per Service e Prevenção de Dual-Write com Transactional Outbox Polling e RabbitMQ**

> * ---

>   **Status:** Aceito  
> * **Data:** 2026-10-21  
> * **Autores:** Diovani da Cruz, Ezequiel Dominguez, Matheus Freire Costa Pimenta, Thiago Vinícius  
> * **Contexto da Disciplina:** GCC129 — Sistemas Distribuídos (Parte 2 — Arquitetura, Seção 4.5)  
> * **Microsserviço(s) Afetado(s):** Todos os microsserviços (doadores, hemocentros, agendamentos, comunicacao) e RabbitMQ

## **1\. Contexto e Problema**

Em conformidade com as boas práticas de microsserviços e os requisitos de GCC129 (Seção 4.5), cada serviço de domínio mantém uma base de persistência completamente isolada (*Database per Service*), sem compartilhamento direto de tabelas:

> * Os 4 serviços de domínio (doadores, hemocentros, agendamentos, comunicacao) utilizam **PostgreSQL** como banco transacional para gravação de comandos (*Write / Command*);  
> * O serviço hemocentros possui adicionalmente um banco **MongoDB** dedicado à *view* de leitura direta (*Query CQRS*), sincronizado via **Fila Message Broker RabbitMQ**;  
> * O módulo IA com RAG (previsto para a Parte 4\) utiliza um **VectorDB** isolado.

Sempre que um serviço precisa gravar no seu **PostgreSQL** e publicar uma mensagem no **RabbitMQ** (ex.: hemocentros publicando campanha.criada para atualizar o MongoDB, ou agendamentos publicando comandos/eventos para comunicacao), surge o risco clássico de **Dual-Write**:

> 1. Se o PostgreSQL fizer COMMIT e o processo cair ou a rede com o RabbitMQ falhar antes do envio da mensagem, **o evento é perdido para sempre** (a *view* do MongoDB em hemocentros nunca seria atualizada e o doador nunca seria notificado por comunicacao);  
> 2. Se a mensagem for publicada no RabbitMQ antes do COMMIT no PostgreSQL e o banco sofrer ROLLBACK, **um evento fantasma terá sido disparado**.

## **2\. Forças e Critérios de Decisão (Drivers Arquiteturais)**

> * **Atomicidade Garantida:** Impossibilidade de divergência entre o estado persistido no PostgreSQL e os eventos publicados no RabbitMQ.  
> * **Simplicidade Operacional e Baixo Consumo de RAM:** Evitar infraestruturas pesadas como Apache Kafka \+ ZooKeeper \+ Debezium Connect (+1.5 GB de RAM), adotando o **RabbitMQ** com **Transactional Outbox Polling** nativo em SQL (SELECT ... FOR UPDATE SKIP LOCKED).  
> * **Unificação do Outbox no PostgreSQL:** Como o lado de escrita (*Command*) de todos os serviços — inclusive do serviço hemocentros — reside no PostgreSQL, o mecanismo de Outbox é 100% relacional, simples e uniforme em toda a plataforma.

## **3\. Alternativas Consideradas**

### **Opção 1: Database per Service (PostgreSQL \+ MongoDB) com Transactional Outbox Polling para RabbitMQ (Opção Escolhida)**

> * **Descrição Técnica:**  
  * Cada serviço possui seu banco **PostgreSQL** independente (e o serviço hemocentros possui também o **MongoDB** para leitura CQRS);  
  * Toda operação de escrita grava a entidade de negócio e um registro na tabela outbox\_events **dentro da mesma transação ACID do PostgreSQL** (Grava Command / Outbox);  
  * Um worker leve de *Outbox Polling* embutido no próprio serviço executa periodicamente SELECT ... FROM outbox\_events WHERE published \= FALSE ORDER BY created\_at ASC LIMIT 50 FOR UPDATE SKIP LOCKED, publica na **Fila Message Broker RabbitMQ** com *Publisher Confirms* e marca published \= TRUE;  
  * Os consumidores no RabbitMQ (hemocentros atualizando o MongoDB e comunicacao disparando notificações) garantem processamento **idempotente** (upsert por \_id no MongoDB e tabela processed\_events no PostgreSQL).  
> * **Vantagens (Prós):** Eliminação matemática do risco de Dual-Write com complexidade mínima; não exige containers extras de CDC (Debezium) nem Multi-Document Transactions no MongoDB; tolerância total a quedas temporárias do RabbitMQ.  
> * **Desvantagens (Contras / Trade-offs aceitos):** Latência de polling de \~200ms a 500ms e necessidade de garantir consumidores idempotentes (*At-Least-Once delivery*).

### **Opção 2: Apache Kafka \+ Debezium Connect CDC**

> * **Desvantagens (Contras):** Consumo elevado de memória RAM e complexidade de configuração de conectores Kafka Connect para um projeto que já utiliza RabbitMQ.  
> * **Motivo do Descarte:** Sobrecarga de infraestrutura desnecessária frente ao RabbitMQ \+ Outbox Polling.

### **Opção 3: Publicação Direta Dupla no Código (*Direct Dual-Write*) ou Banco Compartilhado**

> * **Motivo do Descarte:** Risco de perda silenciosa de eventos e violação direta do isolamento de dados (Seção 4.5).

## **4\. Decisão Tomada**

*Decidimos adotar a Opção 1: Arquitetura Database per Service (PostgreSQL para doadores, agendamentos, comunicacao e escrita de hemocentros; MongoDB para leitura CQRS de hemocentros), prevenindo Dual-Write através do padrão Transactional Outbox no PostgreSQL aliado a um worker leve de Outbox Polling (FOR UPDATE SKIP LOCKED) publicando na Fila Message Broker RabbitMQ.*

## **5\. Especificação Técnica da Implementação**

### **5.1 Esquema da Tabela outbox\_events no PostgreSQL**

Presente nos bancos PostgreSQL de hemocentros, agendamentos e doadores:

`CREATE TABLE outbox_events (`  
    `id UUID PRIMARY KEY DEFAULT gen_random_uuid(),`  
    `aggregate_type VARCHAR(64) NOT NULL,`  
    `aggregate_id VARCHAR(64) NOT NULL,`  
    `routing_key VARCHAR(128) NOT NULL,`  
    `payload JSONB NOT NULL,`  
    `created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,`  
    `published BOOLEAN DEFAULT FALSE,`  
    `published_at TIMESTAMP WITH TIME ZONE`  
`);`

`CREATE INDEX idx_outbox_unpublished ON outbox_events(created_at) WHERE published = FALSE;`

### **5.2 Exemplo de Transação Atômica \+ Outbox Polling Worker**

**1\. Na transação de negócio (ex.: POST api/v1/campanhas no serviço hemocentros):**

`BEGIN;`  
  `INSERT INTO campaigns (id, titulo, tipo_sanguineo, urgencia, created_at)`  
  `VALUES ('camp-lavras-2026', 'Doação Urgente O-', 'O-', 'CRITICO', NOW());`

  `INSERT INTO outbox_events (id, aggregate_type, aggregate_id, routing_key, payload)`  
  `VALUES (`  
    `gen_random_uuid(),`  
    `'Campanha',`  
    `'camp-lavras-2026',`  
    `'hemocentros.campanha.criada',`  
    `'{"id": "camp-lavras-2026", "titulo": "Doação Urgente O-", "tipo_sanguineo": "O-", "urgencia": "CRITICO"}'::jsonb`  
  `);`  
`COMMIT;`

**2\. No Worker de Outbox Polling (publicando no RabbitMQ):**

`BEGIN;`  
  `SELECT id, routing_key, payload`  
  `FROM outbox_events`  
  `WHERE published = FALSE`  
  `ORDER BY created_at ASC`  
  `LIMIT 50`  
  `FOR UPDATE SKIP LOCKED;`  
  `-- Publica cada evento na exchange do RabbitMQ com confirmação (ACK)`  
  `UPDATE outbox_events`  
  `SET published = TRUE, published_at = NOW()`  
  `WHERE id IN (...);`  
`COMMIT;`

### **5.3 Comportamento durante Indisponibilidade Temporária do RabbitMQ**

Caso o container do **RabbitMQ** fique inacessível por alguns minutos:

> 1. **Zero perda de transações:** O serviço hemocentros continua aceitando POST api/v1/campanhas e o serviço agendamentos continua recebendo solicitações, pois o COMMIT ocorre localmente no PostgreSQL;  
> 2. **Drenagem automática:** Os eventos permanecem com published \= FALSE na tabela outbox\_events. Assim que o RabbitMQ restabelece a conexão, o worker drena a fila na ordem exata de created\_at ASC, atualizando a *view* de leitura do MongoDB e disparando as notificações pendentes.

## **6\. Referências**

> 1. **RICHARDSON, Chris.** *Microservices Patterns: With examples in Java*. Manning Publications, 2018\. (Transactional Outbox and Polling Publisher Patterns).  
> 2. **KLEPPMANN, Martin.** *Designing Data-Intensive Applications*. O'Reilly Media, 2017\.  
> 3. **RABBITMQ.** *Publisher Confirms and Consumer Acknowledgements Documentation*. Broadcom / RabbitMQ, 2026\.

# ---

**ADR-004: Aplicação do Padrão CQRS no Serviço hemocentros (PostgreSQL Command/Outbox \+ RabbitMQ \+ MongoDB Query View)**

> * ---

>   **Status:** Aceito  
> * **Data:** 2026-10-21  
> * **Autores:** Diovani da Cruz, Ezequiel Dominguez, Matheus Freire Costa Pimenta, Thiago Vinícius  
> * **Contexto da Disciplina:** GCC129 — Sistemas Distribuídos (Parte 2 — Arquitetura, Seção 4.7)  
> * **Microsserviço(s) Afetado(s):** hemocentros (Campaign & Need Service — Python FastAPI), RabbitMQ, BFF Mobile e BFF Web

## **1\. Contexto e Problema**

O microsserviço hemocentros (Campaign & Need Service, construído em **Python com FastAPI**) centraliza o cadastro institucional de hemocentros, a publicação de campanhas de doação e os alertas de necessidades críticas por tipo sanguíneo.  
A dinâmica operacional desse serviço apresenta uma **assimetria extrema entre escrita e leitura**:

> * **Escrita (Commands):** Executada pelos gestores dos hemocentros através do Painel Web React (POST /api/web/campanhas → POST /bff-web/campanhas → POST api/v1/campanhas). Ocorre em baixa frequência (dezenas de vezes por semana), mas exige consistência transacional ACID e garantia de publicação de eventos (Outbox);  
> * **Leitura (Queries):** Executada milhares de vezes por minuto sempre que doadores abrem o aplicativo móvel (GET /api/mobile/home → GET /bff-mobile/home → GET hemocentros/api/v1/campanhas?tipo\_sanguineo=O-), exigindo respostas ultrarrápidas filtradas por tipo sanguíneo sem bloquear a base relacional de escrita.

A disciplina GCC129 (Seção 4.7) exige a aplicação do padrão **CQRS (Command Query Responsibility Segregation)** em ao menos um serviço, com justificativa formal, definição dos modelos de escrita e leitura, estratégia de atualização e explicitação da defasagem aceitável (*eventual consistency*).

## **2\. Forças e Critérios de Decisão (Drivers Arquiteturais)**

> * **Segregação Física de Armazenamento:** No serviço hemocentros, a arquitetura CQRS separa dois bancos distintos: **PostgreSQL** (Grava Command / Outbox) e **MongoDB** (Leitura Direta (Query)), sincronizados pela **Fila Message Broker RabbitMQ** (Atualiza view de leitura).  
> * **Simplicidade do Outbox Relacional:** Gravar o comando e o registro de Outbox no PostgreSQL elimina qualquer necessidade de configurar transações multi-documento complexas no MongoDB.  
> * **Desempenho de Leitura Documental:** Consultar documentos JSON pré-formatados e indexados por tipo\_sanguineo diretamente no MongoDB dispensa JOINs relacionais e não exige uma camada extra de cache Redis.  
> * **Consistência Read-Your-Own-Writes (RYOW) para o Gestor Web:** Garantir que o operador do hemocentro veja imediatamente a campanha que acabou de publicar no painel React Web.

## **3\. Alternativas Consideradas**

### **Opção 1: CQRS Poliglota com PostgreSQL (Command/Outbox) → RabbitMQ → MongoDB (Query View) (Opção Escolhida)**

> * **Descrição Técnica:**  
  * **Command Store (PostgreSQL 16):** Quando o BFF Web envia POST api/v1/campanhas, o serviço hemocentros (Python FastAPI) grava os dados normalizados da campanha e o evento na tabela outbox\_events dentro da mesma transação ACID do PostgreSQL;  
  * **Sincronização Assíncrona (RabbitMQ):** O worker de Outbox Polling lê os eventos pendentes do PostgreSQL e publica na **Fila Message Broker RabbitMQ**, onde o consumidor de projeção atualiza a *view* de leitura no MongoDB (Atualiza view de leitura);  
  * **Query Store (MongoDB 7.0):** Quando o BFF Mobile solicita GET hemocentros/api/v1/campanhas?tipo\_sanguineo=O-, o serviço hemocentros realiza **Leitura Direta (Query)** na coleção desnormalizada do MongoDB;  
  * **Garantia Read-Your-Own-Writes (RYOW):** O comando POST api/v1/campanhas retorna 201 Created com o payload recém-gravado para atualização imediata da tela no React Web, e rotas administrativas de edição consultam o PostgreSQL canônico.  
> * **Vantagens (Prós):** Combina segurança transacional ACID no PostgreSQL (escrita \+ Outbox) com leitura documental rápida sem locks no MongoDB; elimina a necessidade de Redis adicional, reduzindo o número de containers no Docker Compose.  
> * **Desvantagens (Contras / Trade-offs aceitos):** Janela de consistência eventual de **1 a 3 segundos** até que uma nova campanha apareça na *view* de leitura do MongoDB.

### **Opção 2: Banco Único Relacional sem Segregação de Leitura e Escrita**

> * **Motivo do Descarte:** Contenção de conexões e locks sob picos de alertas críticos e não atendimento ao requisito obrigatório de CQRS (Seção 4.7).

### **Opção 3: MongoDB para Escrita e Redis para Leitura**

> * **Motivo do Descarte:** Exigiria configurar Replica Set para Multi-Document Transactions no MongoDB para suportar o Outbox e divergiria do protótipo oficial da equipe.

## **4\. Decisão Tomada**

*Decidimos adotar a Opção 1: Implementação do padrão CQRS no serviço hemocentros (Python FastAPI) utilizando PostgreSQL como Command Store (com Transactional Outbox), Fila Message Broker RabbitMQ como barramento de sincronização assíncrona e MongoDB como Query Store para leitura direta (GET hemocentros/api/v1/campanhas?tipo\_sanguineo=O-), admitindo uma defasagem eventual de 1 a 3 segundos no feed móvel.*

## **5\. Especificação Técnica e Fluxo de Sincronização CQRS**

> 1. **Gravação do Comando (PostgreSQL):** O BFF Web envia POST api/v1/campanhas ao Command Handler de hemocentros, que persiste a campanha e o registro em outbox\_events em transação ACID única e retorna 201 Created.  
> 2. **Publicação e Projeção Assíncrona (RabbitMQ → MongoDB):** O Outbox Polling Worker lê os eventos pendentes (SKIP LOCKED) e publica no RabbitMQ; o Projection Consumer realiza upsert idempotente do documento JSON na coleção campanhas\_view do MongoDB.  
> 3. **Defasagem Aceitável (*Eventual Consistency*):** A propagação assíncrona PostgreSQL → Outbox Worker → RabbitMQ → Consumer → MongoDB leva entre **1 e 3 segundos** (máximo aceitável de **5 segundos** sob carga intensa), sem impacto de negócio para os doadores no aplicativo móvel.  
> 4. **Prevenção de Violação de Read-Your-Own-Writes (RYOW) no Painel Web:** O operador que cadastra a campanha no Painel Web recebe o objeto criado na resposta do POST /bff-web/campanhas (201 Created) e visualiza os dados imediatamente na interface React, sem depender da leitura eventual do MongoDB.

## **6\. Referências**

> 1. **FOWLER, Martin.** *CQRS (Command Query Responsibility Segregation)*. MartinFowler.com, 2011\.  
> 2. **RICHARDSON, Chris.** *Microservices Patterns: With examples in Java*. Manning Publications, 2018\. (Capítulo 7: Designing queries with CQRS).  
> 3. **KLEPPMANN, Martin.** *Designing Data-Intensive Applications*. O'Reilly Media, 2017\.

# ---

**ADR-005: Adoção de Keycloak para Auth, API Gateway e 2 BFFs em Python (FastAPI) para Clientes React**

> * ---

>   **Status:** Aceito  
> * **Data:** 2026-10-21  
> * **Autores:** Diovani da Cruz, Ezequiel Dominguez, Matheus Freire Costa Pimenta, Thiago Vinícius  
> * **Contexto da Disciplina:** GCC129 — Sistemas Distribuídos (Parte 2 — Arquitetura, Seções 4.3 e 4.4)  
> * **Microsserviço(s) Afetado(s):** Keycloak, API Gateway, BFF Mobile (Python FastAPI), BFF Web (Python FastAPI) e Clientes Frontend em **React**

## **1\. Contexto e Problema**

A plataforma StarTech atende a dois clientes frontend construídos em **React**, mas com perfis de uso, permissões e requisitos de payload completamente distintos:

> 1. **App Mobile do Doador (React PWA / React Native):** Autentica no **Keycloak** via /realms/login/clientId=mobile e envia requisições GET /api/mobile/home passando o **token JWT**. Exige agregação rápida em *Single Roundtrip* combinando os dados do doador (GET doadores/api/v1/doadores/{123}) com as campanhas compatíveis com seu tipo sanguíneo (GET hemocentros/api/v1/campanhas?tipo\_sanguineo=O-), além de conexão futura com o serviço IA com RAG (Parte 4);  
> 2. **Painel Web do Hemocentro (React Desktop SPA):** Autentica no **Keycloak** via /realms/login/clientId=web e envia comandos POST /api/web/campanhas passando o **token JWT**. Exige interfaces administrativas ricas, publicação de campanhas (POST api/v1/campanhas no serviço hemocentros), controle de agendamentos por slot e relatórios de notificações.

A disciplina GCC129 (Seções 4.3 e 4.4) exige a definição clara do **API Gateway** (regras de roteamento, autenticação e rate limiting) e a implementação de **ao menos 2 BFFs distintos**, demonstrando como as respostas diferem para cada cliente.

## **2\. Forças e Critérios de Decisão (Drivers Arquiteturais)**

> * **Separação de Responsabilidades na Borda:** O Keycloak gerencia usuários com banco de dados próprio, concessão de permissões e sessões; o API Gateway valida o token JWT gerado pelo Keycloak; os BFFs (GET /bff-mobile/home e POST /bff-web/campanhas) recebem requisições já autenticadas.  
> * **Padronização de Stack em Python (FastAPI) para os BFFs:** Utilizar **Python (FastAPI com httpx.AsyncClient)** nos dois BFFs, aproveitando a leveza, tipagem com Pydantic e execução assíncrona não-bloqueante.  
> * **Resiliência e Degradação Graciosa (*Graceful Degradation*):** Garantir que uma oscilação em doadores não impeça o BFF Mobile de exibir campanhas ativas de hemocentros.

## **3\. Alternativas Consideradas**

### **Opção 1: Keycloak \+ API Gateway \+ 2 BFFs em Python (FastAPI) para Clientes React (Opção Escolhida)**

> * **Descrição Técnica:**  
  * **Keycloak:** Gerencia usuários em banco próprio, permissões e sessões para clientId=mobile e clientId=web, emitindo tokens JWT assinados com chave privada RSA (RS256);  
  * **API Gateway:** Valida a assinatura do token JWT gerado pelo Keycloak, aplica Rate Limiting e RBAC na borda, e roteia /api/mobile/\* → BFF Mobile (/bff-mobile/\*) e /api/web/\* → BFF Web (/bff-web/\*);  
  * **BFF Mobile (Python FastAPI):** Recebe GET /bff-mobile/home já autenticado pelo Gateway, consulta GET doadores/api/v1/doadores/{123} e GET hemocentros/api/v1/campanhas?tipo\_sanguineo=O- com httpx assíncrono, timeout de 800 ms e *Graceful Degradation*;  
  * **BFF Web (Python FastAPI):** Recebe POST /bff-web/campanhas já autenticado pelo Gateway, encaminha POST api/v1/campanhas ao serviço hemocentros e agrega visões gerenciais para a SPA React.  
> * **Vantagens (Prós):** Alinhado ao protótipo oficial da equipe e à padronização em Java e Python; BFFs e microsserviços ficam livres da lógica repetitiva de validação criptográfica de JWT; elimina *over-fetching* e múltiplos roundtrips no App Mobile.  
> * **Desvantagens (Contras / Trade-offs aceitos):** Manutenção de dois serviços FastAPI leves para os BFFs.

### **Opção 2: API Gateway Único sem BFFs (Clientes React chamando microsserviços diretamente)**

> * **Motivo do Descarte:** Obrigaria o App Mobile a fazer múltiplas chamadas sequenciais na rede móvel (primeiro buscar o doador para descobrir seu tipo sanguíneo O- e só depois buscar as campanhas O-), além de não atender ao requisito de 2 BFFs (Seção 4.4).

## **4\. Decisão Tomada**

*Decidimos adotar a Opção 1: Autenticação centralizada no Keycloak (/realms/login/clientId=mobile e clientId=web), validação de JWT e Rate Limiting no API Gateway, e 2 BFFs independentes desenvolvidos em Python (FastAPI) (BFF Mobile e BFF Web) servindo os frontends em React com payloads diferenciados e degradação graciosa.*

## **5\. Especificação de Roteamento, Segurança e Agregação Resiliente**

### **5.1 Fluxo de Autenticação e Roteamento (Keycloak → Gateway → BFFs)**

> 1. **Login no Keycloak:** O App Mobile (clientId=mobile) ou Painel Web (clientId=web) autentica no Keycloak e obtém o token JWT;  
> 2. **Validação no API Gateway:** O cliente chama GET /api/mobile/home ou POST /api/web/campanhas enviando Authorization: Bearer \<JWT\>. O API Gateway valida o token junto às chaves públicas do Keycloak, verifica se o clientId/role corresponde à rota solicitada (bloqueando com 403 Forbidden qualquer tentativa cruzada) e aplica *Header Stripping* injetando X-User-Id verificado;  
> 3. **Execução nos BFFs:** O Gateway encaminha GET /bff-mobile/home para o BFF Mobile e POST /bff-web/campanhas para o BFF Web.

### **5.2 Agregação com Degradação Graciosa no BFF Mobile (Python FastAPI)**

Ao receber GET /bff-mobile/home para o doador 123:

`async with httpx.AsyncClient(timeout=0.8) as client:`  
    `# 1. Consulta doadores/api/v1/doadores/123`  
    `try:`  
        `doador = (await client.get(f"http://doadores:8081/api/v1/doadores/{user_id}")).json()`  
        `tipo_sanguineo = doador.get("tipoSanguineo", "O-")`  
    `except Exception:`  
        `doador = {"id": user_id, "statusDegradado": True}`  
        `tipo_sanguineo = "O-"`

    `# 2. Consulta hemocentros/api/v1/campanhas?tipo_sanguineo=O- (Leitura Direta MongoDB)`  
    `campanhas = (await client.get(`  
        `"http://hemocentros:8000/api/v1/campanhas",`  
        `params={"tipo_sanguineo": tipo_sanguineo}`  
    `)).json()`

Se o serviço doadores estiver temporariamente indisponível, o BFF Mobile não falha com HTTP 500: ele aciona o fallback seguro e entrega normalmente a lista de campanhas do serviço hemocentros.

## **6\. Referências**

> 1. **NEWMAN, Sam.** *Backends For Frontends*. SamNewman.io, 2015\.  
> 2. **NYGARD, Michael T.** *Release It\!: Design and Deploy Production-Ready Software*. 2\. ed. Pragmatic Bookshelf, 2018\.  
> 3. **KEYCLOAK.** *Keycloak Documentation: Securing Applications and Services Guide (OIDC / JWT)*. 2026\.