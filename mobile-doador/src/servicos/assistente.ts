import type { criarClienteHttp } from './clienteHttp';

type ClienteHttp = ReturnType<typeof criarClienteHttp>;

export type PerguntaAssistente = {
  pergunta: string;
};

export type ModoAssistente = 'RAG' | 'FERRAMENTA' | 'FORA_DO_ESCOPO' | 'SEM_RAG' | 'FALLBACK';

export type FonteAssistente = {
  secao: string;
  fonte: string;
  trecho: string;
};

export type RespostaAssistente = {
  resposta: string | null;
  modo: ModoAssistente | null;
  fontes: FonteAssistente[];
  degradado: boolean;
  motivo?: string;
};

export async function perguntarAssistente(
  clienteHttp: ClienteHttp,
  pergunta: PerguntaAssistente,
): Promise<RespostaAssistente> {
  const texto = pergunta.pergunta.trim();

  if (texto.length < 3 || texto.length > 500) {
    throw new Error('A pergunta deve ter entre 3 e 500 caracteres.');
  }

  const resposta = await clienteHttp.requisitar<RespostaAssistente>('/api/mobile/assistente', {
    corpo: { pergunta: texto },
    metodo: 'POST',
  });

  if (!resposta.corpo) {
    throw new Error('A resposta do assistente não contém informações para exibir.');
  }

  return resposta.corpo;
}
