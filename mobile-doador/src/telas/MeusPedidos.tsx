import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Cartao, EstadoFeedback } from '../componentes';
import { cores, espacamentos, pesosFonte, tamanhosFonte } from '../tema';

export function MeusPedidos() {
  return (
    <SafeAreaView edges={['right', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <View style={estilos.cabecalho}>
          <Text style={estilos.titulo}>Meus pedidos</Text>
          <Text style={estilos.descricao}>Consulte solicitações e agendamentos vinculados à sua conta.</Text>
        </View>

        <Cartao estilo={estilos.cartaoInformativo}>
          <Text style={estilos.tituloCartao}>Consulta de agendamentos indisponível</Text>
          <Text style={estilos.textoCartao}>
            O BFF Mobile ainda não disponibiliza um recurso público para listar ou detalhar seus agendamentos.
          </Text>
        </Cartao>

        <EstadoFeedback
          descricao="Quando o Back-End disponibilizar a consulta, seus agendamentos aparecerão aqui."
          tipo="vazio"
          titulo="Nenhum dado para consultar agora"
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { gap: espacamentos.muitoGrande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  cabecalho: { gap: espacamentos.pequeno },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 24 },
  cartaoInformativo: { backgroundColor: cores.principalClaro, gap: espacamentos.pequeno },
  tituloCartao: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  textoCartao: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal, lineHeight: 20 },
});
