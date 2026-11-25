import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useNavigation } from '@react-navigation/native';
import { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useContextoAutenticacao } from '../autenticacao';
import { BotaoPrimario, Cartao, EstadoFeedback } from '../componentes';
import type { ParametrosRaiz } from '../navegacao/NavegacaoPrincipal';
import { consultarHome, ErroHttp, type RespostaHome } from '../servicos';
import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

type EstadoPerfil = 'CARREGANDO' | 'SUCESSO' | 'ERRO';
type DestinoPerfil = 'InformacoesBasicas' | 'Seguranca' | 'CadastroPerfil';

const categorias: { destino: DestinoPerfil; descricao: string; icone: string; titulo: string }[] = [
  { destino: 'InformacoesBasicas', descricao: 'Nome, nome de usuário e e-mail.', icone: '◉', titulo: 'Informações básicas' },
  { destino: 'Seguranca', descricao: 'Opções relacionadas à senha.', icone: '⌁', titulo: 'Segurança' },
  { destino: 'CadastroPerfil', descricao: 'Dados informados para seu cadastro.', icone: '✚', titulo: 'Cadastro' },
];

export function Perfil() {
  const navegacao = useNavigation<NativeStackNavigationProp<ParametrosRaiz>>();
  const { clienteHttp, encerrarSessao } = useContextoAutenticacao();
  const [estadoPerfil, definirEstadoPerfil] = useState<EstadoPerfil>('CARREGANDO');
  const [home, definirHome] = useState<RespostaHome>();
  const [mensagemErro, definirMensagemErro] = useState('');
  const [encerrandoSessao, definirEncerrandoSessao] = useState(false);

  const carregarPerfil = useCallback(async (signal?: AbortSignal) => {
    definirEstadoPerfil('CARREGANDO');
    definirMensagemErro('');

    try {
      const resposta = await consultarHome(clienteHttp, signal);
      if (signal?.aborted) return;
      definirHome(resposta);
      definirEstadoPerfil('SUCESSO');
    } catch (erro) {
      if (signal?.aborted) return;
      definirHome(undefined);
      definirMensagemErro(obterMensagemErro(erro));
      definirEstadoPerfil('ERRO');
    }
  }, [clienteHttp]);

  useEffect(() => {
    const controlador = new AbortController();
    void carregarPerfil(controlador.signal);
    return () => controlador.abort();
  }, [carregarPerfil]);

  const doador = home?.doador;
  const nome = doador?.nome;
  const tipoSanguineo = doador?.tipoSanguineo ?? doador?.tipo_sanguineo;

  async function sairDaConta() {
    definirEncerrandoSessao(true);

    try {
      await encerrarSessao();
    } finally {
      definirEncerrandoSessao(false);
    }
  }

  function abrirCategoria(destino: DestinoPerfil) {
    if (destino === 'InformacoesBasicas') {
      navegacao.navigate(destino, { nome });
      return;
    }

    if (destino === 'CadastroPerfil') {
      navegacao.navigate(destino, { tipoSanguineo });
      return;
    }

    navegacao.navigate(destino);
  }

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <Pressable accessibilityRole="button" onPress={() => navegacao.goBack()} style={estilos.voltar}>
          <Text style={estilos.textoVoltar}>← Voltar</Text>
        </Pressable>

        <View style={estilos.cabecalho}>
          <View style={estilos.avatar}>
            <Text style={estilos.iniciais}>{obterIniciais(nome)}</Text>
          </View>
          <View style={estilos.detalhesCabecalho}>
            <Text style={estilos.titulo}>Meu perfil</Text>
            <Text style={estilos.nome}>{nome ?? 'Informação não disponível'}</Text>
          </View>
        </View>

        {estadoPerfil === 'CARREGANDO' && <EstadoFeedback tipo="carregando" titulo="Carregando seu perfil" />}
        {estadoPerfil === 'ERRO' && (
          <EstadoFeedback
            aoTentarNovamente={() => void carregarPerfil()}
            descricao={mensagemErro}
            tipo="erro"
            titulo="Não foi possível carregar seu perfil"
          />
        )}

        {estadoPerfil === 'SUCESSO' && (
          <View style={estilos.listaCategorias}>
            {categorias.map((categoria) => (
              <Pressable
                accessibilityRole="button"
                key={categoria.destino}
                onPress={() => abrirCategoria(categoria.destino)}
                style={({ pressed }) => [estilos.categoriaPressionavel, pressed && estilos.categoriaPressionada]}
              >
                <Cartao estilo={estilos.categoria}>
                  <View style={estilos.iconeCategoria}>
                    <Text style={estilos.textoIcone}>{categoria.icone}</Text>
                  </View>
                  <View style={estilos.detalhesCategoria}>
                    <Text style={estilos.tituloCategoria}>{categoria.titulo}</Text>
                    <Text style={estilos.descricaoCategoria}>{categoria.descricao}</Text>
                  </View>
                  <Text accessibilityElementsHidden style={estilos.seta}>›</Text>
                </Cartao>
              </Pressable>
            ))}
          </View>
        )}

        <View style={estilos.areaSaida}>
          <Text style={estilos.descricaoSaida}>Deseja usar outra conta?</Text>
          <BotaoPrimario
            aoPressionar={() => void sairDaConta()}
            carregando={encerrandoSessao}
            titulo="Encerrar sessão"
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function obterIniciais(nome?: string): string {
  if (!nome) return '•';
  return nome.trim().split(/\s+/).slice(0, 2).map((parte) => parte[0]?.toUpperCase()).join('');
}

function obterMensagemErro(erro: unknown): string {
  if (erro instanceof ErroHttp) return erro.problema.detail ?? erro.problema.title;
  return erro instanceof Error ? erro.message : 'Tente novamente em alguns instantes.';
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { gap: espacamentos.muitoGrande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  voltar: { alignSelf: 'flex-start', justifyContent: 'center', minHeight: 44, paddingHorizontal: espacamentos.pequeno },
  textoVoltar: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  cabecalho: { alignItems: 'center', flexDirection: 'row', gap: espacamentos.padrao },
  avatar: { alignItems: 'center', backgroundColor: cores.principal, borderRadius: raiosBorda.arredondada, height: 64, justifyContent: 'center', width: 64 },
  iniciais: { color: cores.cartao, fontSize: tamanhosFonte.subtitulo, fontWeight: pesosFonte.negrito },
  detalhesCabecalho: { flex: 1, gap: espacamentos.minimo },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  nome: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.medio },
  listaCategorias: { gap: espacamentos.medio },
  categoriaPressionavel: { borderRadius: raiosBorda.grande },
  categoriaPressionada: { opacity: 0.78 },
  categoria: { alignItems: 'center', flexDirection: 'row', gap: espacamentos.medio },
  iconeCategoria: { alignItems: 'center', backgroundColor: cores.principalClaro, borderRadius: raiosBorda.media, height: 44, justifyContent: 'center', width: 44 },
  textoIcone: { color: cores.principalEscuro, fontSize: tamanhosFonte.subtitulo, fontWeight: pesosFonte.negrito },
  detalhesCategoria: { flex: 1, gap: espacamentos.minimo },
  tituloCategoria: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  descricaoCategoria: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  seta: { color: cores.principalEscuro, fontSize: tamanhosFonte.cabecalho, fontWeight: pesosFonte.normal },
  areaSaida: { gap: espacamentos.pequeno, marginTop: espacamentos.medio },
  descricaoSaida: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal, textAlign: 'center' },
});
