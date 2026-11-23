import { useEffect, useState } from "react";
import { semFiltros, tiposSanguineos, tamanhoPagina, mensagemErro, type Campanha, type Filtros } from "./campanhas";
import { campanhas } from "./sessao";
import { Formulario } from "./Formulario";

function dataBr(data: string) {
  return data.split("T")[0].split("-").reverse().join("/");
}

function Tabela({ itens }: { itens: Campanha[] }) {
  return <div className="rolagem" role="region" aria-label="Lista de campanhas" tabIndex={0}>
    <table><thead><tr>
      <th>Campanha e hemocentro</th><th>Tipo sanguíneo</th><th>Urgência</th><th>Período</th><th>Status</th>
    </tr></thead><tbody>{itens.map(c => <tr key={c.id}>
      <th scope="row"><strong>{c.titulo}</strong><small>{c.hemocentro}</small></th>
      <td><span className="tipo">{c.tipo_sanguineo}</span></td>
      <td><span className={c.urgencia === "CRITICO" ? "critica" : ""}>{c.urgencia === "CRITICO" ? "Crítica" : c.urgencia === "NORMAL" ? "Normal" : c.urgencia}</span></td>
      <td>{dataBr(c.data_inicio)} a {dataBr(c.data_fim)}</td>
      <td><span className={c.status === "ATIVA" ? "ativa" : "neutra"}>{c.status === "ATIVA" ? "Ativa" : c.status === "ENCERRADA" ? "Encerrada" : c.status}</span></td>
    </tr>)}</tbody></table>
  </div>;
}

type Consulta = Awaited<ReturnType<typeof campanhas.listar>>;

function Lista({ nova, criada }: { nova: () => void; criada: Campanha | null }) {
  const [filtros, setFiltros] = useState(semFiltros);
  const [pagina, setPagina] = useState(0);
  const [revisao, setRevisao] = useState(0);
  const [dados, setDados] = useState<Consulta | null>(null);
  const [erro, setErro] = useState("");
  const atualizar = () => setRevisao(n => n + 1);
  useEffect(() => {
    const consulta = new AbortController();
    setDados(null);
    setErro("");
    campanhas.listar(filtros, pagina, consulta.signal).then(resultado => {
      if (consulta.signal.aborted) return;
      if (pagina > 0 && !resultado.itens.length) setPagina(0);
      else setDados(resultado);
    }).catch(falha => {
      if (!consulta.signal.aborted) setErro(mensagemErro(falha));
    });
    return () => consulta.abort();
  }, [filtros, pagina, revisao]);
  function filtrar(alteracao: Partial<Filtros>) {
    setPagina(0);
    setFiltros(atuais => ({ ...atuais, ...alteracao }));
  }
  const temProxima = dados && (dados.total === null ? dados.itens.length === tamanhoPagina : (pagina + 1) * tamanhoPagina < dados.total);

  return <>
    <div className="cabecalho"><h1>Campanhas</h1>
      <button className="primario" onClick={nova}><span aria-hidden="true">＋ </span>Nova campanha</button></div>
    {criada && <div className="aviso sucesso" role="status"><strong>Campanha criada: {criada.titulo}</strong>
      <small>Identificador: {criada.id}</small>
      A lista e o aplicativo podem levar alguns segundos para exibi-la.</div>}
    <section className="cartao" aria-label="Consulta de campanhas">
      <div className="filtros">
        <label>Tipo sanguíneo<select value={filtros.tipo} onChange={e => filtrar({ tipo: e.target.value })}>
          <option value="">Todos</option>{tiposSanguineos.map(tipo => <option key={tipo}>{tipo}</option>)}
        </select></label>
        <label>Status<select value={filtros.status} onChange={e => filtrar({ status: e.target.value })}>
          <option value="">Todos</option><option value="ATIVA">Ativa</option><option value="ENCERRADA">Encerrada</option>
        </select></label>
        <label className="check"><input type="checkbox" checked={filtros.vigentes} onChange={e => filtrar({ vigentes: e.target.checked })} />Somente vigentes</label>
        <button className="atualizar" onClick={atualizar}>Atualizar lista</button>
      </div>
      {erro ? <p className="estado erro" role="alert">{erro}</p> : !dados ? <p className="estado" role="status">Carregando campanhas…</p>
        : dados.itens.length ? <Tabela itens={dados.itens} /> : <p className="estado" role="status">Nenhuma campanha encontrada com esta seleção.</p>}
      <div className="paginacao"><span aria-live="polite">{dados?.total != null ? "Total de campanhas: " + dados.total : "Campanhas"}</span>
        <nav aria-label="Paginação de campanhas"><button disabled={!dados || pagina === 0} onClick={() => setPagina(pagina - 1)}>Anterior</button>
          <span>Página {pagina + 1}</span><button disabled={!temProxima} onClick={() => setPagina(pagina + 1)}>Próxima</button></nav></div>
    </section>
  </>;
}

export function Painel({ usuario, sair }: { usuario: string; sair: () => void }) {
  const [formulario, setFormulario] = useState(false);
  const [criada, setCriada] = useState<Campanha | null>(null);
  return <>
    <header><div className="barra"><div className="identidade"><span className="marca">StarTech</span><span>Hemocentros</span></div>
      <div className="conta"><span>{usuario}</span><button onClick={sair}>Sair</button></div></div></header>
    <main className="conteudo">{formulario ?
      <Formulario voltar={() => setFormulario(false)} aoCriar={c => { setCriada(c); setFormulario(false); }} /> :
      <Lista criada={criada} nova={() => { setCriada(null); setFormulario(true); }} />}
    </main>
  </>;
}
