import { Ionicons } from '@expo/vector-icons';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useNavigation } from '@react-navigation/native';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Cartao } from '../componentes';
import type { ParametrosRaiz } from '../navegacao/NavegacaoPrincipal';
import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

export function Seguranca() {
  const navegacao = useNavigation<NativeStackNavigationProp<ParametrosRaiz>>();

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <Pressable accessibilityLabel="Voltar para Meu perfil" accessibilityRole="button" onPress={() => navegacao.goBack()} style={estilos.voltar}>
          <Ionicons color={cores.principalEscuro} name="arrow-back" size={20} />
          <Text style={estilos.textoVoltar}>Voltar</Text>
        </Pressable>
        <View style={estilos.cabecalho}>
          <Text style={estilos.titulo}>Segurança</Text>
          <Text style={estilos.descricao}>Gerencie as opções de acesso à sua conta.</Text>
        </View>
        <Cartao estilo={estilos.cartao}>
          <View style={estilos.linhaOpcao}>
            <View style={estilos.icone}><Ionicons color={cores.principalEscuro} name="lock-closed-outline" size={21} /></View>
            <View style={estilos.detalhesOpcao}>
              <Text style={estilos.tituloOpcao}>Alterar senha</Text>
              <Text style={estilos.descricaoOpcao}>Esta funcionalidade ainda não está disponível no aplicativo.</Text>
            </View>
          </View>
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ disabled: true }}
            disabled
            style={estilos.acaoDesabilitada}
          >
            <Text style={estilos.textoAcaoDesabilitada}>Indisponível</Text>
          </Pressable>
        </Cartao>
      </ScrollView>
    </SafeAreaView>
  );
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { gap: espacamentos.muitoGrande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  voltar: { alignItems: 'center', alignSelf: 'flex-start', flexDirection: 'row', gap: espacamentos.pequeno, justifyContent: 'center', minHeight: 44, paddingHorizontal: espacamentos.pequeno },
  textoVoltar: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  cabecalho: { gap: espacamentos.pequeno },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal },
  cartao: { gap: espacamentos.medio, padding: espacamentos.medio },
  linhaOpcao: { alignItems: 'center', flexDirection: 'row', gap: espacamentos.medio },
  icone: { alignItems: 'center', backgroundColor: cores.principalClaro, borderRadius: raiosBorda.media, height: 44, justifyContent: 'center', width: 44 },
  detalhesOpcao: { flex: 1, gap: espacamentos.minimo },
  tituloOpcao: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  descricaoOpcao: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  acaoDesabilitada: { alignSelf: 'flex-start', backgroundColor: cores.principalClaro, borderRadius: raiosBorda.media, minHeight: 40, justifyContent: 'center', paddingHorizontal: espacamentos.medio },
  textoAcaoDesabilitada: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
});
