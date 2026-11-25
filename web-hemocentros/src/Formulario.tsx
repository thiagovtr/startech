import { useRef, useState, type FormEvent } from "react";
import { ErroCampanhas, mensagemErro, tiposSanguineos, type Campanha } from "./campanhas";
import { campanhas } from "./sessao";

interface Props {
  aoCriar: (campanha: Campanha) => void;
  voltar: () => void;
}

export function Formulario({ aoCriar, voltar }: Props) {
  const [inicio, setInicio] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const emCurso = useRef(false);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (emCurso.current) return;
    const dados = new FormData(evento.currentTarget);
    const texto = (campo: string) => String(dados.get(campo) ?? "").trim();
    const campanha = {
      titulo: texto("titulo"), hemocentro: texto("hemocentro"), tipo_sanguineo: texto("tipo_sanguineo"),
      urgencia: texto("urgencia"), data_inicio: texto("data_inicio"), data_fim: texto("data_fim")
    };
    if (campanha.titulo.length < 3 || campanha.hemocentro.length < 2) {
      setErro("Informe ao menos três caracteres no título e dois no hemocentro, descontando espaços nas pontas.");
      return;
    }
    emCurso.current = true;
    setEnviando(true);
    setErro("");
    try {
      aoCriar(await campanhas.criar(campanha));
    } catch (falha) {
      const incerto = !(falha instanceof ErroCampanhas) || falha.status === 0 || falha.status >= 500;
      setErro(mensagemErro(falha) + (incerto ? " Consulte a lista antes de reenviar para evitar uma campanha duplicada." : ""));
    } finally {
      emCurso.current = false;
      setEnviando(false);
    }
  }

  return <>
    <div className="cabecalho-formulario">
      <button type="button" className="voltar" onClick={voltar} disabled={enviando}>← Campanhas</button>
      <div><h1>Nova campanha</h1><p className="subtitulo">Preencha as informações da campanha.</p></div>
    </div>
    <form className="cartao formulario" onSubmit={enviar} aria-busy={enviando}>
      <fieldset disabled={enviando}>
        <legend>Dados da campanha</legend>
        <label>Título<input autoFocus name="titulo" required minLength={3} maxLength={200} /></label>
        <label>Hemocentro<input name="hemocentro" required minLength={2} maxLength={200} /></label>
        <div className="dupla">
          <label>Tipo sanguíneo<select name="tipo_sanguineo" required defaultValue="">
            <option value="" disabled>Selecione</option>
            {tiposSanguineos.map(tipo => <option key={tipo}>{tipo}</option>)}
          </select></label>
          <label>Urgência<select name="urgencia" defaultValue="NORMAL">
            <option value="NORMAL">Normal</option><option value="CRITICO">Crítica</option>
          </select></label>
        </div>
        <div className="dupla">
          <label>Data de início<input type="date" name="data_inicio" required value={inicio} onChange={e => setInicio(e.target.value)} /></label>
          <label>Data de término<input type="date" name="data_fim" min={inicio || undefined} required /></label>
        </div>
      </fieldset>
      {erro && <p className="aviso erro" role="alert">{erro}</p>}
      <div className="acoes"><button type="button" onClick={voltar} disabled={enviando}>Cancelar</button>
        <button className="primario" type="submit" disabled={enviando}>{enviando ? "Criando…" : "Criar campanha"}</button></div>
    </form>
  </>;
}
