import type { criarClienteHttp } from './clienteHttp';

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
