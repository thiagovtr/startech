import type { criarClienteHttp } from './clienteHttp';
import type { LinkHateoas } from './tiposHttp';

type ClienteHttp = ReturnType<typeof criarClienteHttp>;

export type SolicitacaoAgendamento = {
  slotId: string;
};

export type LinkAgendarSlot = {
  href: string;
  method: 'POST';
  title?: string;
};

export type SlotDisponivel = {
  slotId: string;
  postoId: string;
  dataHoraInicio: string;
  dataHoraFim: string;
  vagasDisponiveis: number;
  _links: {
    agendar: LinkAgendarSlot;
  };
};

export type RespostaSlotsDisponiveis = {
  itens: SlotDisponivel[];
  _links: {
    self: LinkHateoas;
  };
};

export type SituacaoAgendamento = 'CRIADO_PROVISORIO' | 'CONFIRMADO' | 'CANCELADO_DOADOR' | 'CANCELADO_COMPENSACAO_SAGA';

export type LinkConsultarAgendamento = {
  href: string;
  method: 'GET';
  title?: string;
};

export type DadosSlotAgendamento = {
  slotId: string;
  postoId: string;
  dataHoraInicio: string;
  dataHoraFim: string;
};

export type Agendamento = {
  id: string;
  status: SituacaoAgendamento;
  concluido: boolean;
  slot: DadosSlotAgendamento;
  disclaimerLegal?: string;
  dataCancelamento?: string | null;
  motivo?: string | null;
  slotLiberado?: string;
  _links: {
    self: LinkConsultarAgendamento;
    cancelar?: LinkHateoas;
    'novo-agendamento'?: LinkHateoas;
  };
};

export type RespostaListaAgendamentos = {
  itens: Agendamento[];
  _links: {
    self: LinkConsultarAgendamento;
    'novo-agendamento'?: LinkHateoas;
  };
};

export type SituacaoSolicitacaoAgendamento = 'EM_ANDAMENTO';

export type LinkAcompanharAgendamento = {
  href: string;
  method: 'GET';
};

export type RespostaSolicitacaoAgendamento = {
  sagaId: string;
  agendamentoId: string;
  situacao: SituacaoSolicitacaoAgendamento;
  _links: {
    acompanhar: LinkAcompanharAgendamento;
  };
};

export type SituacaoAcompanhamentoSaga = 'EM_ANDAMENTO' | 'CONFIRMADO' | 'RECUSADO' | 'CANCELADO' | 'ERRO';

export type RespostaAcompanhamentoSaga = {
  sagaId: string;
  agendamentoId: string;
  situacao: SituacaoAcompanhamentoSaga;
  finalizada: boolean;
  slotId: string;
  dataHoraInicio?: string | null;
  motivo?: string | null;
  _links: {
    self: LinkAcompanharAgendamento;
    agendamento?: LinkConsultarAgendamento;
    'novo-agendamento'?: LinkHateoas;
  };
};

export function slotIdEhValido(slotId: string | undefined): slotId is string {
  const slotIdNormalizado = slotId?.trim();
  return Boolean(slotIdNormalizado && slotIdNormalizado.length <= 64);
}

export async function solicitarAgendamento(
  clienteHttp: ClienteHttp,
  solicitacao: SolicitacaoAgendamento,
  linkAgendar: LinkAgendarSlot,
): Promise<RespostaSolicitacaoAgendamento> {
  if (!slotIdEhValido(solicitacao.slotId)) {
    throw new Error('O identificador do horário selecionado é inválido.');
  }

  const resposta = await clienteHttp.requisitarLink<RespostaSolicitacaoAgendamento>(linkAgendar, {
    corpo: { slotId: solicitacao.slotId.trim() },
  });

  if (resposta.status !== 202 || resposta.categoria !== 'ACEITO' || !resposta.corpo) {
    throw new Error('A solicitação de agendamento não foi aceita pelo serviço.');
  }

  return resposta.corpo;
}

export async function listarSlotsDisponiveis(clienteHttp: ClienteHttp): Promise<RespostaSlotsDisponiveis> {
  const resposta = await clienteHttp.requisitar<RespostaSlotsDisponiveis>('/api/mobile/slots');

  if (!resposta.corpo) {
    throw new Error('A resposta de disponibilidade não contém horários para exibir.');
  }

  return resposta.corpo;
}

export async function listarAgendamentos(clienteHttp: ClienteHttp): Promise<RespostaListaAgendamentos> {
  const resposta = await clienteHttp.requisitar<RespostaListaAgendamentos>('/api/mobile/agendamentos');

  if (!resposta.corpo) {
    throw new Error('A resposta não contém os agendamentos para exibir.');
  }

  return resposta.corpo;
}

export async function consultarAgendamento(
  clienteHttp: ClienteHttp,
  linkConsultar: LinkConsultarAgendamento,
  signal?: AbortSignal,
): Promise<Agendamento> {
  const resposta = await clienteHttp.requisitarLink<Agendamento>(linkConsultar, { signal });

  if (!resposta.corpo) {
    throw new Error('A resposta não contém os detalhes do agendamento.');
  }

  return resposta.corpo;
}

export async function acompanharSaga(
  clienteHttp: ClienteHttp,
  linkAcompanhar: LinkAcompanharAgendamento,
  signal?: AbortSignal,
): Promise<RespostaAcompanhamentoSaga> {
  const resposta = await clienteHttp.requisitarLink<RespostaAcompanhamentoSaga>(linkAcompanhar, { signal });

  if (!resposta.corpo) {
    throw new Error('A resposta de acompanhamento não contém informações para exibir.');
  }

  return resposta.corpo;
}
