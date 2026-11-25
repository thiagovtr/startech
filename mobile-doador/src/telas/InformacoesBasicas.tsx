import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Cartao } from '../componentes';
import type { ParametrosRaiz } from '../navegacao/NavegacaoPrincipal';
import { cores, espacamentos, pesosFonte, tamanhosFonte } from '../tema';

export function InformacoesBasicas() {
  const navegacao = useNavigation<NativeStackNavigationProp<ParametrosRaiz>>();
  const rota = useRoute<RouteProp<ParametrosRaiz, 'InformacoesBasicas'>>();
  const nome = rota.params?.nome;

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <Pressable accessibilityRole="button" onPress={() => navegacao.goBack()} style={estilos.voltar}>
          <Text style={estilos.textoVoltar}>← Meu perfil</Text>
        </Pressable>
        <View style={estilos.cabecalho}>
          <Text style={estilos.titulo}>Informações básicas</Text>
          <Text style={estilos.descricao}>Dados associados à sua conta no StarTech.</Text>
        </View>
        <Cartao estilo={estilos.cartao}>
          <Informacao rotulo="Nome completo" valor={nome} />
          <Informacao rotulo="Nome de usuário" />
          <Informacao rotulo="E-mail" />
        </Cartao>
      </ScrollView>
    </SafeAreaView>
  );
}

function Informacao({ rotulo, valor }: { rotulo: string; valor?: string }) {
  return (
    <View style={estilos.informacao}>
      <Text style={estilos.rotulo}>{rotulo}</Text>
      <Text style={valor ? estilos.valor : estilos.indisponivel}>{valor ?? 'Informação não disponível'}</Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { gap: espacamentos.muitoGrande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  voltar: { alignSelf: 'flex-start', justifyContent: 'center', minHeight: 44, paddingHorizontal: espacamentos.pequeno },
  textoVoltar: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  cabecalho: { gap: espacamentos.pequeno },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal },
  cartao: { gap: espacamentos.padrao },
  informacao: { gap: espacamentos.minimo },
  rotulo: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  valor: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  indisponivel: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal },
});
