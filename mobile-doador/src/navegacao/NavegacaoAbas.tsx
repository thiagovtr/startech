import { Ionicons } from '@expo/vector-icons';
import { createBottomTabNavigator, type BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Agendar, Assistente, Inicio, MeusPedidos } from '../telas';
import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

export type ParametrosAbas = {
  Inicio: undefined;
  Agendar: undefined;
  MeusPedidos: undefined;
  Assistente: undefined;
};

type NomeIcone = keyof typeof Ionicons.glyphMap;

const Abas = createBottomTabNavigator<ParametrosAbas>();

const configuracoesAbas: Record<keyof ParametrosAbas, { iconeAtivo: NomeIcone; iconeInativo: NomeIcone; titulo: string }> = {
  Inicio: { iconeAtivo: 'home', iconeInativo: 'home-outline', titulo: 'Início' },
  Agendar: { iconeAtivo: 'calendar', iconeInativo: 'calendar-outline', titulo: 'Agendar' },
  MeusPedidos: { iconeAtivo: 'clipboard', iconeInativo: 'clipboard-outline', titulo: 'Meus pedidos' },
  Assistente: { iconeAtivo: 'chatbubble', iconeInativo: 'chatbubble-outline', titulo: 'Assistente' },
};

export function NavegacaoAbas() {
  return (
    <Abas.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: cores.cartao },
        headerTitleStyle: {
          color: cores.texto,
          fontWeight: pesosFonte.seminegrito,
        },
        tabBarHideOnKeyboard: true,
      }}
      tabBar={(propriedades) => <BarraNavegacaoFlutuante {...propriedades} />}
    >
      <Abas.Screen component={Inicio} name="Inicio" options={{ headerShown: false, title: 'Início' }} />
      <Abas.Screen component={Agendar} name="Agendar" options={{ headerShown: false, title: 'Agendar' }} />
      <Abas.Screen component={MeusPedidos} name="MeusPedidos" options={{ headerShown: false, title: 'Meus pedidos' }} />
      <Abas.Screen component={Assistente} name="Assistente" options={{ headerShown: false, title: 'Assistente' }} />
    </Abas.Navigator>
  );
}

function BarraNavegacaoFlutuante({ descriptors, navigation, state }: BottomTabBarProps) {
  const areasSeguras = useSafeAreaInsets();

  return (
    <View style={[estilos.container, { paddingBottom: Math.max(areasSeguras.bottom, espacamentos.padrao) }]}>
      <View style={estilos.barra}>
        {state.routes.map((rota, indice) => {
          const selecionada = state.index === indice;
          const configuracao = configuracoesAbas[rota.name as keyof ParametrosAbas];

          function pressionarAba() {
            const evento = navigation.emit({
              canPreventDefault: true,
              target: rota.key,
              type: 'tabPress',
            });

            if (!selecionada && !evento.defaultPrevented) {
              navigation.navigate(rota.name);
            }
          }

          function manterPressionada() {
            navigation.emit({ target: rota.key, type: 'tabLongPress' });
          }

          return (
            <Pressable
              accessibilityLabel={configuracao.titulo}
              accessibilityRole="button"
              accessibilityState={{ selected: selecionada }}
              key={rota.key}
              onLongPress={manterPressionada}
              onPress={pressionarAba}
              style={({ pressed }) => [
                estilos.aba,
                selecionada && estilos.abaSelecionada,
                pressed && !selecionada && estilos.abaPressionada,
              ]}
            >
              <Ionicons
                color={selecionada ? cores.principalEscuro : cores.textoSecundario}
                name={selecionada ? configuracao.iconeAtivo : configuracao.iconeInativo}
                size={25}
              />
              <Text adjustsFontSizeToFit minimumFontScale={0.82} numberOfLines={1} style={[estilos.rotulo, selecionada && estilos.rotuloSelecionado]}>
                {configuracao.titulo}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const estilos = StyleSheet.create({
  container: {
    backgroundColor: 'transparent',
    bottom: 0,
    left: 0,
    paddingHorizontal: espacamentos.padrao,
    paddingTop: espacamentos.pequeno,
    position: 'absolute',
    right: 0,
  },
  barra: {
    backgroundColor: cores.cartao,
    borderRadius: raiosBorda.grande,
    elevation: 8,
    flexDirection: 'row',
    minHeight: 72,
    padding: espacamentos.minimo,
    shadowColor: cores.texto,
    shadowOffset: { height: 4, width: 0 },
    shadowOpacity: 0.12,
    shadowRadius: 10,
  },
  aba: {
    alignItems: 'center',
    borderRadius: raiosBorda.media,
    flex: 1,
    gap: espacamentos.minimo,
    justifyContent: 'center',
    minHeight: 64,
    paddingHorizontal: espacamentos.minimo,
  },
  abaSelecionada: { backgroundColor: cores.principalClaro },
  abaPressionada: { backgroundColor: cores.fundo },
  rotulo: {
    color: cores.textoSecundario,
    fontSize: tamanhosFonte.legenda,
    fontWeight: pesosFonte.medio,
    textAlign: 'center',
  },
  rotuloSelecionado: { color: cores.principalEscuro, fontWeight: pesosFonte.seminegrito },
});
