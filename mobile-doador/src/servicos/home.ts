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
