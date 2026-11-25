import { Ionicons } from '@expo/vector-icons';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Cartao } from '../componentes';
import type { ParametrosRaiz } from '../navegacao/NavegacaoPrincipal';
import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

export function CadastroPerfil() {
  const navegacao = useNavigation<NativeStackNavigationProp<ParametrosRaiz>>();
  const rota = useRoute<RouteProp<ParametrosRaiz, 'CadastroPerfil'>>();
  const dataNascimento = formatarData(rota.params?.dataNascimento);
  const dataUltimaDoacao = formatarData(rota.params?.dataUltimaDoacao);
  const sexo = formatarSexo(rota.params?.sexo);
  const tipoSanguineo = rota.params?.tipoSanguineo;

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <Pressable accessibilityLabel="Voltar para Meu perfil" accessibilityRole="button" onPress={() => navegacao.goBack()} style={estilos.voltar}>
          <Ionicons color={cores.principalEscuro} name="arrow-back" size={20} />
          <Text style={estilos.textoVoltar}>Voltar</Text>
        </Pressable>
        <View style={estilos.cabecalho}>
          <Text style={estilos.titulo}>Cadastro</Text>
          <Text style={estilos.descricao}>Informações registradas para seu perfil de doador.</Text>
        </View>
        <Cartao estilo={estilos.cartao}>
          <Informacao icone="heart-outline" rotulo="Tipo sanguíneo" valor={tipoSanguineo} />
          <Informacao icone="person-outline" rotulo="Sexo" valor={sexo} />
          <Informacao icone="gift-outline" rotulo="Data de nascimento" valor={dataNascimento} />
          <Informacao icone="calendar-outline" rotulo="Data da última doação" valor={dataUltimaDoacao} />
        </Cartao>
      </ScrollView>
    </SafeAreaView>
  );
}

function formatarSexo(sexo?: 'M' | 'F'): string | undefined {
  if (sexo === 'M') return 'Masculino';
  if (sexo === 'F') return 'Feminino';
  return undefined;
}

function formatarData(data?: string | null): string | undefined {
  if (data === null) return 'Não informado';
  if (!data || !/^\d{4}-\d{2}-\d{2}$/.test(data)) return undefined;

  const [ano, mes, dia] = data.split('-').map(Number);
  const dataFormatada = new Date(ano, mes - 1, dia);
  const dataValida = dataFormatada.getFullYear() === ano
    && dataFormatada.getMonth() === mes - 1
    && dataFormatada.getDate() === dia;

  return dataValida ? `${dia.toString().padStart(2, '0')}/${mes.toString().padStart(2, '0')}/${ano}` : undefined;
}

function Informacao({ icone, rotulo, valor }: { icone: keyof typeof Ionicons.glyphMap; rotulo: string; valor?: string }) {
  return (
    <View style={estilos.informacao}>
      <View style={estilos.iconeInformacao}>
        <Ionicons color={cores.principalEscuro} name={icone} size={19} />
      </View>
      <View style={estilos.detalhesInformacao}>
        <Text style={estilos.rotulo}>{rotulo}</Text>
        <Text style={valor ? estilos.valor : estilos.indisponivel}>{valor ?? 'Informação não disponível'}</Text>
      </View>
    </View>
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
  informacao: { alignItems: 'center', flexDirection: 'row', gap: espacamentos.medio },
  iconeInformacao: { alignItems: 'center', backgroundColor: cores.principalClaro, borderRadius: raiosBorda.media, height: 36, justifyContent: 'center', width: 36 },
  detalhesInformacao: { flex: 1, gap: espacamentos.minimo },
  rotulo: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  valor: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  indisponivel: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal },
});
