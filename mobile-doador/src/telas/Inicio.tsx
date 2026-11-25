import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import type { CompositeNavigationProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useNavigation } from '@react-navigation/native';
import { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useContextoAutenticacao } from '../autenticacao';
import { Cartao, EstadoFeedback, SeloStatus } from '../componentes';
import type { ParametrosAbas } from '../navegacao/NavegacaoAbas';
import type { ParametrosRaiz } from '../navegacao/NavegacaoPrincipal';
import { ErroHttp, type RespostaHome } from '../servicos';
import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

type DestinoAtalho = Exclude<keyof ParametrosAbas, 'Inicio'>;
type EstadoCarregamento = 'CARREGANDO' | 'SUCESSO' | 'ERRO';
type NavegacaoInicio = CompositeNavigationProp<
  BottomTabNavigationProp<ParametrosAbas>,
  NativeStackNavigationProp<ParametrosRaiz>
>;

const atalhos: { titulo: string; icone: string; destino: DestinoAtalho }[] = [
  { titulo: 'Agendar doação', icone: '+', destino: 'Agendar' },
  { titulo: 'Meus pedidos', icone: '☰', destino: 'MeusPedidos' },
  { titulo: 'Assistente', icone: '?', destino: 'Assistente' },
];

export function Inicio() {
  const navegacao = useNavigation<NavegacaoInicio>();
  const { clienteHttp } = useContextoAutenticacao();
  const [estadoCarregamento, definirEstadoCarregamento] = useState<EstadoCarregamento>('CARREGANDO');
  const [respostaHome, definirRespostaHome] = useState<RespostaHome | null>(null);
  const [mensagemErro, definirMensagemErro] = useState('');

  const carregarHome = useCallback(async (signal?: AbortSignal) => {
    definirEstadoCarregamento('CARREGANDO');
    definirMensagemErro('');

    try {
      const resposta = await clienteHttp.requisitar<RespostaHome>('/api/mobile/home', { signal });

      if (!resposta.corpo) {
        throw new Error('A resposta da Home não contém informações para exibir.');
      }

      definirRespostaHome(resposta.corpo);
      definirEstadoCarregamento('SUCESSO');
    } catch (erro) {
      if (signal?.aborted) return;

      definirRespostaHome(null);
      definirEstadoCarregamento('ERRO');
      definirMensagemErro(obterMensagemErro(erro));
    }
  }, [clienteHttp]);

  useEffect(() => {
    const controlador = new AbortController();
    void carregarHome(controlador.signal);
    return () => controlador.abort();
  }, [carregarHome]);

  const doador = respostaHome?.doador;
  const nomeDoador = doador?.nome;
  const tipoSanguineo = doador?.tipoSanguineo ?? doador?.tipo_sanguineo;
  const perfilNaoCadastrado = doador?.cadastrado === false;

  return (
    <SafeAreaView edges={['right', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <View style={estilos.cabecalho}>
          <View>
            <Text style={estilos.saudacao}>{nomeDoador ? `Olá, ${nomeDoador}` : 'Olá'}</Text>
            <Text style={estilos.subtitulo}>Que bom ter você por aqui.</Text>
          </View>
          <Pressable
            accessibilityLabel="Abrir meu perfil"
            accessibilityRole="button"
            onPress={() => navegacao.navigate('Perfil')}
            style={({ pressed }) => [estilos.avatarPerfil, pressed && estilos.avatarPerfilPressionado]}
          >
            <Text style={estilos.iniciaisPerfil}>{obterIniciais(nomeDoador)}</Text>
          </Pressable>
        </View>

        <SecaoAtalhos navegacao={navegacao} />

        {estadoCarregamento === 'CARREGANDO' && <EstadoFeedback tipo="carregando" titulo="Carregando sua Home" />}

        {estadoCarregamento === 'ERRO' && (
          <EstadoFeedback
            aoTentarNovamente={() => void carregarHome()}
            descricao={mensagemErro}
            tipo="erro"
            titulo="Não foi possível carregar sua Home"
          />
        )}

        {estadoCarregamento === 'SUCESSO' && respostaHome && (
          <>
            <Cartao estilo={estilos.cartaoPerfil}>
              {perfilNaoCadastrado ? (
                <View style={estilos.detalhesPerfil}>
                  <Text style={estilos.rotuloCartao}>Seu perfil</Text>
                  <Text style={estilos.nomeDoador}>Perfil não cadastrado</Text>
                  <Text style={estilos.descricaoPerfil}>Complete seu cadastro para receber campanhas personalizadas.</Text>
                </View>
              ) : respostaHome.doador.statusDegradado ? (
                <View style={estilos.detalhesPerfil}>
                  <Text style={estilos.rotuloCartao}>Seu perfil</Text>
                  <Text style={estilos.nomeDoador}>Perfil temporariamente indisponível</Text>
                  <Text style={estilos.descricaoPerfil}>Não foi possível consultar suas informações agora.</Text>
                </View>
              ) : (
                <>
                  <View style={estilos.detalhesPerfil}>
                    <Text style={estilos.rotuloCartao}>Seu perfil</Text>
                    {nomeDoador && <Text style={estilos.nomeDoador}>{nomeDoador}</Text>}
                    {!nomeDoador && <Text style={estilos.descricaoPerfil}>Nome não informado no perfil.</Text>}
                  </View>
                  {tipoSanguineo && (
                    <View style={estilos.tipoSanguineo}>
                      <Text style={estilos.rotuloTipoSanguineo}>Tipo sanguíneo</Text>
                      <Text style={estilos.valorTipoSanguineo}>{tipoSanguineo}</Text>
                    </View>
                  )}
                </>
              )}
            </Cartao>

            {respostaHome.status === 'degradado' && (
              <Cartao estilo={estilos.avisoDegradado}>
                <Text style={estilos.tituloAviso}>Algumas informações podem estar indisponíveis</Text>
                <Text style={estilos.descricaoAviso}>{descreverServicosIndisponiveis(respostaHome.servicosIndisponiveis)}</Text>
              </Cartao>
            )}

            <View style={estilos.secao}>
              <View style={estilos.cabecalhoSecao}>
                <Text style={estilos.tituloSecao}>{respostaHome.campanhasPersonalizadas ? 'Campanhas para você' : 'Campanhas vigentes'}</Text>
                {!respostaHome.campanhasPersonalizadas && <Text style={estilos.avisoNaoPersonalizado}>Não personalizadas</Text>}
              </View>
              {!respostaHome.campanhasPersonalizadas && (
                <Text style={estilos.descricaoNaoPersonalizada}>Estas campanhas não foram filtradas pelo seu tipo sanguíneo.</Text>
              )}
              {respostaHome.campanhas.length === 0 ? (
                <EstadoFeedback descricao="Não há campanhas vigentes para mostrar no momento." tipo="vazio" titulo="Nenhuma campanha disponível" />
              ) : (
                respostaHome.campanhas.map((campanha) => (
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
                ))
              )}
            </View>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function SecaoAtalhos({ navegacao }: { navegacao: NavegacaoInicio }) {
  return (
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
  );
}

function obterMensagemErro(erro: unknown): string {
  if (erro instanceof ErroHttp) return erro.problema.detail ?? erro.problema.title;
  return erro instanceof Error ? erro.message : 'Tente novamente em alguns instantes.';
}

function obterIniciais(nome?: string): string {
  if (!nome) return '•';
  return nome.trim().split(/\s+/).slice(0, 2).map((parte) => parte[0]?.toUpperCase()).join('');
}

function formatarPeriodo(dataInicio: string, dataFim: string): string {
  return `${formatarData(dataInicio)} a ${formatarData(dataFim)}`;
}

function formatarData(data: string): string {
  const partes = data.split('-');
  return partes.length === 3 ? `${partes[2]}/${partes[1]}/${partes[0]}` : data;
}

function descreverServicosIndisponiveis(servicos: string[]): string {
  if (servicos.length === 0) return 'Algumas informações não puderam ser atualizadas agora.';
  return `Não foi possível consultar: ${servicos.join(', ')}.`;
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { gap: espacamentos.muitoGrande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  cabecalho: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  saudacao: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  subtitulo: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, marginTop: espacamentos.minimo },
  avatarPerfil: { alignItems: 'center', backgroundColor: cores.principalClaro, borderRadius: raiosBorda.arredondada, height: 48, justifyContent: 'center', width: 48 },
  avatarPerfilPressionado: { opacity: 0.78 },
  iniciaisPerfil: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.negrito },
  cartaoPerfil: { alignItems: 'center', flexDirection: 'row', gap: espacamentos.padrao, justifyContent: 'space-between' },
  detalhesPerfil: { flex: 1, gap: espacamentos.minimo },
  rotuloCartao: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  nomeDoador: { color: cores.texto, fontSize: tamanhosFonte.subtitulo, fontWeight: pesosFonte.seminegrito },
  descricaoPerfil: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  tipoSanguineo: { alignItems: 'center', backgroundColor: cores.principalClaro, borderRadius: raiosBorda.media, paddingHorizontal: espacamentos.medio, paddingVertical: espacamentos.pequeno },
  rotuloTipoSanguineo: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  valorTipoSanguineo: { color: cores.principalEscuro, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  avisoDegradado: { backgroundColor: cores.principalClaro, gap: espacamentos.minimo },
  tituloAviso: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  descricaoAviso: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  secao: { gap: espacamentos.medio },
  cabecalhoSecao: { alignItems: 'center', flexDirection: 'row', gap: espacamentos.pequeno, justifyContent: 'space-between' },
  tituloSecao: { color: cores.texto, fontSize: tamanhosFonte.subtitulo, fontWeight: pesosFonte.negrito },
  avisoNaoPersonalizado: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  descricaoNaoPersonalizada: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
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
  rodapeCampanha: { alignItems: 'center', flexDirection: 'row', gap: espacamentos.pequeno, justifyContent: 'space-between' },
  tipoCampanha: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
  periodoCampanha: { color: cores.textoSecundario, flexShrink: 1, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal, textAlign: 'right' },
});
