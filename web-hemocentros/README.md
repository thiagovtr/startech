# StarTech — Painel dos hemocentros

Cliente web em React, TypeScript e Vite para operadores consultarem e criarem campanhas de doação. O login usa o realm `startech` e o cliente público `startech-web` do Keycloak, com Authorization Code e PKCE (S256). O token fica em memória. As consultas e os comandos seguem pelo Gateway até o BFF Web.

## Execução

Na raiz do projeto, execute:

```sh
docker compose up -d --build
```

Abra `http://localhost:8085` e entre com uma conta com o papel `operador`. O contêiner compila o frontend em Node e serve os arquivos estáticos com nginx.

Para desenvolver apenas o frontend, use Node.js 22.13 ou superior e npm na pasta `web-hemocentros`:

```sh
npm ci
npm run dev
```

O Vite atende em `http://localhost:5173`. O login e as operações de campanhas precisam do Keycloak e do Gateway acessíveis ao navegador. Para compilar e executar os testes isolados do cliente HTTP:

```sh
npm run build
npm test
```

| Configuração | Padrão | Uso |
| --- | --- | --- |
| `WEB_HEMOCENTROS_PORT` | `8085` | Porta publicada pelo Compose |
| `WEB_GATEWAY_URL` | `http://localhost:8080` | URL pública do Gateway usada no build do Compose |
| `WEB_KEYCLOAK_URL` | `http://localhost:8089` | URL pública do Keycloak usada no build do Compose |

Os padrões do Compose acompanham `GATEWAY_HOST_PORT` e `KEYCLOAK_HOST_PORT`. No Vite, as variáveis equivalentes são `VITE_GATEWAY_URL` e `VITE_KEYCLOAK_URL`. Os endereços são incorporados na compilação. Em um domínio próprio, use HTTPS e confira a origem permitida pelo Gateway e as origens e os redirecionamentos do cliente no Keycloak.

## Campanhas

A listagem usa `GET /api/web/campanhas` com `limit` e `offset`. O cabeçalho `X-Total-Count` informa a contagem após aplicar os filtros. O filtro de vigência considera a data de término, inclusive o próprio dia.

O formulário envia `POST /api/web/campanhas`. A confirmação mostra o título e o identificador devolvidos na escrita. A listagem consulta a projeção do CQRS, que pode levar alguns segundos para refletir o cadastro. Use **Atualizar lista** para consultar novamente. Em caso de perda da resposta do cadastro, consulte as campanhas antes de repetir o envio.

## Verificação integrada

1. Entre no painel como operador. A listagem deve carregar pelo Gateway.
2. Cadastre uma campanha com título identificável, tipo sanguíneo igual ao do doador de teste, início hoje e término igual ou posterior a hoje. Confira o identificador na confirmação e o HTTP `201` no POST.
3. Atualize a lista e filtre pelo tipo escolhido. A campanha deve aparecer com status **Ativa**. A ordenação é por data de início e identificador. Avance a página se necessário.
4. Após alguns segundos, abra o aplicativo conectado ao mesmo ambiente e entre como doador. Se a tela inicial já estava aberta, reabra o aplicativo para carregar os dados novamente. Confira título, hemocentro e tipo sanguíneo. Compare o ID da confirmação com o da campanha em `campanhas` na resposta de `GET /api/mobile/home`.
