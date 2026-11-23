import { criarUrlMobile, ErroConfiguracaoApi, validarLinkMobile } from '../configuracao';
import type {
  CategoriaErroHttp,
  CategoriaRespostaHttp,
  LinkHateoas,
  MetodoHttp,
  ObterTokenAcesso,
  OpcoesRequisicao,
  ParametroInvalido,
  ProblemaHttp,
  RespostaHttp,
} from './tiposHttp';

export class ErroHttp extends Error {
  constructor(
    public readonly status: number,
    public readonly categoria: CategoriaErroHttp,
    public readonly problema: ProblemaHttp,
  ) {
    super(problema.detail ?? problema.title);
    this.name = 'ErroHttp';
  }
}

export function criarClienteHttp(obterTokenAcesso: ObterTokenAcesso) {
  async function requisitar<TCorpo>(caminho: string, opcoes: OpcoesRequisicao = {}): Promise<RespostaHttp<TCorpo>> {
    return executarRequisicao<TCorpo>(criarUrlMobile(caminho), opcoes, obterTokenAcesso);
  }

  async function requisitarLink<TCorpo>(link: LinkHateoas, opcoes: Omit<OpcoesRequisicao, 'metodo'> = {}): Promise<RespostaHttp<TCorpo>> {
    return executarRequisicao<TCorpo>(validarLinkMobile(link.href), { ...opcoes, metodo: link.method ?? 'GET' }, obterTokenAcesso);
  }

  return { requisitar, requisitarLink };
}

async function executarRequisicao<TCorpo>(
  url: URL,
  opcoes: OpcoesRequisicao,
  obterTokenAcesso: ObterTokenAcesso,
): Promise<RespostaHttp<TCorpo>> {
  const tokenAcesso = await obterTokenAcesso();
  const cabecalhos = new Headers({ Accept: 'application/json, application/problem+json' });

  if (tokenAcesso) {
    cabecalhos.set('Authorization', `Bearer ${tokenAcesso}`);
  }

  if (opcoes.corpo !== undefined) {
    cabecalhos.set('Content-Type', 'application/json');
  }

  let resposta: Response;

  try {
    resposta = await fetch(url, {
      body: opcoes.corpo === undefined ? undefined : JSON.stringify(opcoes.corpo),
      headers: cabecalhos,
      method: opcoes.metodo ?? 'GET',
      signal: opcoes.signal,
    });
  } catch (erro) {
    if (erro instanceof ErroConfiguracaoApi || erro instanceof ErroHttp) {
      throw erro;
    }

    throw new ErroHttp(0, 'REDE', {
      title: 'Não foi possível conectar ao serviço',
      detail: 'Verifique sua conexão e a configuração do API Gateway.',
      status: 0,
    });
  }

  if (!resposta.ok) {
    throw new ErroHttp(resposta.status, classificarErro(resposta.status), await lerProblema(resposta));
  }

  return {
    status: resposta.status,
    categoria: classificarResposta(resposta.status),
    corpo: await lerCorpo<TCorpo>(resposta),
    cabecalhos: resposta.headers,
  };
}

function classificarResposta(status: number): CategoriaRespostaHttp {
  if (status === 202) {
    return 'ACEITO';
  }

  if (status === 204) {
    return 'SEM_CONTEUDO';
  }

  return 'SUCESSO';
}

function classificarErro(status: number): CategoriaErroHttp {
  if (status === 400 || status === 422) return 'REQUISICAO_INVALIDA';
  if (status === 401) return 'AUTENTICACAO_NECESSARIA';
  if (status === 403) return 'ACESSO_NEGADO';
  if (status === 404) return 'NAO_ENCONTRADO';
  if (status === 409) return 'CONFLITO';
  if ([502, 503, 504].includes(status)) return 'SERVICO_INDISPONIVEL';
  return 'DESCONHECIDO';
}

async function lerCorpo<TCorpo>(resposta: Response): Promise<TCorpo | undefined> {
  if (resposta.status === 204 || !resposta.headers.get('content-type')?.includes('json')) {
    return undefined;
  }

  return (await resposta.json()) as TCorpo;
}

async function lerProblema(resposta: Response): Promise<ProblemaHttp> {
  const corpo = await lerCorpo<Partial<ProblemaHttp>>(resposta);

  return {
    detail: corpo?.detail,
    instance: corpo?.instance,
    invalidParams: normalizarParametrosInvalidos(corpo?.invalidParams),
    status: corpo?.status ?? resposta.status,
    title: corpo?.title ?? tituloPadraoErro(resposta.status),
    type: corpo?.type,
  };
}

function normalizarParametrosInvalidos(parametros: unknown): ParametroInvalido[] | undefined {
  if (!Array.isArray(parametros)) {
    return undefined;
  }

  return parametros.filter((parametro): parametro is ParametroInvalido => (
    typeof parametro === 'object'
    && parametro !== null
    && typeof parametro.name === 'string'
    && typeof parametro.reason === 'string'
  ));
}

function tituloPadraoErro(status: number): string {
  const titulos: Record<number, string> = {
    400: 'Requisição inválida',
    401: 'Autenticação necessária',
    403: 'Acesso não autorizado',
    404: 'Recurso não encontrado',
    409: 'Conflito na solicitação',
    422: 'Requisição inválida',
    502: 'Serviço temporariamente indisponível',
    503: 'Serviço temporariamente indisponível',
    504: 'Serviço temporariamente indisponível',
  };

  return titulos[status] ?? 'Erro na comunicação';
}
