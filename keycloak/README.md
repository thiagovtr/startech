# StarTech — Keycloak IAM (OIDC / JWT RS256)

Serviço de gerenciamento de identidade e acesso (IAM) da plataforma **StarTech**, responsável pela autenticação OIDC e emissão de tokens JWT assinados com chave assimétrica RSA (`RS256`), conforme especificado no **ADR-005**.

---

## 1. Boas Práticas no `Dockerfile` Multi-Stage

O [Dockerfile](./Dockerfile) utiliza build em **dois estágios** sobre o Keycloak 26 (Quarkus):
1. **Stage 1 (`builder`):** Executa `/opt/keycloak/bin/kc.sh build` com `KC_DB=postgres` e `KC_HEALTH_ENABLED=true`. Isso pré-compila os índices e classes Quarkus do driver JDBC PostgreSQL em tempo de imagem, reduzindo o tempo de inicialização em ~60% e o consumo de memória RAM.
2. **Stage 2 (`runtime`):** Copia a distribuição otimizada, embute o arquivo declarativo [realm-export.json](./realm-export.json) em `/opt/keycloak/data/import/startech-realm.json`, restringe o heap da JVM (`-Xms128m -Xmx384m`), executa como usuário não-root (`USER 1000`) e expõe o healthcheck nativo na porta de gerenciamento `9000` (`/health/ready`).

---

## 2. Arquitetura de Segurança do Realm `startech`

### 2.1. Thin Token e Conformidade com a LGPD
Tokens JWT trafegam na borda HTTP codificados apenas em Base64URL (qualquer intermediário com acesso ao token consegue decodificar seu payload JSON). Por isso, adotamos o padrão **Thin Token**:
* O escopo customizado `startech-roles-thin` inclui **apenas** o identificador opaco do usuário (`sub`, UUID imutável) e os papéis de autorização (`realm_access.roles`).
* Dados clínicos ou pessoais sensíveis (CPF, tipo sanguíneo, histórico de inaptidão, nome completo, endereço ou e-mail) **jamais** são inseridos no token JWT. Os BFFs utilizam o `X-User-Id` (extraído do `sub` pelo API Gateway) para consultar os dados necessários internamente na rede privada.

### 2.2. Segregação por Client, Escopo (`scope`) e Audience (`aud`)
Existem dois clientes OIDC independentes com `fullScopeAllowed: false` (*Princípio do Menor Privilégio*):

| Client ID | Canal Alvo | Scope Padrão | Audience (`aud`) Injetado | Role Permitida (`scopeMappings`) |
| :--- | :--- | :--- | :--- | :--- |
| **`mobile`** | App Mobile do Doador | `startech-roles-thin`, `startech:mobile` | `bff-mobile` | Apenas `doador` |
| **`web`** | Painel Web do Hemocentro | `startech-roles-thin`, `startech:web` | `bff-web` | Apenas `operador` |

> **Defesa em profundidade na origem:** Como `fullScopeAllowed` está desativado (`false`) e cada client possui `scopeMappings` restrito ao seu respectivo papel, mesmo que um operador tente autenticar usando `client_id=mobile`, o token emitido pelo client `mobile` **não** conterá a role `operador` nem o audience `bff-web`.

---

## 3. Usuários Pré-configurados para Testes (Seed)

| Usuário | Senha | UUID (`sub`) | Role no Realm | Client Recomendado |
| :--- | :--- | :--- | :--- | :--- |
| `doador1` | `doador123` | `11111111-1111-1111-1111-111111111111` | `doador` | `mobile` |
| `operador1` | `operador123` | `22222222-2222-2222-2222-222222222222` | `operador` | `web` |

---

## 4. Como Obter e Inspecionar um Token JWT via Terminal

Com o Compose no ar (`docker compose up -d`), o Keycloak responde em `http://localhost:8089` (painel admin: `admin` / `admin`).

### Emitir token de Doador (`client_id=mobile`):
```bash
curl -s -X POST "http://localhost:8089/realms/startech/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=mobile" \
  -d "grant_type=password" \
  -d "username=doador1" \
  -d "password=doador123"
```

### Emitir token de Operador (`client_id=web`):
```bash
curl -s -X POST "http://localhost:8089/realms/startech/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=web" \
  -d "grant_type=password" \
  -d "username=operador1" \
  -d "password=operador123"
```
