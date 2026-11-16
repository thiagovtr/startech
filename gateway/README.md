# StarTech — API Gateway (Spring Cloud Gateway / Java 21)

Ponto único de entrada (*Single Point of Entry*) da plataforma **StarTech**, responsável por roteamento reativo (WebFlux / Netty), validação criptográfica de tokens JWT (`RS256`) emitidos pelo **Keycloak**, controle de acesso por papel e *audience* (RBAC), *Header Stripping* de identidade e *Rate Limiting* na borda (**ADR-005** / Seção 4.3).

---

## 1. Responsabilidades Arquiteturais na Borda

1. **Validação Criptográfica de JWT (`OAuth2 Resource Server`):**
   * Valida a assinatura RSA (`RS256`) e a expiração (`exp`) de cada token consultando o endpoint JWKS do Keycloak (`http://keycloak:8080/realms/startech/protocol/openid-connect/certs`).
   * Se o token estiver ausente, expirado ou adulterado, responde imediatamente com `401 Unauthorized` em formato **RFC 7807 (`application/problem+json`)**.
2. **Segregação Estrita de Canais (RBAC + Audience Check):**
   * `/api/mobile/**`: exige simultaneamente o papel `doador` (`realm_access.roles`) e o audience `bff-mobile` (`aud`).
   * `/api/web/**`: exige simultaneamente o papel `operador` (`realm_access.roles`) e o audience `bff-web` (`aud`).
   * Tentativas de acesso cruzado (ex.: doador chamando `/api/web/campanhas` ou operador chamando `/api/mobile/home`) são bloqueadas na borda com `403 Forbidden` (`urn:startech:error:acesso-negado`).
3. **Header Stripping e Propagação Segura de Identidade (`JwtHeaderEnrichmentFilter`):**
   * Remove qualquer cabeçalho `X-User-Id` ou `X-User-Roles` enviado maliciosamente pelo cliente externo.
   * Injeta na requisição interna encaminhada aos BFFs os valores confiáveis extraídos do JWT validado:
     * `X-User-Id`: claim `sub` (UUID imutável do usuário no Keycloak).
     * `X-User-Roles`: lista de papéis em `realm_access.roles` separada por vírgula.
     * `X-Correlation-Id`: preserva o identificador de correlação recebido ou gera um UUID v4 novo, devolvendo-o também na resposta HTTP.
4. **Roteamento e Reescrita de Caminhos (`RewritePath`):**
   * `/api/mobile/<rota>` ➔ `http://bff-mobile:8001/bff-mobile/<rota>`
   * `/api/web/<rota>` ➔ `http://bff-web:8002/bff-web/<rota>`
   * `/realms/<rota>` ➔ `http://keycloak:8080/realms/<rota>` (proxy reverso público de autenticação OIDC)
5. **Rate Limiting (`RateLimitGlobalFilter`):**
   * Algoritmo *Token Bucket* em memória por usuário autenticado (`X-User-Id`) ou IP de origem (`X-Forwarded-For`), retornando `429 Too Many Requests` (`urn:startech:error:rate-limit-excedido`) quando excedido.
6. **Timeouts Calibrados para Degradação Graciosa:**
   * `response-timeout: 6s` (superior ao teto de `3.8s` do `bff-mobile`, garantindo que respostas degradadas graciosamente nunca sejam cortadas pelo Gateway).

---

## 2. Boas Práticas no `Dockerfile` Multi-Stage

* **Stage 1 (`builder`):** `maven:3.9.9-eclipse-temurin-21-alpine` com cache da camada de dependências (`mvn dependency:go-offline`) separado da compilação do código-fonte.
* **Stage 2 (`runtime`):** `eclipse-temurin:21-jre-alpine` (apenas JRE, reduzindo a imagem final em mais de 50%), pacotes atualizados (`apk upgrade`), execução com usuário não-root (`app`, `uid 10001`), limite de memória da JVM (`-Xms128m -Xmx256m`) e `HEALTHCHECK` nativo em `/health`.
