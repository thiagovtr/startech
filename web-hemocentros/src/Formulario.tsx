import { useEffect, useRef, useState, type FormEvent } from "react";
import { ErroCampanhas, mensagemErro, tiposSanguineos, type Campanha, type CampanhaAtualizar, type Hemocentro, type NovaCampanha } from "./campanhas";
import { campanhas } from "./sessao";

interface Props {
  campanha?: Campanha;
  aoConcluir: (campanha: Campanha) => void;
  voltar: () => void;
}

export function Formulario({ campanha: campanhaInicial, aoConcluir, voltar }: Props) {
  const editando = Boolean(campanhaInicial);
  const [inicio, setInicio] = useState(campanhaInicial?.data_inicio.split("T")[0] || "");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [hemocentros, setHemocentros] = useState<Hemocentro[] | null>(null);
  const [erroHemocentros, setErroHemocentros] = useState("");
  const [hemocentroSelecionado, setHemocentroSelecionado] = useState("");
  const emCurso = useRef(false);

  useEffect(() => {
    const consulta = new AbortController();
    campanhas.listarHemocentros(consulta.signal).then(resultado => {
      if (consulta.signal.aborted) return;
      setHemocentros(resultado);
      const hemocentroAtual = resultado.find(item => item.nome === campanhaInicial?.hemocentro);
      if (campanhaInicial && !hemocentroAtual) {
        setErroHemocentros("O hemocentro salvo nesta campanha não está disponível. Selecione uma instituição válida antes de salvar.");
      } else if (hemocentroAtual) {
        setHemocentroSelecionado(hemocentroAtual.id);
      }
    }).catch(falha => {
      if (!consulta.signal.aborted) {
        setHemocentros([]);
        setErroHemocentros(mensagemErro(falha));
      }
    });
    return () => consulta.abort();
  }, []);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (emCurso.current) return;
    const dados = new FormData(evento.currentTarget);
    const texto = (campo: string) => String(dados.get(campo) ?? "").trim();
    const hemocentro = hemocentros?.find(item => item.id === texto("hemocentro"));
    if (!hemocentro) {
      setErro("Selecione um hemocentro válido para criar a campanha.");
      return;
    }
    const campanha = {
      titulo: texto("titulo"), hemocentro: hemocentro.nome, tipo_sanguineo: texto("tipo_sanguineo"),
      urgencia: texto("urgencia"), data_inicio: texto("data_inicio"), data_fim: texto("data_fim")
    } satisfies NovaCampanha;
    if (campanha.titulo.length < 3) {
      setErro("Informe ao menos três caracteres no título, descontando espaços nas pontas.");
      return;
    }
    emCurso.current = true;
    setEnviando(true);
    setErro("");
    try {
      const resultado = campanhaInicial
        ? await campanhas.atualizar(campanhaInicial.id, { ...campanha, status: texto("status") } satisfies CampanhaAtualizar)
        : await campanhas.criar(campanha);
      aoConcluir(resultado);
    } catch (falha) {
      const incerto = !(falha instanceof ErroCampanhas) || falha.status === 0 || falha.status >= 500;
      setErro(mensagemErro(falha) + (incerto ? editando ? " Consulte a lista antes de reenviar a alteração." : " Consulte a lista antes de reenviar para evitar uma campanha duplicada." : ""));
    } finally {
      emCurso.current = false;
      setEnviando(false);
    }
  }

  return <>
    <div className="cabecalho-formulario">
      <button type="button" className="voltar" onClick={voltar} disabled={enviando}>← Campanhas</button>
      <div><h1>{editando ? "Editar campanha" : "Nova campanha"}</h1><p className="subtitulo">Preencha as informações da campanha.</p></div>
    </div>
    <form className="cartao formulario" onSubmit={enviar} aria-busy={enviando}>
      <fieldset disabled={enviando}>
        <legend>Dados da campanha</legend>
        <label>Título<input autoFocus name="titulo" required minLength={3} maxLength={200} defaultValue={campanhaInicial?.titulo} /></label>
        <label>Hemocentro<select name="hemocentro" required value={hemocentroSelecionado}
          onChange={e => { setHemocentroSelecionado(e.target.value); setErroHemocentros(""); }} disabled={enviando || !hemocentros?.length}
          aria-describedby={erroHemocentros ? "erro-hemocentros" : undefined}>
          <option value="" disabled>{hemocentros === null ? "Carregando hemocentros…" : erroHemocentros && !hemocentros?.length ? "Não foi possível carregar" : "Selecione"}</option>
          {hemocentros?.map(hemocentro => <option key={hemocentro.id} value={hemocentro.id}>
            {hemocentro.nome}{hemocentro.cidade ? " — " + hemocentro.cidade : ""}
          </option>)}
        </select></label>
        {erroHemocentros ? <p id="erro-hemocentros" className="mensagem-campo erro" role="alert">{erroHemocentros}</p>
          : hemocentros?.length === 0 ? <p className="mensagem-campo" role="status">Nenhum hemocentro disponível no momento.</p> : null}
        <div className="dupla">
          <label>Tipo sanguíneo<select name="tipo_sanguineo" required defaultValue={campanhaInicial?.tipo_sanguineo || ""}>
            <option value="" disabled>Selecione</option>
            {tiposSanguineos.map(tipo => <option key={tipo}>{tipo}</option>)}
          </select></label>
          <label>Urgência<select name="urgencia" defaultValue={campanhaInicial?.urgencia || "NORMAL"}>
            <option value="NORMAL">Normal</option><option value="CRITICO">Crítica</option>
          </select></label>
        </div>
        <div className="dupla">
          <label>Data de início<input type="date" name="data_inicio" required value={inicio} onChange={e => setInicio(e.target.value)} /></label>
          <label>Data de término<input type="date" name="data_fim" min={inicio || undefined} required defaultValue={campanhaInicial?.data_fim.split("T")[0]} /></label>
        </div>
        {campanhaInicial && <label>Status<select name="status" required defaultValue={campanhaInicial.status}>
          <option value="ATIVA">Ativa</option><option value="ENCERRADA">Encerrada</option>
        </select></label>}
      </fieldset>
      {erro && <p className="aviso erro" role="alert">{erro}</p>}
      <div className="acoes"><button type="button" onClick={voltar} disabled={enviando}>Cancelar</button>
        <button className="primario" type="submit" disabled={enviando || !hemocentros?.length || !hemocentroSelecionado}>{enviando ? editando ? "Salvando…" : "Criando…" : editando ? "Salvar alterações" : "Criar campanha"}</button></div>
    </form>
  </>;
}
