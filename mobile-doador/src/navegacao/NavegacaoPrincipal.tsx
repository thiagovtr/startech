import { NavigationContainer } from '@react-navigation/native';
import { useState } from 'react';

import { NavegacaoAbas } from './NavegacaoAbas';
import { Login } from '../telas';

export function NavegacaoPrincipal() {
  // Acesso provisório para testar as abas; substituir pela sessão autenticada via OIDC.
  const [acessoLiberado, definirAcessoLiberado] = useState(false);

  return (
    <NavigationContainer>
      {acessoLiberado ? <NavegacaoAbas /> : <Login aoEntrar={() => definirAcessoLiberado(true)} />}
    </NavigationContainer>
  );
}
