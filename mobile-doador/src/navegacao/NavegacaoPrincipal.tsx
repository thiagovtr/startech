import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useState } from 'react';

import { NavegacaoAbas } from './NavegacaoAbas';
import { AcompanhamentoSaga, Login } from '../telas';

export type ParametrosRaiz = {
  Abas: undefined;
  AcompanhamentoSaga: undefined;
};

const PilhaRaiz = createNativeStackNavigator<ParametrosRaiz>();

export function NavegacaoPrincipal() {
  // Acesso provisório para testar as abas; substituir pela sessão autenticada via OIDC.
  const [acessoLiberado, definirAcessoLiberado] = useState(false);

  return (
    <NavigationContainer>
      {acessoLiberado ? (
        <PilhaRaiz.Navigator screenOptions={{ headerShown: false }}>
          <PilhaRaiz.Screen component={NavegacaoAbas} name="Abas" />
          <PilhaRaiz.Screen component={AcompanhamentoSaga} name="AcompanhamentoSaga" />
        </PilhaRaiz.Navigator>
      ) : (
        <Login aoEntrar={() => definirAcessoLiberado(true)} />
      )}
    </NavigationContainer>
  );
}
