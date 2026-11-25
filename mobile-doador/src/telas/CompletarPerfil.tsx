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
import { BotaoPrimario } from '../componentes';
import { ErroHttp, salvarPerfil, type FormularioPerfil, type SexoDoador, type TipoSanguineo } from '../servicos';
import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

type PropriedadesCompletarPerfil = {
  aoConcluir: () => void;
};

const tiposSanguineos: TipoSanguineo[] = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];

const opcoesSexo: { valor: SexoDoador; titulo: string }[] = [
  { valor: 'M', titulo: 'Masculino' },
  { valor: 'F', titulo: 'Feminino' },
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

  const erroNome = obterErroCampo(erros, ['nome']);
  const erroTipoSanguineo = obterErroCampo(erros, ['tipo sanguíneo', 'tiposanguineo']);
  const erroSexo = obterErroCampo(erros, ['sexo']);
  const erroData = obterErroCampo(erros, ['data', 'doação']);

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={estilos.areaSegura}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={estilos.areaFlexivel}>
        <ScrollView contentContainerStyle={estilos.conteudo} keyboardShouldPersistTaps="handled">
          <View style={estilos.cabecalho}>
            <Text style={estilos.titulo}>Complete seu cadastro</Text>
            <Text style={estilos.descricao}>Precisamos de algumas informações para configurar seu perfil de doador.</Text>
          </View>

          <View style={estilos.formulario}>
            <Campo
              aoAlterarTexto={definirNome}
              autoCapitalize="words"
              erro={erroNome}
              maxLength={120}
              texto={nome}
              titulo="Nome completo"
            />

            <View style={estilos.grupoCampo}>
              <Text style={estilos.rotulo}>Tipo sanguíneo</Text>
              <View style={estilos.gradeTiposSanguineos}>
                {tiposSanguineos.map((tipo) => (
                  <OpcaoSelecionavel
                    compacta
                    key={tipo}
                    selecionada={tipoSanguineo === tipo}
                    aoPressionar={() => definirTipoSanguineo(tipo)}
                    titulo={tipo}
                  />
                ))}
              </View>
              {erroTipoSanguineo && <MensagemCampo texto={erroTipoSanguineo} />}
            </View>

            <View style={estilos.grupoCampo}>
              <Text style={estilos.rotulo}>Sexo</Text>
              <View style={estilos.listaSexo}>
                {opcoesSexo.map((opcao) => (
                  <OpcaoSelecionavel
                    key={opcao.valor}
                    selecionada={sexo === opcao.valor}
                    aoPressionar={() => definirSexo(opcao.valor)}
                    titulo={opcao.titulo}
                  />
                ))}
              </View>
              {erroSexo && <MensagemCampo texto={erroSexo} />}
            </View>

            <Campo
              aoAlterarTexto={(texto) => definirDataUltimaDoacao(mascararData(texto))}
              descricao="Opcional"
              erro={erroData}
              keyboardType="number-pad"
              maxLength={10}
              placeholder="dd/mm/aaaa"
              texto={dataUltimaDoacao}
              titulo="Data da última doação"
            />

            {erros.length > 0 && (
              <View accessibilityLiveRegion="polite" style={estilos.areaErros}>
                <Text style={estilos.tituloErros}>Revise os dados informados</Text>
                {erros.map((erro) => <Text key={erro} style={estilos.textoErro}>• {erro}</Text>)}
              </View>
            )}

            <BotaoPrimario aoPressionar={() => void enviarPerfil()} carregando={salvando} titulo="Concluir cadastro" />
          </View>

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
  erro?: string;
  keyboardType?: 'default' | 'number-pad';
  maxLength?: number;
  placeholder?: string;
  texto: string;
  titulo: string;
};

function Campo({
  aoAlterarTexto,
  autoCapitalize = 'none',
  descricao,
  erro,
  keyboardType = 'default',
  maxLength,
  placeholder,
  texto,
  titulo,
}: PropriedadesCampo) {
  return (
    <View style={estilos.grupoCampo}>
      <View style={estilos.linhaRotulo}>
        <Text style={estilos.rotulo}>{titulo}</Text>
        {descricao && <Text style={estilos.descricaoCampo}>{descricao}</Text>}
      </View>
      <TextInput
        accessibilityLabel={titulo}
        autoCapitalize={autoCapitalize}
        keyboardType={keyboardType}
        maxLength={maxLength}
        onChangeText={aoAlterarTexto}
        placeholder={placeholder}
        placeholderTextColor={cores.textoSecundario}
        style={[estilos.entrada, erro && estilos.entradaComErro]}
        value={texto}
      />
      {erro && <MensagemCampo texto={erro} />}
    </View>
  );
}

type PropriedadesOpcaoSelecionavel = {
  aoPressionar: () => void;
  compacta?: boolean;
  selecionada: boolean;
  titulo: string;
};

function OpcaoSelecionavel({ aoPressionar, compacta = false, selecionada, titulo }: PropriedadesOpcaoSelecionavel) {
  return (
    <Pressable
      accessibilityLabel={`Selecionar ${titulo}`}
      accessibilityRole="button"
      accessibilityState={{ selected: selecionada }}
      onPress={aoPressionar}
      style={({ pressed }) => [
        estilos.opcao,
        compacta && estilos.opcaoCompacta,
        selecionada && estilos.opcaoSelecionada,
        pressed && !selecionada && estilos.opcaoPressionada,
      ]}
    >
      <Text style={[estilos.textoOpcao, selecionada && estilos.textoOpcaoSelecionada]}>{titulo}</Text>
    </Pressable>
  );
}

function MensagemCampo({ texto }: { texto: string }) {
  return <Text accessibilityLiveRegion="polite" style={estilos.textoErroCampo}>{texto}</Text>;
}

function prepararDadosPerfil(
  nome: string,
  tipoSanguineo: TipoSanguineo | undefined,
  sexo: SexoDoador | undefined,
  dataUltimaDoacao: string,
): FormularioPerfil | string[] {
  const nomeNormalizado = nome.trim();
  const dataNormalizada = converterDataParaApi(dataUltimaDoacao.trim());
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

  if (dataUltimaDoacao.trim() && (!dataNormalizada || !dataEhValida(dataNormalizada))) {
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

function mascararData(texto: string): string {
  const digitos = texto.replace(/\D/g, '').slice(0, 8);
  if (digitos.length <= 2) return digitos;
  if (digitos.length <= 4) return `${digitos.slice(0, 2)}/${digitos.slice(2)}`;
  return `${digitos.slice(0, 2)}/${digitos.slice(2, 4)}/${digitos.slice(4)}`;
}

function converterDataParaApi(data: string): string | undefined {
  const resultado = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(data);
  if (!resultado) return undefined;
  return `${resultado[3]}-${resultado[2]}-${resultado[1]}`;
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

function obterErroCampo(erros: string[], termos: string[]): string | undefined {
  return erros.find((erro) => {
    const erroNormalizado = erro.toLocaleLowerCase('pt-BR');
    return termos.some((termo) => erroNormalizado.includes(termo));
  });
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
  conteudo: { gap: espacamentos.grande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  cabecalho: { gap: espacamentos.pequeno },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 23 },
  formulario: { gap: espacamentos.grande },
  grupoCampo: { gap: espacamentos.pequeno },
  linhaRotulo: { alignItems: 'baseline', flexDirection: 'row', gap: espacamentos.pequeno, justifyContent: 'space-between' },
  rotulo: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  descricaoCampo: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  entrada: {
    backgroundColor: cores.cartao,
    borderColor: cores.principalClaro,
    borderRadius: raiosBorda.media,
    borderWidth: 1,
    color: cores.texto,
    fontSize: tamanhosFonte.corpo,
    minHeight: 48,
    paddingHorizontal: espacamentos.medio,
    paddingVertical: espacamentos.pequeno,
  },
  entradaComErro: { borderColor: cores.principalEscuro },
  gradeTiposSanguineos: { flexDirection: 'row', flexWrap: 'wrap', gap: espacamentos.pequeno },
  listaSexo: { flexDirection: 'row', gap: espacamentos.pequeno },
  opcao: {
    alignItems: 'center',
    backgroundColor: cores.cartao,
    borderColor: cores.principalClaro,
    borderRadius: raiosBorda.media,
    borderWidth: 1,
    flex: 1,
    justifyContent: 'center',
    minHeight: 48,
    paddingHorizontal: espacamentos.medio,
  },
  opcaoCompacta: { flexBasis: '22%', flexGrow: 1, flexShrink: 1, minHeight: 44, paddingHorizontal: espacamentos.pequeno },
  opcaoSelecionada: { backgroundColor: cores.principal, borderColor: cores.principal },
  opcaoPressionada: { backgroundColor: cores.principalClaro },
  textoOpcao: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  textoOpcaoSelecionada: { color: cores.cartao },
  areaErros: { backgroundColor: cores.principalClaro, borderRadius: raiosBorda.media, gap: espacamentos.minimo, padding: espacamentos.medio },
  tituloErros: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  textoErro: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  textoErroCampo: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  areaSaida: { gap: espacamentos.pequeno, paddingTop: espacamentos.pequeno },
  descricaoSaida: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal, textAlign: 'center' },
});
