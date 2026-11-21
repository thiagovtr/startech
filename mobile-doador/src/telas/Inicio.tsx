import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import { useNavigation } from '@react-navigation/native';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Cartao, SeloStatus, type SituacaoSelo } from '../componentes';
import type { ParametrosAbas } from '../navegacao/NavegacaoAbas';
import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

type CampanhaDemonstracao = {
  titulo: string;
  hemocentro: string;
  tipoSanguineo: string;
  situacao: SituacaoSelo;
  periodo: string;
};

// Dados temporários para visualização da interface antes da integração com o Back-End.
const campanhasDemonstracao: CampanhaDemonstracao[] = [
  {
    titulo: 'Campanha de doação',
    hemocentro: 'Hemocentro Municipal',
    tipoSanguineo: 'O+',
    situacao: 'CRITICO',
    periodo: '10 a 24 de novembro',
  },
  {
    titulo: 'Doe e ajude a salvar vidas',
    hemocentro: 'Unidade de Coleta Central',
    tipoSanguineo: 'O+',
    situacao: 'NORMAL',
    periodo: '1 a 30 de novembro',
  },
];

type DestinoAtalho = Exclude<keyof ParametrosAbas, 'Inicio'>;

const atalhos: { titulo: string; icone: string; destino: DestinoAtalho }[] = [
  { titulo: 'Agendar doação', icone: '+', destino: 'Agendar' },
  { titulo: 'Meus pedidos', icone: '☰', destino: 'MeusPedidos' },
  { titulo: 'Assistente', icone: '?', destino: 'Assistente' },
];

export function Inicio() {
  const navegacao = useNavigation<BottomTabNavigationProp<ParametrosAbas>>();

  return (
    <SafeAreaView edges={['right', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <View style={estilos.cabecalho}>
          <View>
            <Text style={estilos.saudacao}>Olá, Doador</Text>
            <Text style={estilos.subtitulo}>Que bom ter você por aqui.</Text>
          </View>
          <View accessibilityLabel="Perfil do doador" style={estilos.avatarPerfil}>
            <Text style={estilos.iniciaisPerfil}>DS</Text>
          </View>
        </View>

        <Cartao estilo={estilos.cartaoPerfil}>
          <View>
            <Text style={estilos.rotuloCartao}>Seu perfil</Text>
            <Text style={estilos.nomeDoador}>Doador StarTech</Text>
          </View>
          <View style={estilos.tipoSanguineo}>
            <Text style={estilos.rotuloTipoSanguineo}>Tipo sanguíneo</Text>
            <Text style={estilos.valorTipoSanguineo}>O+</Text>
          </View>
        </Cartao>

        <View style={estilos.secao}>
          <Text style={estilos.tituloSecao}>Ações rápidas</Text>
          <View style={estilos.gradeAtalhos}>
            {atalhos.map(({ titulo, icone, destino }) => (
              <Pressable
                accessibilityRole="button"
                key={destino}
                onPress={() => navegacao.navigate(destino)}
                style={({ pressed }) => [estilos.atalho, pressed && estilos.atalhoPressionado]}
              >
                <Text style={estilos.iconeAtalho}>{icone}</Text>
                <Text style={estilos.tituloAtalho}>{titulo}</Text>
              </Pressable>
            ))}
          </View>
        </View>

        <View style={estilos.secao}>
          <View style={estilos.cabecalhoSecao}>
            <Text style={estilos.tituloSecao}>Campanhas para você</Text>
            <Text style={estilos.avisoDemonstracao}>Demonstração</Text>
          </View>
          {campanhasDemonstracao.map((campanha) => (
            <Cartao estilo={estilos.cartaoCampanha} key={`${campanha.titulo}-${campanha.hemocentro}`}>
              <View style={estilos.linhaCampanha}>
                <View style={estilos.detalhesCampanha}>
                  <Text style={estilos.tituloCampanha}>{campanha.titulo}</Text>
                  <Text style={estilos.hemocentro}>{campanha.hemocentro}</Text>
                </View>
                <SeloStatus situacao={campanha.situacao} />
              </View>
              <View style={estilos.rodapeCampanha}>
                <Text style={estilos.tipoCampanha}>Tipo {campanha.tipoSanguineo}</Text>
                <Text style={estilos.periodoCampanha}>{campanha.periodo}</Text>
              </View>
            </Cartao>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { gap: espacamentos.muitoGrande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  cabecalho: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  saudacao: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  subtitulo: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, marginTop: espacamentos.minimo },
  avatarPerfil: { alignItems: 'center', backgroundColor: cores.principalClaro, borderRadius: raiosBorda.arredondada, height: 48, justifyContent: 'center', width: 48 },
  iniciaisPerfil: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.negrito },
  cartaoPerfil: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  rotuloCartao: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  nomeDoador: { color: cores.texto, fontSize: tamanhosFonte.subtitulo, fontWeight: pesosFonte.seminegrito, marginTop: espacamentos.minimo },
  tipoSanguineo: { alignItems: 'center', backgroundColor: cores.principalClaro, borderRadius: raiosBorda.media, paddingHorizontal: espacamentos.medio, paddingVertical: espacamentos.pequeno },
  rotuloTipoSanguineo: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  valorTipoSanguineo: { color: cores.principalEscuro, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  secao: { gap: espacamentos.medio },
  cabecalhoSecao: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  tituloSecao: { color: cores.texto, fontSize: tamanhosFonte.subtitulo, fontWeight: pesosFonte.negrito },
  avisoDemonstracao: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  gradeAtalhos: { flexDirection: 'row', flexWrap: 'wrap', gap: espacamentos.medio },
  atalho: { backgroundColor: cores.cartao, borderRadius: raiosBorda.grande, flexBasis: '47%', flexGrow: 1, gap: espacamentos.pequeno, minHeight: 108, padding: espacamentos.padrao },
  atalhoPressionado: { backgroundColor: cores.principalClaro },
  iconeAtalho: { color: cores.principal, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  tituloAtalho: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  cartaoCampanha: { gap: espacamentos.padrao },
  linhaCampanha: { alignItems: 'flex-start', flexDirection: 'row', gap: espacamentos.pequeno, justifyContent: 'space-between' },
  detalhesCampanha: { flex: 1, gap: espacamentos.minimo },
  tituloCampanha: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  hemocentro: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  rodapeCampanha: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  tipoCampanha: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
  periodoCampanha: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
});
