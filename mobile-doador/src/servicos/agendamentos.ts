import type { criarClienteHttp } from './clienteHttp';
import type { LinkHateoas } from './tiposHttp';

type ClienteHttp = ReturnType<typeof criarClienteHttp>;

export type SolicitacaoAgendamento = {
  slotId: string;
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
): Promise<RespostaSolicitacaoAgendamento> {
  if (!slotIdEhValido(solicitacao.slotId)) {
    throw new Error('O identificador do horário selecionado é inválido.');
  }

  const resposta = await clienteHttp.requisitar<RespostaSolicitacaoAgendamento>('/api/mobile/agendamentos', {
    corpo: { slotId: solicitacao.slotId.trim() },
    metodo: 'POST',
  });

  if (resposta.status !== 202 || resposta.categoria !== 'ACEITO' || !resposta.corpo) {
    throw new Error('A solicitação de agendamento não foi aceita pelo serviço.');
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
