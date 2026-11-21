import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { BotaoPrimario, Cartao } from '../componentes';
import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

type PropriedadesLogin = {
  aoEntrar: () => void;
};

export function Login({ aoEntrar }: PropriedadesLogin) {
  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudoRolavel}>
        <View style={estilos.cabecalho}>
          <View accessibilityLabel="Identidade StarTech" style={estilos.marca}>
            <Text style={estilos.marcaTexto}>ST</Text>
          </View>
          <Text style={estilos.nomeAplicativo}>StarTech</Text>
          <Text style={estilos.slogan}>Doar sangue é cuidar de vidas.</Text>
        </View>

        <Cartao estilo={estilos.cartaoBoasVindas}>
          <Text style={estilos.titulo}>Boas-vindas</Text>
          <Text style={estilos.descricao}>
            Encontre campanhas, agende sua doação e acompanhe seus pedidos em um só lugar.
          </Text>
          <BotaoPrimario aoPressionar={aoEntrar} titulo="Login" />
        </Cartao>

        <Text style={estilos.rodape}>Sua próxima doação pode fazer a diferença.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const estilos = StyleSheet.create({
  areaSegura: {
    backgroundColor: cores.fundo,
    flex: 1,
  },
  conteudoRolavel: {
    flexGrow: 1,
    justifyContent: 'space-between',
    padding: espacamentos.muitoGrande,
  },
  cabecalho: {
    alignItems: 'center',
    gap: espacamentos.pequeno,
    marginTop: espacamentos.extraGrande,
  },
  marca: {
    alignItems: 'center',
    backgroundColor: cores.principal,
    borderRadius: raiosBorda.arredondada,
    height: 72,
    justifyContent: 'center',
    width: 72,
  },
  marcaTexto: {
    color: cores.cartao,
    fontSize: tamanhosFonte.subtitulo,
    fontWeight: pesosFonte.negrito,
  },
  nomeAplicativo: {
    color: cores.principalEscuro,
    fontSize: tamanhosFonte.cabecalho,
    fontWeight: pesosFonte.negrito,
  },
  slogan: {
    color: cores.textoSecundario,
    fontSize: tamanhosFonte.corpo,
    fontWeight: pesosFonte.medio,
    textAlign: 'center',
  },
  cartaoBoasVindas: {
    gap: espacamentos.padrao,
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
    lineHeight: 24,
  },
  rodape: {
    color: cores.textoSecundario,
    fontSize: tamanhosFonte.legenda,
    fontWeight: pesosFonte.medio,
    textAlign: 'center',
  },
});
