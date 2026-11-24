import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useContextoAutenticacao } from '../autenticacao';
import { BotaoPrimario, Cartao } from '../componentes';
import { ErroHttp, salvarPerfil, type FormularioPerfil, type SexoDoador, type TipoSanguineo } from '../servicos';
import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

type PropriedadesCompletarPerfil = {
  aoConcluir: () => void;
};

const tiposSanguineos: TipoSanguineo[] = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];

const opcoesSexo: { valor: SexoDoador; titulo: string }[] = [
  { valor: 'M', titulo: 'Masculino (M)' },
  { valor: 'F', titulo: 'Feminino (F)' },
];

export function CompletarPerfil({ aoConcluir }: PropriedadesCompletarPerfil) {
  const { clienteHttp, encerrarSessao } = useContextoAutenticacao();
  const [nome, definirNome] = useState('');
  const [tipoSanguineo, definirTipoSanguineo] = useState<TipoSanguineo>();
  const [sexo, definirSexo] = useState<SexoDoador>();
  const [dataUltimaDoacao, definirDataUltimaDoacao] = useState('');
  const [erros, definirErros] = useState<string[]>([]);
  const [salvando, definirSalvando] = useState(false);
  const [encerrandoSessao, definirEncerrandoSessao] = useState(false);

  async function enviarPerfil() {
    const dados = prepararDadosPerfil(nome, tipoSanguineo, sexo, dataUltimaDoacao);

    if (Array.isArray(dados)) {
      definirErros(dados);
      return;
    }

    definirSalvando(true);
    definirErros([]);

    try {
      await salvarPerfil(clienteHttp, dados);
      aoConcluir();
    } catch (erro) {
      definirErros(obterMensagensErro(erro));
    } finally {
      definirSalvando(false);
    }
  }

  async function sairDaConta() {
    definirEncerrandoSessao(true);

    try {
      await encerrarSessao();
    } finally {
      definirEncerrandoSessao(false);
    }
  }

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={estilos.areaSegura}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={estilos.areaFlexivel}>
        <ScrollView contentContainerStyle={estilos.conteudo} keyboardShouldPersistTaps="handled">
          <View style={estilos.cabecalho}>
            <Text style={estilos.titulo}>Complete seu cadastro</Text>
            <Text style={estilos.descricao}>
              Precisamos de alguns dados para personalizar sua experiência no StarTech.
            </Text>
          </View>

          <Cartao estilo={estilos.cartaoFormulario}>
            <Campo
              aoAlterarTexto={definirNome}
              autoCapitalize="words"
              maxLength={120}
              texto={nome}
              titulo="Nome completo"
            />

            <View style={estilos.grupoCampo}>
              <Text style={estilos.rotulo}>Tipo sanguíneo</Text>
              <View style={estilos.gradeOpcoes}>
                {tiposSanguineos.map((tipo) => (
                  <OpcaoSelecionavel
                    key={tipo}
                    selecionada={tipoSanguineo === tipo}
                    aoPressionar={() => definirTipoSanguineo(tipo)}
                    titulo={tipo}
                  />
                ))}
              </View>
            </View>

            <View style={estilos.grupoCampo}>
              <Text style={estilos.rotulo}>Sexo</Text>
              <View style={estilos.listaOpcoes}>
                {opcoesSexo.map((opcao) => (
                  <OpcaoSelecionavel
                    key={opcao.valor}
                    selecionada={sexo === opcao.valor}
                    aoPressionar={() => definirSexo(opcao.valor)}
                    titulo={opcao.titulo}
                  />
                ))}
              </View>
            </View>

            <Campo
              aoAlterarTexto={definirDataUltimaDoacao}
              descricao="Opcional. Use o formato AAAA-MM-DD."
              keyboardType="numbers-and-punctuation"
              maxLength={10}
              placeholder="AAAA-MM-DD"
              texto={dataUltimaDoacao}
              titulo="Data da última doação"
            />

            {erros.length > 0 && (
              <View accessibilityLiveRegion="polite" style={estilos.areaErros}>
                <Text style={estilos.tituloErros}>Não foi possível salvar seu cadastro</Text>
                {erros.map((erro) => <Text key={erro} style={estilos.textoErro}>• {erro}</Text>)}
              </View>
            )}

            <BotaoPrimario aoPressionar={() => void enviarPerfil()} carregando={salvando} titulo="Salvar cadastro" />
          </Cartao>

          <View style={estilos.areaSaida}>
            <Text style={estilos.descricaoSaida}>Entrou com outra conta?</Text>
            <BotaoPrimario
              aoPressionar={() => void sairDaConta()}
              carregando={encerrandoSessao}
              desabilitado={salvando}
              titulo="Sair da conta"
            />
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

type PropriedadesCampo = {
  aoAlterarTexto: (texto: string) => void;
  autoCapitalize?: 'none' | 'sentences' | 'words' | 'characters';
  descricao?: string;
  keyboardType?: 'default' | 'numbers-and-punctuation';
  maxLength?: number;
  placeholder?: string;
  texto: string;
  titulo: string;
};

function Campo({
  aoAlterarTexto,
  autoCapitalize = 'none',
  descricao,
  keyboardType = 'default',
  maxLength,
  placeholder,
  texto,
  titulo,
}: PropriedadesCampo) {
  return (
    <View style={estilos.grupoCampo}>
      <Text style={estilos.rotulo}>{titulo}</Text>
      {descricao && <Text style={estilos.descricaoCampo}>{descricao}</Text>}
      <TextInput
        autoCapitalize={autoCapitalize}
        keyboardType={keyboardType}
        maxLength={maxLength}
        onChangeText={aoAlterarTexto}
        placeholder={placeholder}
        placeholderTextColor={cores.textoSecundario}
        style={estilos.entrada}
        value={texto}
      />
    </View>
  );
}

type PropriedadesOpcaoSelecionavel = {
  aoPressionar: () => void;
  selecionada: boolean;
  titulo: string;
};

function OpcaoSelecionavel({ aoPressionar, selecionada, titulo }: PropriedadesOpcaoSelecionavel) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: selecionada }}
      onPress={aoPressionar}
      style={({ pressed }) => [
        estilos.opcao,
        selecionada && estilos.opcaoSelecionada,
        pressed && !selecionada && estilos.opcaoPressionada,
      ]}
    >
      <Text style={[estilos.textoOpcao, selecionada && estilos.textoOpcaoSelecionada]}>{titulo}</Text>
    </Pressable>
  );
}

function prepararDadosPerfil(
  nome: string,
  tipoSanguineo: TipoSanguineo | undefined,
  sexo: SexoDoador | undefined,
  dataUltimaDoacao: string,
): FormularioPerfil | string[] {
  const nomeNormalizado = nome.trim();
  const dataNormalizada = dataUltimaDoacao.trim();
  const erros: string[] = [];

  if (nomeNormalizado.length < 2 || nomeNormalizado.length > 120) {
    erros.push('Informe seu nome completo com 2 a 120 caracteres.');
  }

  if (!tipoSanguineo) {
    erros.push('Selecione seu tipo sanguíneo.');
  }

  if (!sexo) {
    erros.push('Selecione seu sexo.');
  }

  if (dataNormalizada && !dataEhValida(dataNormalizada)) {
    erros.push('Informe uma data de última doação válida e que não seja futura.');
  }

  if (erros.length > 0 || !tipoSanguineo || !sexo) {
    return erros;
  }

  return {
    nome: nomeNormalizado,
    tipoSanguineo,
    sexo,
    ...(dataNormalizada ? { dataUltimaDoacao: dataNormalizada } : {}),
  };
}

function dataEhValida(data: string): boolean {
  const resultado = /^(\d{4})-(\d{2})-(\d{2})$/.exec(data);

  if (!resultado) return false;

  const ano = Number(resultado[1]);
  const mes = Number(resultado[2]);
  const dia = Number(resultado[3]);
  const dataInformada = new Date(ano, mes - 1, dia);

  if (
    dataInformada.getFullYear() !== ano
    || dataInformada.getMonth() !== mes - 1
    || dataInformada.getDate() !== dia
  ) {
    return false;
  }

  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  return dataInformada <= hoje;
}

function obterMensagensErro(erro: unknown): string[] {
  if (erro instanceof ErroHttp) {
    const parametrosInvalidos = erro.problema.invalidParams?.map((parametro) => `${parametro.name}: ${parametro.reason}`);
    return parametrosInvalidos?.length ? parametrosInvalidos : [erro.problema.detail ?? erro.problema.title];
  }

  return [erro instanceof Error ? erro.message : 'Não foi possível salvar seu cadastro. Tente novamente.'];
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  areaFlexivel: { flex: 1 },
  conteudo: { gap: espacamentos.muitoGrande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  cabecalho: { gap: espacamentos.pequeno },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 23 },
  cartaoFormulario: { gap: espacamentos.grande },
  grupoCampo: { gap: espacamentos.pequeno },
  rotulo: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  descricaoCampo: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  entrada: {
    backgroundColor: cores.fundo,
    borderColor: cores.principalClaro,
    borderRadius: raiosBorda.media,
    borderWidth: 1,
    color: cores.texto,
    fontSize: tamanhosFonte.corpo,
    minHeight: 48,
    paddingHorizontal: espacamentos.medio,
    paddingVertical: espacamentos.pequeno,
  },
  gradeOpcoes: { flexDirection: 'row', flexWrap: 'wrap', gap: espacamentos.pequeno },
  listaOpcoes: { gap: espacamentos.pequeno },
  opcao: {
    alignItems: 'center',
    backgroundColor: cores.fundo,
    borderColor: cores.principalClaro,
    borderRadius: raiosBorda.media,
    borderWidth: 1,
    justifyContent: 'center',
    minHeight: 48,
    paddingHorizontal: espacamentos.medio,
  },
  opcaoSelecionada: { backgroundColor: cores.principal, borderColor: cores.principal },
  opcaoPressionada: { backgroundColor: cores.principalClaro },
  textoOpcao: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  textoOpcaoSelecionada: { color: cores.cartao },
  areaErros: { backgroundColor: cores.principalClaro, borderRadius: raiosBorda.media, gap: espacamentos.minimo, padding: espacamentos.medio },
  tituloErros: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  textoErro: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  areaSaida: { gap: espacamentos.pequeno },
  descricaoSaida: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal, textAlign: 'center' },
});
