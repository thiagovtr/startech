import type { criarClienteHttp } from './clienteHttp';

type ClienteHttp = ReturnType<typeof criarClienteHttp>;

export type UrgenciaCampanha = 'NORMAL' | 'CRITICO';

export type CampanhaHome = {
  id: string;
  titulo: string;
  hemocentro: string;
  tipo_sanguineo: string;
  urgencia: UrgenciaCampanha;
  status: string;
  data_inicio: string;
  data_fim: string;
};

export type DoadorHome = {
  id: string;
  nome?: string;
  tipoSanguineo?: string;
  tipo_sanguineo?: string;
  sexo?: 'M' | 'F';
  dataUltimaDoacao?: string | null;
  cadastrado?: boolean;
  statusDegradado?: boolean;
};

export type RespostaHome = {
  status: 'ok' | 'degradado';
  servicosIndisponiveis: string[];
  doador: DoadorHome;
  tipoSanguineoCampanhas: string | null;
  campanhasPersonalizadas: boolean;
  campanhas: CampanhaHome[];
};

export async function consultarHome(
  clienteHttp: ClienteHttp,
  signal?: AbortSignal,
): Promise<RespostaHome> {
  const resposta = await clienteHttp.requisitar<RespostaHome>('/api/mobile/home', { signal });

  if (!resposta.corpo) {
    throw new Error('A resposta da Home não contém informações para exibir.');
  }

  return resposta.corpo;
}
