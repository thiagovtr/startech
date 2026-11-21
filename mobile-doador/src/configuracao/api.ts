const PREFIXO_MOBILE = '/api/mobile/';

export class ErroConfiguracaoApi extends Error {
  constructor(mensagem: string) {
    super(mensagem);
    this.name = 'ErroConfiguracaoApi';
  }
}

export function obterUrlApiGateway(): URL {
  const valorConfigurado = process.env.EXPO_PUBLIC_API_URL?.trim();

  if (!valorConfigurado) {
    throw new ErroConfiguracaoApi(
      'A variável EXPO_PUBLIC_API_URL não foi configurada. Defina a URL pública do API Gateway.',
    );
  }

  let urlGateway: URL;

  try {
    urlGateway = new URL(valorConfigurado);
  } catch {
    throw new ErroConfiguracaoApi('EXPO_PUBLIC_API_URL deve conter uma URL válida do API Gateway.');
  }

  if (!['http:', 'https:'].includes(urlGateway.protocol) || urlGateway.username || urlGateway.password) {
    throw new ErroConfiguracaoApi('EXPO_PUBLIC_API_URL deve usar http ou https, sem credenciais na URL.');
  }

  if (urlGateway.pathname !== '/' || urlGateway.search || urlGateway.hash) {
    throw new ErroConfiguracaoApi('EXPO_PUBLIC_API_URL deve apontar somente para a origem pública do API Gateway.');
  }

  return urlGateway;
}

export function criarUrlMobile(caminho: string): URL {
  if (!caminho.startsWith(PREFIXO_MOBILE)) {
    throw new ErroConfiguracaoApi('As requisições móveis devem usar caminhos iniciados por /api/mobile/.');
  }

  return new URL(caminho, obterUrlApiGateway());
}

export function validarLinkMobile(href: string): URL {
  const urlGateway = obterUrlApiGateway();
  const urlLink = new URL(href, urlGateway);

  if (urlLink.origin !== urlGateway.origin) {
    throw new ErroConfiguracaoApi('O link recebido não pertence ao API Gateway configurado.');
  }

  if (!urlLink.pathname.startsWith(PREFIXO_MOBILE)) {
    throw new ErroConfiguracaoApi('O link recebido não utiliza o prefixo público /api/mobile/.');
  }

  return urlLink;
}
