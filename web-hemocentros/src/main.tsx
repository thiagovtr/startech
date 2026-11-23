import { createRoot } from "react-dom/client";
import { Painel } from "./Painel";
import { retorno, sessao } from "./sessao";
import "./estilo.css";

const root = createRoot(document.getElementById("root")!);

function Entrada({ mensagem, acao, rotulo }: { mensagem: string; acao?: () => void; rotulo?: string }) {
  return <main className="entrada cartao">
    <span className="marca">StarTech</span>
    <h1>Painel dos hemocentros</h1>
    <p role="status">{mensagem}</p>
    {acao && <button className="primario" onClick={acao}>{rotulo}</button>}
  </main>;
}

function falhaLogin() {
  root.render(<Entrada mensagem="Não foi possível conectar ao serviço de autenticação."
    rotulo="Tentar novamente" acao={() => window.location.replace(retorno)} />);
}

function sair() {
  void sessao.logout({ redirectUri: retorno }).catch(falhaLogin);
}

root.render(<Entrada mensagem="Verificando sua sessão…" />);
sessao.init({
  onLoad: "check-sso",
  pkceMethod: "S256",
  flow: "standard",
  redirectUri: retorno,
  checkLoginIframe: false
}).then((autenticado) => {
  if (!autenticado) {
    root.render(<Entrada mensagem="Entre com sua conta de operador para gerenciar campanhas."
      acao={() => void sessao.login({ redirectUri: retorno }).catch(falhaLogin)} rotulo="Entrar com StarTech" />);
  } else if (!sessao.hasRealmRole("operador")) {
    root.render(<Entrada mensagem="Este painel exige o perfil de operador de hemocentro."
      acao={sair} rotulo="Sair e trocar de conta" />);
  } else {
    root.render(<Painel usuario={sessao.tokenParsed?.preferred_username || "Operador"} sair={sair} />);
  }
}).catch(falhaLogin);
