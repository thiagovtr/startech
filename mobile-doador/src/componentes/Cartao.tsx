import type { ReactNode } from 'react';
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { cores, espacamentos, raiosBorda } from '../tema';

type PropriedadesCartao = {
  children: ReactNode;
  estilo?: StyleProp<ViewStyle>;
};

export function Cartao({ children, estilo }: PropriedadesCartao) {
  return <View style={[estilos.cartao, estilo]}>{children}</View>;
}

const estilos = StyleSheet.create({
  cartao: {
    backgroundColor: cores.cartao,
    borderRadius: raiosBorda.grande,
    padding: espacamentos.padrao,
  },
});
