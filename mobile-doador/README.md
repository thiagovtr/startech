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
EXPO_PUBLIC_KEYCLOAK_CLIENT_ID=startech-mobile
```

Substitua `IP_DO_COMPUTADOR` pelo endereço IP do computador que está executando a infraestrutura StarTech.

Exemplo ilustrativo:

```dotenv
EXPO_PUBLIC_API_URL=http://192.168.1.100:8080
EXPO_PUBLIC_KEYCLOAK_URL=http://192.168.1.100:8089
EXPO_PUBLIC_KEYCLOAK_CLIENT_ID=startech-mobile
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

No ambiente Azure já testado, o login e o retorno ao aplicativo funcionaram no Expo Go em um iPhone. Ainda assim, a validação do esquema personalizado `startech://` em um development build permanece necessária, pois ela cobre o comportamento nativo da configuração distribuída do aplicativo.

## 7. Development build e autenticação OIDC

O StarTech Mobile utiliza o esquema personalizado:

```text
startech://autenticacao
```

Esse endereço permite que o provedor de autenticação redirecione o usuário de volta ao aplicativo após o login.

Para validar especificamente o esquema personalizado em uma instalação nativa, utilize uma versão de desenvolvimento que o suporte.

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

- Client público principal: `startech-mobile`.
- Client público `mobile`: alias de compatibilidade para configurações legadas e testes E2E.
- Fluxo: Authorization Code + PKCE.
- Papel exigido: `doador`.
- Audience exigida pelo Gateway: `bff-mobile`.
- Redirecionamento do aplicativo: `startech://autenticacao`.

Os dois clients estão presentes em `keycloak/realm-export.json`, são públicos, utilizam Authorization Code com PKCE S256 e aceitam os redirecionamentos `exp://*` e `startech://*`. Para novas configurações, utilizar `startech-mobile`; em ambientes já configurados com o alias, utilizar o valor efetivamente disponibilizado pelo Keycloak.

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
- Logout, revogação de refresh token quando suportada e tratamento de erros de autenticação.

Login, logout e restauração de sessão foram testados com sucesso em um iPhone pelo Expo Go, usando a infraestrutura Azure.

### Cadastro de perfil

Após o primeiro login, e também após a restauração de uma sessão, o aplicativo consulta:

```http
GET /api/mobile/home
```

Quando a resposta indicar `doador.cadastrado: false`, as abas permanecem bloqueadas até a conclusão do cadastro. Uma resposta degradada ou `doador.statusDegradado` não é tratada como ausência de perfil.

O formulário envia os dados exclusivamente pelo Gateway:

```http
PUT /api/mobile/perfil
```

O formulário modernizado solicita nome completo, tipo sanguíneo (`A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `O+` ou `O-`) e sexo (`M` ou `F`), todos obrigatórios, além da data da última doação opcional. A data é digitada em `dd/mm/aaaa` e convertida para `AAAA-MM-DD` antes do envio. O aplicativo valida nome, data inexistente e data futura antes do envio; também apresenta falhas de conexão e os campos devolvidos em `invalidParams`.

Após salvar, o aplicativo consulta a Home novamente e libera as abas somente se o perfil estiver cadastrado. A tela também permite encerrar a sessão para trocar de usuário.

A tela, a seleção de tipo sanguíneo e o salvamento do perfil foram testados com sucesso em um iPhone com Expo Go conectado à infraestrutura Azure.

### Home

Endpoint:

```http
GET /api/mobile/home
```

Apresenta:

- Cabeçalho StarTech integrado ao conteúdo e acesso ao Meu perfil pelo avatar.
- Cartão de perfil do doador com nome e tipo sanguíneo quando disponíveis.
- Banner condicional do próximo agendamento confirmado, com acesso aos detalhes pelo link HATEOAS recebido.
- Prévia de campanhas personalizadas pelo tipo sanguíneo e página Todas as campanhas para os itens retornados pela Home.
- Indicação de campanhas não personalizadas.
- Três ações rápidas lado a lado para Agendar doação, Meus pedidos e Assistente.
- Atualização por ícone.
- Estados de carregamento, lista vazia e erro.
- Indicação de resposta degradada quando algum serviço está indisponível.

A Home não realiza avaliação clínica da aptidão do doador.

### Meu perfil e navegação

O avatar da Home abre a página Meu perfil. Ela organiza informações somente para leitura nas categorias Informações básicas, Segurança e Cadastro.

- Nome completo é exibido quando retornado pela Home.
- Nome de usuário, e-mail, sexo e data da última doação são apresentados como indisponíveis enquanto não forem fornecidos pelos contratos atuais.
- A opção de alteração de senha permanece desabilitada, pois não há suporte público disponível no aplicativo.
- O logout está concentrado em Meu perfil; a opção de troca de usuário também permanece na conclusão obrigatória do cadastro.

A navegação principal utiliza uma navbar flutuante com quatro abas — Início, Agendar, Meus pedidos e Assistente —, ícones, áreas de toque adequadas e respeito às safe areas. Os cabeçalhos das telas foram integrados ao conteúdo para evitar barras superiores separadas.

### Solicitação de agendamento

Endpoint:

```http
GET /api/mobile/slots
POST /api/mobile/agendamentos
```

O Back-End implementa a consulta de slots reais, com os filtros opcionais `postoId`, `de` e `ate`. Cada item fornece, entre outros campos, `slotId`, `postoId`, período, vagas disponíveis e o link HATEOAS `_links.agendar`.

O endpoint de solicitação recebe um `slotId` real e inicia o processamento da SAGA.

Quando a solicitação é aceita, o BFF retorna HTTP `202 Accepted`, com identificadores e um link HATEOAS para acompanhamento.

No aplicativo, a tela Agendamentos apresenta acesso rápido a Meus pedidos, a seção Agendar doação e uma prévia de até três horários. Quando houver outros itens retornados pelo Back-End, a página Todos os horários permite consultar a lista completa. Após selecionar um slot real, a página Resumo do agendamento apresenta os dados antes da confirmação. A solicitação utiliza exclusivamente o link HATEOAS `_links.agendar` retornado para esse slot.

A consulta e a seleção de slots, bem como a solicitação real, foram testadas com sucesso no iPhone conectado à Azure.

### Acompanhamento da SAGA

O acompanhamento utiliza o link fornecido na resposta do agendamento:

```text
_links.acompanhar.href
```

O aplicativo não constrói manualmente o endereço de acompanhamento a partir do identificador da SAGA.

Não existe modo demonstrativo: o acompanhamento depende obrigatoriamente do link HATEOAS real retornado pelo BFF.

A interface contempla os estados:

| Situação | Apresentação |
|---|---|
| `EM_ANDAMENTO` | Solicitação em análise |
| `CONFIRMADO` | Agendamento confirmado |
| `RECUSADO` | Solicitação não confirmada |
| `CANCELADO` | Agendamento cancelado |
| `ERRO` | Não foi possível concluir a solicitação |

O BFF Mobile apresenta o estado de SAGA compensada como `CANCELADO`.

Quando existir, o motivo retornado pelo Back-End é exibido ao doador. As mensagens de apresentação foram ajustadas para linguagem natural, sem alterar os status técnicos nem o conteúdo útil retornado pelo serviço.

O aplicativo realiza consultas periódicas controladas durante o processamento e as interrompe quando a operação termina ou a tela deixa de estar ativa.

O cancelamento automático por compensação foi testado com sucesso no iPhone conectado à Azure. Após solicitar um horário com 5 vagas disponíveis, a SAGA terminou como `CANCELADO`, com a mensagem de cancelamento e o motivo de que a última doação ocorreu em 13/11/2026 e uma nova doação seria permitida a partir de 12/01/2027, respeitando o intervalo de 60 dias. Ao retornar à tela Agendar, o mesmo horário continuava com 5 vagas disponíveis; o comportamento foi reproduzido em novas tentativas.

Esse resultado confirma o comportamento observado pelo aplicativo, mas não comprova diretamente nos bancos a reserva provisória nem a execução interna de `STEP1 COMPENSATE OK`.

Quando a SAGA é confirmada, o Back-End fornece `_links.agendamento`. O aplicativo utiliza esse link para abrir os detalhes do agendamento; essa navegação foi testada com sucesso.

### Meus pedidos

A aba apresenta uma interface destinada à consulta de agendamentos.

O Back-End já implementa os contratos públicos abaixo:

```http
GET /api/mobile/agendamentos
GET /api/mobile/agendamentos/{id}
POST /api/mobile/agendamentos/{id}/cancelamento
```

O cancelamento somente é oferecido quando a representação fornecer o link HATEOAS `_links.cancelar`, com o método indicado. O corpo pode conter o motivo opcional do cancelamento.

A aba destaca todos os agendamentos confirmados e apresenta uma prévia de até três pedidos anteriores. Quando houver mais pedidos anteriores, a página Pedidos anteriores apresenta a lista completa. A aba abre os detalhes pelo link `_links.self` e é atualizada ao retornar da tela de detalhes. A ordenação cronológica completa dos pedidos anteriores depende de um campo temporal que ainda não é fornecido pelo Back-End. A listagem, os detalhes e o cancelamento real foram testados com sucesso no iPhone conectado à Azure.

### Assistente de dúvidas

Endpoint:

```http
POST /api/mobile/assistente
```

O aplicativo permite:

- Utilizar cabeçalho integrado ao conteúdo, compatível com teclado e navbar flutuante.
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

Na solicitação de agendamento, o link `_links.acompanhar` é utilizado para consultar a SAGA. Os slots retornam `_links.agendar`; uma SAGA confirmada pode retornar `_links.agendamento`; e um agendamento cancelável pode retornar `_links.cancelar`.

Os contratos da issue [#16 — Consultar e cancelar agendamento com HATEOAS](https://github.com/thiagovtr/startech/issues/16) estão integrados ao aplicativo e foram testados com a infraestrutura Azure.

O aplicativo:

- Consulta o recurso de agendamento pelos links públicos fornecidos.
- Exibe o botão de cancelamento somente quando existir o link HATEOAS `cancelar`.
- Utiliza o método HTTP indicado pelo link.
- Não apresenta ações que o estado atual do agendamento não permita.

Após um cancelamento confirmado, a representação atualizada retornada pelo Back-End substitui a anterior e remove a ação quando o link `cancelar` deixa de existir.

## 12. Situação em relação à issue #15

| Requisito | Situação |
|---|---|
| React Native + Expo + TypeScript | Implementado |
| URLs configuráveis do Gateway e Keycloak | Implementado |
| Login OIDC com PKCE | Implementado e testado no iPhone com Expo Go e Azure |
| Armazenamento e renovação de tokens | Implementado; restauração de sessão testada no ambiente citado |
| Cadastro de perfil após o primeiro login | Implementado e validado no iPhone com Expo Go e Azure |
| Home com perfil e campanhas | Integrada e testada no iPhone com Azure |
| Consulta e solicitação de agendamento | Integradas e testadas no iPhone com Azure |
| Acompanhamento da SAGA | Integrado por HATEOAS; acesso a partir da solicitação e navegação para detalhes confirmados em teste |
| Exibição de compensação e motivo | Implementada e testada no iPhone com Azure |
| Consulta e cancelamento com HATEOAS | Integrados e testados no iPhone com Azure |
| Assistente com identificação de fallback | Integrado e testado no iPhone com Azure |
| Documentação e execução pelo Expo | Documentado |

As funcionalidades principais da issue #15 estão implementadas e tiveram validação manual no iPhone com a infraestrutura Azure. Permanecem pendentes os cenários excepcionais e a comprovação interna da sequência de compensação da SAGA.

## 13. Limitações e dependências conhecidas

As principais pendências são:

1. **SAGA:** a compensação automática e a preservação das vagas foram observadas pelo aplicativo; ainda falta comprovar internamente a reserva provisória e a execução de `STEP1 COMPENSATE OK` no Back-End.
2. **Cenários excepcionais:** conflitos de concorrência, indisponibilidade dos serviços e respostas de erro ainda precisam de testes manuais específicos.
3. **Testes automatizados:** o aplicativo ainda não possui uma suíte própria de testes automatizados.

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

## 15. Testes manuais

Os testes abaixo foram realizados com sucesso em um iPhone, pelo Expo Go, conectado à infraestrutura Azure:

1. Login, logout e restauração de sessão com Keycloak.
2. Navegação entre Início, Agendar, Meus pedidos e Assistente pela navbar flutuante.
3. Carregamento de nome, tipo sanguíneo, campanhas e acesso ao Meu perfil pela Home.
4. Respostas, fontes e fallback do Assistente RAG, além de verificações básicas de estabilidade.
5. Consulta, seleção e solicitação de um slot real pelo link `_links.agendar`.
6. Acesso ao acompanhamento da SAGA após a solicitação e navegação da SAGA confirmada para os detalhes.
7. Listagem e detalhes de agendamentos reais, incluindo atualização da lista ao retornar; oito testes manuais desse fluxo foram aprovados.
8. Exibição condicional do cancelamento, confirmação, desistência, cancelamento real e atualização da situação e da listagem; oito testes manuais desse fluxo foram aprovados.
9. Compensação automática da SAGA: um horário com 5 vagas foi solicitado, terminou como `CANCELADO` com mensagem de cancelamento e motivo de intervalo mínimo; após o retorno à tela Agendar, o mesmo horário permaneceu com 5 vagas. O cenário foi reproduzido em novas tentativas.
10. Conclusão e salvamento do perfil, incluindo a seleção de tipo sanguíneo e a data opcional no formato brasileiro, realizados com sucesso no iPhone com Expo Go conectado à Azure.
11. Páginas de Perfil, cabeçalhos integrados, prévias de horários e pedidos, páginas de listagem completa e navegação de retorno validadas visualmente no Expo Go.

Permanecem recomendados testes da sequência interna de compensação da SAGA, conflitos de concorrência e indisponibilidade dos serviços. Registrar como concluídos somente os cenários efetivamente executados.

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
