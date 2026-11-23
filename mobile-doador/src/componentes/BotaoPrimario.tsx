import { ActivityIndicator, Pressable, StyleSheet, Text } from 'react-native';

import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

type PropriedadesBotaoPrimario = {
  titulo: string;
  aoPressionar: () => void;
  desabilitado?: boolean;
  carregando?: boolean;
};

export function BotaoPrimario({
  titulo,
  aoPressionar,
  desabilitado = false,
  carregando = false,
}: PropriedadesBotaoPrimario) {
  const estaDesabilitado = desabilitado || carregando;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: estaDesabilitado, busy: carregando }}
      disabled={estaDesabilitado}
      onPress={aoPressionar}
      style={({ pressed }) => [
        estilos.botao,
        estaDesabilitado && estilos.botaoDesabilitado,
        pressed && !estaDesabilitado && estilos.botaoPressionado,
      ]}
    >
      {carregando ? (
        <ActivityIndicator color={cores.cartao} />
      ) : (
        <Text style={[estilos.rotulo, estaDesabilitado && estilos.rotuloDesabilitado]}>{titulo}</Text>
      )}
    </Pressable>
  );
}

const estilos = StyleSheet.create({
  botao: {
    alignItems: 'center',
    backgroundColor: cores.principal,
    borderRadius: raiosBorda.media,
    justifyContent: 'center',
    minHeight: 48,
    paddingHorizontal: espacamentos.grande,
    paddingVertical: espacamentos.medio,
  },
  botaoDesabilitado: {
    backgroundColor: cores.principalClaro,
  },
  botaoPressionado: {
    backgroundColor: cores.principalEscuro,
  },
  rotulo: {
    color: cores.cartao,
    fontSize: tamanhosFonte.corpo,
    fontWeight: pesosFonte.seminegrito,
  },
  rotuloDesabilitado: {
    color: cores.principalEscuro,
  },
});
