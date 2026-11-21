# StarTech Mobile — Doador

Aplicativo multiplataforma desenvolvido com **React Native, Expo e TypeScript** para os doadores de sangue da StarTech, projeto acadêmico da disciplina GCC129 — Sistemas Distribuídos, da Universidade Federal de Lavras (UFLA).

O aplicativo permite acessar informações do doador, visualizar campanhas de doação, solicitar agendamentos, acompanhar o processamento das solicitações e utilizar um assistente de dúvidas.

O cliente se comunica com os serviços de negócio exclusivamente pelo **API Gateway**, utilizando o BFF Mobile. A autenticação é realizada pelo Keycloak, por meio do protocolo OpenID Connect (OIDC), com Authorization Code e PKCE.

**Issue relacionada:** [#15 — Cliente mobile (React Native) do doador](https://github.com/thiagovtr/startech/issues/15)

## 1. Tecnologias

- Expo SDK 58
- React Native e React
- TypeScript
- React Navigation
- `expo-auth-session`
- `expo-web-browser`
- `expo-crypto`
- `expo-secure-store`
- API `fetch`, por meio de um cliente HTTP reutilizável

O projeto utiliza componentes reutilizáveis, nomenclatura própria em português brasileiro (PT-BR) e identidade visual com predominância da cor azul.

## 2. Compatibilidade

O StarTech Mobile utiliza uma única base de código para dispositivos Android e iOS.

O desenvolvimento pode ser realizado em computadores com Windows, macOS ou Linux, respeitando as ferramentas e limitações de cada plataforma.

| Ambiente | Utilização |
|---|---|
| Windows | Desenvolvimento, execução do Expo e compilação Android com ambiente configurado |
| macOS | Desenvolvimento, execução do Expo e compilação Android/iOS com ambiente configurado |
| Linux | Desenvolvimento, execução do Expo e compilação Android com ambiente configurado |
| Android | Execução em dispositivo físico ou emulador |
| iOS | Execução em iPhone ou simulador iOS |

**Observações importantes:**

- Não é necessário desenvolver aplicativos separados para Android e iOS.
- A compilação nativa local para Android requer o Android SDK.
- A compilação nativa local para iOS requer macOS e Xcode.
- Em Windows ou Linux, builds iOS podem ser preparados por serviços de compilação na nuvem, respeitando os requisitos de assinatura da Apple.
- A compatibilidade completa ainda depende de validação funcional em ambas as plataformas.
- O painel web dos hemocentros é outro cliente do projeto e não faz parte deste aplicativo.

## 3. Pré-requisitos

Para instalar e executar o ambiente de desenvolvimento:

- Git.
- Node.js e npm compatíveis com a versão do Expo utilizada.
- VS Code ou outro editor de código.
- Dispositivo Android/iOS ou emulador compatível.
- Acesso à infraestrutura StarTech para testar as funcionalidades reais.

Para executar a infraestrutura distribuída, são necessários Docker e Docker Compose, conforme as instruções do README principal.

Para compilações nativas, também é necessário configurar as ferramentas correspondentes à plataforma escolhida.

## 4. Instalação

Clone o repositório StarTech e acesse a pasta do aplicativo:

```bash
cd mobile-doador
npm install
```

Crie o arquivo `.env` a partir de `.env.example`.

**Windows (PowerShell):**

```powershell
Copy-Item .env.example .env
```

**macOS ou Linux:**

```bash
cp .env.example .env
```

O arquivo `.env` contém as configurações locais de execução e não deve ser incluído nos commits.

## 5. Configuração do ambiente

Edite o arquivo `.env`:

```dotenv
EXPO_PUBLIC_API_URL=http://IP_DO_COMPUTADOR:8080
EXPO_PUBLIC_KEYCLOAK_URL=http://IP_DO_COMPUTADOR:8089
EXPO_PUBLIC_KEYCLOAK_CLIENT_ID=mobile
```

Substitua `IP_DO_COMPUTADOR` pelo endereço IP do computador que está executando a infraestrutura StarTech.

Exemplo ilustrativo:

```dotenv
EXPO_PUBLIC_API_URL=http://192.168.1.100:8080
EXPO_PUBLIC_KEYCLOAK_URL=http://192.168.1.100:8089
EXPO_PUBLIC_KEYCLOAK_CLIENT_ID=mobile
```

As portas apresentadas correspondem aos valores padrão definidos no Docker Compose. Caso sejam alteradas, ajuste as URLs.

### Como identificar o IP do computador

**Windows:**

```powershell
ipconfig
```

**macOS:**

Consulte o endereço IP nas configurações de rede do sistema ou utilize, quando aplicável:

```bash
ipconfig getifaddr en0
```

**Linux:**

```bash
ip addr
```

Utilize o endereço da interface de rede conectada à mesma rede do celular.

### Cuidados com a conexão

- Em celulares físicos, `localhost` representa o próprio aparelho, não o computador.
- O computador e o celular devem estar na mesma rede local ou em redes com comunicação permitida.
- Verifique se firewall, VPN ou isolamento do Wi-Fi estão impedindo a conexão.
- Em emuladores, o endereço utilizado para acessar o computador pode ser diferente do endereço utilizado em aparelhos físicos.
- Não inclua senhas, tokens, client secrets ou outras credenciais sensíveis em variáveis `EXPO_PUBLIC_*`.

## 6. Executando o aplicativo

Dentro da pasta `mobile-doador`, execute:

```bash
npx expo start
```

O Expo iniciará o servidor Metro e exibirá um QR Code e as opções de execução disponíveis.

Este comando pode ser utilizado em Windows, macOS e Linux.

### Execução com Expo Go

O Expo Go pode ser utilizado para visualizar funcionalidades compatíveis do aplicativo durante o desenvolvimento.

Para abrir o projeto:

1. Instale o Expo Go no celular.
2. Faça login na sua conta Expo pelo aplicativo.
3. No computador, execute `npx expo login` e entre com a mesma conta Expo, quando a autenticação for exigida.
4. Conecte o celular e o computador à mesma rede Wi-Fi.
5. Execute `npx expo start` no computador.
6. Escaneie o QR Code exibido no terminal.

**iPhone:** utilize a câmera do dispositivo para escanear o QR Code.

**Android:** utilize o leitor de QR Code do Expo Go.

### Conta Expo no computador e no celular

Em configurações que exigem autenticação no Expo Go, o computador e o aplicativo do celular devem utilizar a **mesma conta Expo**.

No computador, execute:

```bash
npx expo login
```

Entre com a conta Expo e depois inicie o projeto:

```bash
npx expo start
```

No celular, entre no Expo Go utilizando essa mesma conta.

Caso apareça a mensagem:

```text
You need to be signed in to Expo Go and Expo CLI to open your project.
```

Verifique se o login foi realizado corretamente nos dois ambientes.

Essa autenticação é utilizada para acessar o ambiente de desenvolvimento Expo e **não substitui o login do StarTech com Keycloak**.

**Atenção:** o Expo Go não é suficiente para validar o fluxo completo de autenticação OIDC do StarTech com esquema de redirecionamento personalizado. Para isso, utilize um development build.

## 7. Development build e autenticação OIDC

O StarTech Mobile utiliza o esquema personalizado:

```text
startech://autenticacao
```

Esse endereço permite que o provedor de autenticação redirecione o usuário de volta ao aplicativo após o login.

Para testar o fluxo completo, é necessário utilizar uma versão de desenvolvimento que suporte o esquema personalizado.

### Android

Com o ambiente Android configurado:

```bash
npx expo run:android
```

Para selecionar um dispositivo físico conectado:

```bash
npx expo run:android --device
```

### iOS

Em um Mac com Xcode configurado:

```bash
npx expo run:ios
```

Para selecionar um iPhone físico conectado:

```bash
npx expo run:ios --device
```

Os comandos de compilação nativa dependem das ferramentas específicas de cada plataforma.

### Iniciando o Metro para development build

Após instalar uma versão de desenvolvimento compatível:

```bash
npx expo start --dev-client
```

Alterações em configurações nativas, incluindo esquema de URL e plugins, podem exigir uma nova compilação.

### Compilação na nuvem

O EAS Build pode ser utilizado para compilar o aplicativo na infraestrutura do Expo.

Essa alternativa permite realizar determinadas compilações sem configurar todo o ambiente nativo local.

Entretanto, builds destinados à instalação em iPhones físicos exigem certificados e perfis de assinatura adequados da Apple.

A configuração e a publicação de builds pelo EAS não fazem parte da instalação básica documentada neste projeto.

## 8. Infraestrutura e Docker Compose

O aplicativo **não é executado dentro do Docker Compose**.

O Docker Compose executa os componentes da infraestrutura distribuída da StarTech, incluindo:

- API Gateway.
- Keycloak.
- BFF Mobile e BFF Web.
- Microsserviços de domínio.
- Orquestrador da SAGA.
- Bancos de dados.
- RabbitMQ.
- Serviços opcionais relacionados ao assistente RAG.

O aplicativo React Native é executado separadamente, pelo Expo ou por uma build instalada no dispositivo, e se comunica com o Gateway pela rede.

### Inicializando o Back-End

Na raiz do repositório StarTech, consulte as instruções do README principal e execute, quando apropriado:

```bash
docker compose up -d --build
```

O comando inicia os serviços habilitados no Compose padrão.

As portas publicadas por padrão são:

| Serviço | Porta |
|---|---|
| API Gateway | 8080 |
| Keycloak | 8089 |

Essas portas podem ser alteradas pelas configurações da infraestrutura.

### Assistente RAG

Os serviços de inteligência artificial, incluindo `ms-rag` e Ollama, estão associados ao perfil opcional `ia` do Docker Compose.

Para incluir esse perfil na inicialização:

```bash
docker compose --profile ia up -d --build
```

A execução do perfil de IA pode exigir memória adicional e download dos modelos configurados.

O BFF Mobile possui tratamento de fallback para situações em que o serviço RAG não está disponível.

## 9. Autenticação e segurança

A autenticação utiliza o Keycloak com o realm `startech`.

Configuração atualmente identificada no repositório:

- Client público: `mobile`.
- Fluxo: Authorization Code + PKCE.
- Papel exigido: `doador`.
- Audience exigida pelo Gateway: `bff-mobile`.
- Redirecionamento do aplicativo: `startech://autenticacao`.

**Atenção à issue #21:** a especificação prevê um client chamado `startech-mobile`, mas o arquivo `keycloak/realm-export.json` consultado ainda utiliza `mobile`.

O identificador configurado no aplicativo deve corresponder ao client realmente disponível no ambiente Keycloak. Essa divergência precisa ser alinhada com o responsável pela issue #21.

O aplicativo utiliza Expo SecureStore para armazenar os tokens e implementa restauração e renovação de sessão.

O login real depende de configuração adequada do Keycloak e de um ambiente de execução compatível.

### Comunicação autenticada

As requisições de negócio são encaminhadas exclusivamente pelo Gateway, utilizando:

```text
/api/mobile/**
```

O aplicativo utiliza o access token OIDC no cabeçalho de autorização.

Os cabeçalhos internos `X-User-Id` e `X-User-Roles` não são enviados manualmente pelo aplicativo. A identidade é tratada pelo Gateway.

## 10. Funcionalidades implementadas

### Login

- Tela de Login com identidade visual StarTech.
- Autenticação OIDC com PKCE.
- Armazenamento seguro dos tokens.
- Restauração e renovação da sessão.
- Logout e tratamento de erros de autenticação.

A autenticação completa ainda precisa ser validada com Keycloak em um development build.

### Home

Endpoint:

```http
GET /api/mobile/home
```

Apresenta:

- Informações do perfil do doador.
- Nome e tipo sanguíneo quando disponíveis.
- Campanhas personalizadas pelo tipo sanguíneo.
- Indicação de campanhas não personalizadas.
- Estados de carregamento, lista vazia e erro.
- Indicação de resposta degradada quando algum serviço está indisponível.

A Home não realiza avaliação clínica da aptidão do doador.

### Solicitação de agendamento

Endpoint:

```http
POST /api/mobile/agendamentos
```

O endpoint recebe um `slotId` real e inicia o processamento da SAGA.

Quando a solicitação é aceita, o BFF retorna HTTP `202 Accepted`, com identificadores e um link HATEOAS para acompanhamento.

Os horários atualmente apresentados na interface são demonstrativos e **não enviam requisições reais de agendamento**.

O fluxo real depende de uma fonte pública que disponibilize horários válidos e seus respectivos identificadores.

### Acompanhamento da SAGA

O acompanhamento utiliza o link fornecido na resposta do agendamento:

```text
_links.acompanhar.href
```

O aplicativo não constrói manualmente o endereço de acompanhamento a partir do identificador da SAGA.

A interface contempla os estados:

| Situação | Apresentação |
|---|---|
| `EM_ANDAMENTO` | Solicitação em processamento |
| `CONFIRMADO` | Agendamento confirmado |
| `RECUSADO` | Solicitação recusada |
| `CANCELADO` | Solicitação compensada no contexto da SAGA |
| `ERRO` | Falha no processamento ou na compensação |

O BFF Mobile apresenta o estado de SAGA compensada como `CANCELADO`.

Quando existir, o motivo retornado pelo Back-End é exibido ao doador.

O aplicativo realiza consultas periódicas controladas durante o processamento e as interrompe quando a operação termina ou a tela deixa de estar ativa.

A liberação efetiva de uma vaga em caso de compensação deve ser confirmada pelo comportamento do Back-End nos testes de integração.

### Meus pedidos

A aba apresenta uma interface destinada à consulta de agendamentos.

Entretanto, os endpoints públicos de listagem, detalhes e cancelamento ainda não estão disponíveis nos contratos implementados do BFF Mobile.

Por esse motivo, a tela informa a indisponibilidade dessas funcionalidades, sem apresentar dados fictícios como reais.

### Assistente de dúvidas

Endpoint:

```http
POST /api/mobile/assistente
```

O aplicativo permite:

- Enviar perguntas ao assistente.
- Exibir respostas retornadas pelo BFF Mobile.
- Apresentar fontes quando fornecidas.
- Identificar o modo da resposta.
- Informar quando o serviço utiliza fallback.
- Tratar erros de conexão e indisponibilidade.

O fallback é identificado quando:

```text
modo = FALLBACK
```

ou quando:

```text
degradado = true
```

O Assistente não substitui a avaliação realizada por profissionais de saúde.

## 11. HATEOAS

O aplicativo utiliza HATEOAS para respeitar os links de navegação e as ações disponibilizadas pelo Back-End.

Na solicitação de agendamento, o link `_links.acompanhar` é utilizado para consultar a SAGA.

A consulta e o cancelamento de agendamentos dependem da implementação da issue [#16 — Consultar e cancelar agendamento com HATEOAS](https://github.com/thiagovtr/startech/issues/16).

Quando os endpoints estiverem disponíveis, o aplicativo deverá:

- Consultar o recurso de agendamento pelos links públicos fornecidos.
- Exibir o botão de cancelamento somente quando existir o link HATEOAS `cancelar`.
- Utilizar o método HTTP indicado pelo link.
- Não apresentar ações que o estado atual do agendamento não permita.

Essas funcionalidades ainda não foram consideradas concluídas.

## 12. Situação em relação à issue #15

| Requisito | Situação |
|---|---|
| React Native + Expo + TypeScript | Implementado |
| URLs configuráveis do Gateway e Keycloak | Implementado |
| Login OIDC com PKCE | Implementado; teste integrado pendente |
| Armazenamento e renovação de tokens | Implementado; validação integrada pendente |
| Home com perfil e campanhas | Integrada no código; teste real pendente |
| Solicitação de agendamento | Preparada; depende de `slotId` real |
| Acompanhamento da SAGA | Integrado no código; teste real pendente |
| Exibição de compensação e motivo | Implementada; confirmação da liberação de vaga pendente |
| Consulta e cancelamento com HATEOAS | Dependem da issue #16 |
| Assistente com identificação de fallback | Integrado no código; teste real pendente |
| Documentação e execução pelo Expo | Documentado |

A implementação das interfaces e dos serviços do cliente mobile está avançada, mas **os critérios de aceite da issue #15 ainda não foram integralmente validados**.

## 13. Limitações e dependências conhecidas

As principais pendências são:

1. **Disponibilidade de horários:** ainda não existe um endpoint público confirmado para consultar slots disponíveis.
2. **Consulta de agendamentos:** depende dos recursos públicos previstos na issue #16.
3. **Cancelamento:** depende dos links HATEOAS e dos endpoints da issue #16.
4. **Autenticação:** o fluxo OIDC precisa ser validado com um development build e um Keycloak acessível.
5. **Client Keycloak:** alinhar a diferença entre o client `mobile` configurado e `startech-mobile` previsto na issue #21.
6. **SAGA:** validar a confirmação, a compensação e seus efeitos reais com a infraestrutura em execução.
7. **Assistente:** validar respostas e fallback do RAG em execução.
8. **Compatibilidade:** realizar testes funcionais completos em Android e iOS.

As integrações ainda não testadas não devem ser consideradas automaticamente funcionais apenas porque o código compila.

## 14. Verificações técnicas

Na pasta `mobile-doador`, execute:

```bash
npm exec tsc -- --noEmit
npx expo-doctor
```

O primeiro comando verifica erros de tipagem TypeScript.

O segundo verifica configurações do projeto e compatibilidade das dependências.

Para iniciar o servidor de desenvolvimento:

```bash
npx expo start
```

No momento da elaboração desta documentação, o cliente mobile não possui uma suíte própria de testes automatizados.

As verificações de compilação e tipagem não substituem testes funcionais de autenticação, rede ou integração com o Back-End.

## 15. Testes manuais recomendados

Com a infraestrutura StarTech acessível:

1. Abrir o aplicativo em um dispositivo compatível.
2. Realizar Login com um usuário autorizado.
3. Verificar o carregamento do perfil na Home.
4. Consultar as campanhas personalizadas.
5. Navegar entre Início, Agendar, Meus pedidos e Assistente.
6. Validar uma solicitação de agendamento utilizando um `slotId` real, quando disponível.
7. Acompanhar uma SAGA até a confirmação ou compensação.
8. Confirmar os efeitos da compensação no Back-End.
9. Consultar e cancelar um agendamento, quando os endpoints da issue #16 estiverem disponíveis.
10. Enviar perguntas ao Assistente e verificar respostas, fontes e fallback.
11. Validar o comportamento em caso de indisponibilidade de serviços.
12. Repetir os testes necessários em Android e iOS.

Registrar como concluídos somente os testes efetivamente executados.

## 16. Issues e documentação relacionada

### Issues

- [#15 — Cliente mobile (React Native) do doador](https://github.com/thiagovtr/startech/issues/15)
- [#16 — Consultar e cancelar agendamento com HATEOAS](https://github.com/thiagovtr/startech/issues/16)
- [#21 — Configurar o Keycloak para os clientes web e mobile](https://github.com/thiagovtr/startech/issues/21)
- [#22 — Design das interfaces do painel web e do app mobile](https://github.com/thiagovtr/startech/issues/22)

A identidade visual do aplicativo foi implementada diretamente no código, conforme decisão interna do grupo. A produção de protótipos externos prevista na issue #22 não está documentada como concluída.

### Documentação do repositório

- [README principal](../README.md)
- [Documentação de arquitetura](../docs/arquitetura/)
- [BFF Mobile](../bff-mobile/)
- [Configuração do Keycloak](../keycloak/)
- [Docker Compose](../compose.yaml)

### Documentação oficial

- [Expo](https://docs.expo.dev/)
- [React Native](https://reactnative.dev/)
- [React Navigation](https://reactnavigation.org/)
- [Expo AuthSession](https://docs.expo.dev/versions/latest/sdk/auth-session/)
- [Expo Development Builds](https://docs.expo.dev/develop/development-builds/introduction/)
- [Expo EAS Build](https://docs.expo.dev/build/introduction/)