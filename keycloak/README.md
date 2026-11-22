# StarTech — Keycloak IAM (OIDC / JWT RS256 + Tema Keycloakify)

Serviço de gerenciamento de identidade e acesso (IAM) da plataforma **StarTech**, responsável pela autenticação OIDC (Authorization Code + PKCE `S256`), auto-cadastro de doadores, tema customizado de login/cadastro e emissão de tokens JWT assinados com chave assimétrica RSA (`RS256`), conforme especificado no **ADR-005**.

---

## 1. Boas Práticas no `Dockerfile` Multi-Stage

O [Dockerfile](./Dockerfile) utiliza build em **três estágios** sobre o Keycloak 26 (Quarkus):
1. **Stage 1 (`theme-builder`):** Compila o tema React/TypeScript com **Keycloakify + Vite** (`keycloak/theme/`) e empacota o provedor `startech-theme.jar` sem levar Node.js, npm ou Maven para a imagem final.
2. **Stage 2 (`builder`):** Copia `startech-theme.jar` para `/opt/keycloak/providers/` e executa `/opt/keycloak/bin/kc.sh build` com `KC_DB=postgres` e `KC_HEALTH_ENABLED=true`, pré-compilando os índices Quarkus.
3. **Stage 3 (`runtime`):** Copia a distribuição otimizada, embute o arquivo declarativo [realm-export.json](./realm-export.json) em `/opt/keycloak/data/import/startech-realm.json`, restringe o heap da JVM (`-Xms128m -Xmx384m`), executa como usuário não-root (`USER 1000`) e expõe o healthcheck nativo na porta de gerenciamento `9000` (`/health/ready`).

---

## 2. Arquitetura de Segurança do Realm `startech`

### 2.1. Thin Token e Conformidade com a LGPD
Tokens JWT trafegam na borda HTTP codificados apenas em Base64URL. Por isso, adotamos o padrão **Thin Token**:
* O escopo customizado `startech-roles-thin` inclui **apenas** o identificador opaco do usuário (`sub`, UUID imutável) e os papéis de autorização (`realm_access.roles`).
* Dados clínicos ou pessoais sensíveis (CPF, tipo sanguíneo, histórico de inaptidão, nome completo ou e-mail) **jamais** são inseridos no token JWT.

### 2.2. Clients OIDC (Authorization Code + PKCE `S256`) e Segregação de Papéis
Todos os clients públicos exigem **PKCE `S256`** no fluxo interativo de login e têm `fullScopeAllowed: false` (*Princípio do Menor Privilégio*):

| Client ID | Canal Alvo | Redirect URIs Permitidas | Audience (`aud`) | Role Permitida (`scopeMappings`) |
| :--- | :--- | :--- | :--- | :--- |
| **`startech-mobile`** *(alias: `mobile`)* | App Mobile React Native / Expo | `exp://*`, `startech://*`, `http://localhost:*` | `bff-mobile` | Apenas `doador` |
| **`startech-web`** *(alias: `web`)* | Painel Web React + Vite | `http://localhost:5173/*`, `http://localhost:3000/*`, `http://localhost:8085/*` | `bff-web` | Apenas `operador` |

> **Auto-cadastro seguro:** `registrationAllowed` está habilitado em `pt-BR` e atribui automaticamente **apenas** o papel `doador` (`default-roles-startech`). Contas de `operador` continuam restritas ao provisionamento administrativo do hemocentro.

---

## 3. Tema Customizado (`keycloak/theme/`)

O tema **`startech`** foi construído com **Keycloakify (React + TypeScript + Vite)** reutilizando a mesma paleta e raios de borda do app mobile (`#2563EB`, `#1D4ED8`, `#DBEAFE`, `#F6F8FC`, `#FFFFFF`, `#1F2937`, `#6B7280`):
* **`Login.tsx`**: tela de login em português com botão de mostrar/ocultar senha e link para criar conta.
* **`Register.tsx`**: tela de cadastro de doador com validação por campo e retorno ao login.
* **`Template.tsx`**: cartão centralizado responsivo com a identidade visual da StarTech e alertas acessíveis.

---

## 4. Usuários Pré-configurados para Testes (Seed)

| Usuário | Senha | UUID (`sub`) | Role no Realm | Client Recomendado |
| :--- | :--- | :--- | :--- | :--- |
| `doador1` | `doador123` | `11111111-1111-1111-1111-111111111111` | `doador` | `startech-mobile` |
| `operador1` | `operador123` | `22222222-2222-2222-2222-222222222222` | `operador` | `startech-web` |

---

## 5. Como Testar Rapidamente

Com o Compose no ar (`docker compose up -d --build`), o Keycloak responde em `http://localhost:8089` (painel admin: `admin` / `admin`) e via proxy do Gateway em `http://localhost:8080/realms/startech/...`.

### Emitir token de Doador (`startech-mobile`):
```bash
curl -s -X POST "http://localhost:8080/realms/startech/protocol/openid-connect/token" \
  -d "client_id=startech-mobile" \
  -d "grant_type=password" \
  -d "username=doador1" \
  -d "password=doador123"
```

### Emitir token de Operador (`startech-web`):
```bash
curl -s -X POST "http://localhost:8080/realms/startech/protocol/openid-connect/token" \
  -d "client_id=startech-web" \
  -d "grant_type=password" \
  -d "username=operador1" \
  -d "password=operador123"
```
