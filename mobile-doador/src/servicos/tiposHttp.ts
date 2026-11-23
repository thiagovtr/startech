export type MetodoHttp = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export type CategoriaRespostaHttp = 'SUCESSO' | 'ACEITO' | 'SEM_CONTEUDO';

export type CategoriaErroHttp =
  | 'REQUISICAO_INVALIDA'
  | 'AUTENTICACAO_NECESSARIA'
  | 'ACESSO_NEGADO'
  | 'NAO_ENCONTRADO'
  | 'CONFLITO'
  | 'SERVICO_INDISPONIVEL'
  | 'REDE'
  | 'DESCONHECIDO';

export type ParametroInvalido = {
  name: string;
  reason: string;
};

export type ProblemaHttp = {
  type?: string;
  title: string;
  detail?: string;
  status: number;
  instance?: string;
  invalidParams?: ParametroInvalido[];
};

export type RespostaHttp<TCorpo> = {
  status: number;
  categoria: CategoriaRespostaHttp;
  corpo?: TCorpo;
  cabecalhos: Headers;
};

export type LinkHateoas = {
  href: string;
  method?: MetodoHttp;
};

export type ObterTokenAcesso = () => Promise<string | null>;

export type OpcoesRequisicao = {
  metodo?: MetodoHttp;
  corpo?: unknown;
  signal?: AbortSignal;
};
