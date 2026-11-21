import { createContext, useContext, type ReactNode } from 'react';

import type { Autenticacao } from './useAutenticacao';

const ContextoAutenticacao = createContext<Autenticacao | null>(null);

type PropriedadesProvedorAutenticacao = {
  autenticacao: Autenticacao;
  children: ReactNode;
};

export function ProvedorAutenticacao({ autenticacao, children }: PropriedadesProvedorAutenticacao) {
  return <ContextoAutenticacao.Provider value={autenticacao}>{children}</ContextoAutenticacao.Provider>;
}

export function useContextoAutenticacao(): Autenticacao {
  const autenticacao = useContext(ContextoAutenticacao);

  if (!autenticacao) {
    throw new Error('A autenticação deve estar disponível dentro do ProvedorAutenticacao.');
  }

  return autenticacao;
}
