import type { ReactNode } from 'react';
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { cores, espacamentos, raiosBorda } from '../tema';

type PropriedadesCartao = {
  filhos: ReactNode;
  estilo?: StyleProp<ViewStyle>;
};

export function Cartao({ filhos, estilo }: PropriedadesCartao) {
  return <View style={[estilos.cartao, estilo]}>{filhos}</View>;
}

const estilos = StyleSheet.create({
  cartao: {
    backgroundColor: cores.cartao,
    borderRadius: raiosBorda.grande,
    padding: espacamentos.padrao,
  },
});
