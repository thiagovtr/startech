import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Cartao, EstadoFeedback, SeloStatus } from '../componentes';
import type { ParametrosRaiz } from '../navegacao/NavegacaoPrincipal';
import { cores, espacamentos, pesosFonte, tamanhosFonte } from '../tema';

export function TodasCampanhas() {
  const navegacao = useNavigation<NativeStackNavigationProp<ParametrosRaiz>>();
  const rota = useRoute<RouteProp<ParametrosRaiz, 'TodasCampanhas'>>();
  const { campanhas, campanhasPersonalizadas } = rota.params;

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <Pressable accessibilityRole="button" onPress={() => navegacao.goBack()} style={estilos.voltar}>
          <Text style={estilos.textoVoltar}>← Voltar para Início</Text>
        </Pressable>

        <View style={estilos.cabecalho}>
          <Text style={estilos.titulo}>{campanhasPersonalizadas ? 'Campanhas para você' : 'Campanhas vigentes'}</Text>
          <Text style={estilos.descricao}>Exibimos todas as campanhas retornadas pela sua Home.</Text>
          {!campanhasPersonalizadas && <Text style={estilos.avisoNaoPersonalizado}>Estas campanhas não foram filtradas pelo seu tipo sanguíneo.</Text>}
        </View>

        {campanhas.length === 0 ? (
          <EstadoFeedback
            descricao="Não há campanhas vigentes para mostrar no momento."
            tipo="vazio"
            titulo="Nenhuma campanha disponível"
          />
        ) : (
          <View style={estilos.listaCampanhas}>
            {campanhas.map((campanha) => (
              <Cartao estilo={estilos.cartaoCampanha} key={campanha.id}>
                <View style={estilos.linhaCampanha}>
                  <View style={estilos.detalhesCampanha}>
                    <Text style={estilos.tituloCampanha}>{campanha.titulo}</Text>
                    <Text style={estilos.hemocentro}>{campanha.hemocentro}</Text>
                  </View>
                  <SeloStatus situacao={campanha.urgencia} />
                </View>
                <View style={estilos.rodapeCampanha}>
                  <Text style={estilos.tipoCampanha}>Tipo {campanha.tipo_sanguineo}</Text>
                  <Text style={estilos.periodoCampanha}>{formatarPeriodo(campanha.data_inicio, campanha.data_fim)}</Text>
                </View>
              </Cartao>
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function formatarPeriodo(dataInicio: string, dataFim: string): string {
  return `${formatarData(dataInicio)} a ${formatarData(dataFim)}`;
}

function formatarData(data: string): string {
  const partes = data.split('-');
  return partes.length === 3 ? `${partes[2]}/${partes[1]}/${partes[0]}` : data;
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { gap: espacamentos.muitoGrande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  voltar: { alignSelf: 'flex-start', justifyContent: 'center', minHeight: 44, paddingHorizontal: espacamentos.pequeno },
  textoVoltar: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  cabecalho: { gap: espacamentos.pequeno },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal },
  avisoNaoPersonalizado: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  listaCampanhas: { gap: espacamentos.medio },
  cartaoCampanha: { gap: espacamentos.padrao },
  linhaCampanha: { alignItems: 'flex-start', flexDirection: 'row', gap: espacamentos.pequeno, justifyContent: 'space-between' },
  detalhesCampanha: { flex: 1, gap: espacamentos.minimo },
  tituloCampanha: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  hemocentro: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  rodapeCampanha: { alignItems: 'center', flexDirection: 'row', gap: espacamentos.pequeno, justifyContent: 'space-between' },
  tipoCampanha: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
  periodoCampanha: { color: cores.textoSecundario, flexShrink: 1, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal, textAlign: 'right' },
});
