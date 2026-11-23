import { StyleSheet, Text, View } from 'react-native';

import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

export type SituacaoSelo = 'NORMAL' | 'CRITICO' | 'PENDENTE' | 'CONFIRMADO' | 'RECUSADO' | 'CANCELADO' | 'ERRO';

type PropriedadesSeloStatus = {
  situacao: SituacaoSelo;
};

const conteudoSituacao: Record<SituacaoSelo, { icone: string; texto: string; destacado?: boolean }> = {
  NORMAL: { icone: '•', texto: 'Normal' },
  CRITICO: { icone: '!', texto: 'Crítico', destacado: true },
  PENDENTE: { icone: '◷', texto: 'Pendente' },
  CONFIRMADO: { icone: '✓', texto: 'Confirmado' },
  RECUSADO: { icone: '−', texto: 'Recusado' },
  CANCELADO: { icone: '−', texto: 'Cancelado' },
  ERRO: { icone: '!', texto: 'Erro', destacado: true },
};

export function SeloStatus({ situacao }: PropriedadesSeloStatus) {
  const { icone, texto, destacado } = conteudoSituacao[situacao];

  return (
    <View accessibilityLabel={`Situação: ${texto}`} style={[estilos.selo, destacado && estilos.seloDestacado]}>
      <Text style={[estilos.icone, destacado && estilos.textoDestacado]}>{icone}</Text>
      <Text style={[estilos.texto, destacado && estilos.textoDestacado]}>{texto}</Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  selo: {
    alignSelf: 'flex-start',
    alignItems: 'center',
    backgroundColor: cores.principalClaro,
    borderRadius: raiosBorda.arredondada,
    flexDirection: 'row',
    gap: espacamentos.minimo,
    minHeight: 28,
    paddingHorizontal: espacamentos.pequeno,
    paddingVertical: espacamentos.minimo,
  },
  seloDestacado: {
    backgroundColor: cores.principalEscuro,
  },
  icone: {
    color: cores.principalEscuro,
    fontSize: tamanhosFonte.corpo,
    fontWeight: pesosFonte.negrito,
  },
  texto: {
    color: cores.principalEscuro,
    fontSize: tamanhosFonte.legenda,
    fontWeight: pesosFonte.seminegrito,
  },
  textoDestacado: {
    color: cores.cartao,
  },
});
