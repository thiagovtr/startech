import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Cartao } from '../componentes';
import { cores, espacamentos, pesosFonte, tamanhosFonte } from '../tema';

type PropriedadesTelaProvisoria = {
  titulo: string;
  descricao: string;
};

export function TelaProvisoria({ titulo, descricao }: PropriedadesTelaProvisoria) {
  return (
    <SafeAreaView edges={['right', 'bottom', 'left']} style={estilos.areaSegura}>
      <View style={estilos.conteudo}>
        <Text style={estilos.titulo}>{titulo}</Text>
        <Cartao>
          <Text style={estilos.descricao}>{descricao}</Text>
        </Cartao>
      </View>
    </SafeAreaView>
  );
}

const estilos = StyleSheet.create({
  areaSegura: {
    backgroundColor: cores.fundo,
    flex: 1,
  },
  conteudo: {
    flex: 1,
    gap: espacamentos.padrao,
    padding: espacamentos.padrao,
  },
  titulo: {
    color: cores.texto,
    fontSize: tamanhosFonte.titulo,
    fontWeight: pesosFonte.negrito,
  },
  descricao: {
    color: cores.textoSecundario,
    fontSize: tamanhosFonte.corpo,
    fontWeight: pesosFonte.normal,
  },
});
