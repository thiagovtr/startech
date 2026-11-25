import { useEffect, useState } from "react";
import { semFiltros, tiposSanguineos, tamanhoPagina, mensagemErro, type Campanha, type Filtros } from "./campanhas";
import { campanhas } from "./sessao";
import { Formulario } from "./Formulario";

function dataBr(data: string) {
  return data.split("T")[0].split("-").reverse().join("/");
}

function Tabela({ itens, editar }: { itens: Campanha[]; editar: (campanha: Campanha) => void }) {
  return <div className="rolagem" role="region" aria-label="Lista de campanhas" tabIndex={0}>
    <table className="tabela-campanhas"><thead><tr>
      <th>Campanha e hemocentro</th><th>Tipo sanguíneo</th><th>Urgência</th><th>Período</th><th>Status</th><th>Ações</th>
    </tr></thead><tbody>{itens.map(c => <tr key={c.id}>
      <th scope="row"><strong>{c.titulo}</strong><small>{c.hemocentro}</small></th>
      <td><span className="tipo">{c.tipo_sanguineo}</span></td>
      <td><span className={c.urgencia === "CRITICO" ? "critica" : ""}>{c.urgencia === "CRITICO" ? "Crítica" : c.urgencia === "NORMAL" ? "Normal" : c.urgencia}</span></td>
      <td>{dataBr(c.data_inicio)} a {dataBr(c.data_fim)}</td>
      <td><span className={c.status === "ATIVA" ? "ativa" : "neutra"}>{c.status === "ATIVA" ? "Ativa" : c.status === "ENCERRADA" ? "Encerrada" : c.status}</span></td>
      <td><button className="acao-tabela" onClick={() => editar(c)}>Editar</button></td>
    </tr>)}</tbody></table>
  </div>;
}

type Consulta = Awaited<ReturnType<typeof campanhas.listar>>;
type Confirmacao = { campanha: Campanha; tipo: "criada" | "atualizada" };

function Lista({ nova, editar, confirmacao, filtros, pagina, filtrar, mudarPagina }: {
  nova: () => void;
  editar: (campanha: Campanha) => void;
  confirmacao: Confirmacao | null;
  filtros: Filtros;
  pagina: number;
  filtrar: (alteracao: Partial<Filtros>) => void;
  mudarPagina: (pagina: number) => void;
}) {
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
      if (pagina > 0 && !resultado.itens.length) mudarPagina(0);
      else setDados(resultado);
    }).catch(falha => {
      if (!consulta.signal.aborted) setErro(mensagemErro(falha));
    });
    return () => consulta.abort();
  }, [filtros, pagina, revisao]);
  const temProxima = dados && (dados.total === null ? dados.itens.length === tamanhoPagina : (pagina + 1) * tamanhoPagina < dados.total);

  return <>
    <div className="cabecalho"><div><h1>Painel de campanhas</h1><p className="subtitulo">Gerencie as campanhas de doação.</p></div>
      <button className="primario" onClick={nova}><span aria-hidden="true">＋ </span>Nova campanha</button></div>
    {confirmacao && <div className="aviso sucesso" role="status"><strong>Campanha {confirmacao.tipo}: {confirmacao.campanha.titulo}</strong>
      <small>Identificador: {confirmacao.campanha.id}</small>
      A lista e o aplicativo podem levar alguns segundos para exibi-la.</div>}
    <section className="cartao lista-campanhas" aria-label="Consulta de campanhas">
      <div className="filtros">
        <label>Tipo sanguíneo<select value={filtros.tipo} onChange={e => filtrar({ tipo: e.target.value })}>
          <option value="">Todos</option>{tiposSanguineos.map(tipo => <option key={tipo}>{tipo}</option>)}
        </select></label>
        <label>Status<select value={filtros.status} onChange={e => filtrar({ status: e.target.value })}>
          <option value="">Todos</option><option value="ATIVA">Ativa</option><option value="ENCERRADA">Encerrada</option>
        </select></label>
        <label className="check"><input type="checkbox" checked={filtros.vigentes} onChange={e => filtrar({ vigentes: e.target.checked })} />Somente vigentes</label>
        <button className="atualizar" onClick={atualizar} aria-label="Atualizar lista" title="Atualizar lista"><svg aria-hidden="true" width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M23 4v6h-6" /><path d="M1 20v-6h6" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10" /><path d="M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
        </svg></button>
      </div>
      {erro ? <p className="estado erro" role="alert">{erro}</p> : !dados ? <p className="estado" role="status">Carregando campanhas…</p>
        : dados.itens.length ? <Tabela itens={dados.itens} editar={editar} /> : <p className="estado" role="status">Nenhuma campanha encontrada com esta seleção.</p>}
      <div className="paginacao"><span aria-live="polite">{dados?.total != null ? "Total de campanhas: " + dados.total : "Campanhas"}</span>
        <nav aria-label="Paginação de campanhas"><button disabled={!dados || pagina === 0} onClick={() => mudarPagina(pagina - 1)}>Anterior</button>
          <span>Página {pagina + 1}</span><button disabled={!temProxima} onClick={() => mudarPagina(pagina + 1)}>Próxima</button></nav></div>
    </section>
  </>;
}

export function Painel({ usuario, sair }: { usuario: string; sair: () => void }) {
  const [formulario, setFormulario] = useState(false);
  const [campanhaEmEdicao, setCampanhaEmEdicao] = useState<Campanha | null>(null);
  const [confirmacao, setConfirmacao] = useState<Confirmacao | null>(null);
  const [filtros, setFiltros] = useState(semFiltros);
  const [pagina, setPagina] = useState(0);
  function filtrar(alteracao: Partial<Filtros>) {
    setPagina(0);
    setFiltros(atuais => ({ ...atuais, ...alteracao }));
  }
  function concluir(campanha: Campanha) {
    setConfirmacao({ campanha, tipo: campanhaEmEdicao ? "atualizada" : "criada" });
    setFormulario(false);
  }
  return <>
    <header><div className="barra"><div className="identidade"><span className="marca">StarTech</span><span>Hemocentros</span></div>
      <div className="conta"><span>{usuario}</span><button onClick={sair}>Sair</button></div></div></header>
    <main className="conteudo">{formulario ?
      <Formulario campanha={campanhaEmEdicao || undefined} voltar={() => setFormulario(false)} aoConcluir={concluir} /> :
      <Lista confirmacao={confirmacao} filtros={filtros} pagina={pagina} filtrar={filtrar} mudarPagina={setPagina}
        editar={campanha => { setConfirmacao(null); setCampanhaEmEdicao(campanha); setFormulario(true); }}
        nova={() => { setConfirmacao(null); setCampanhaEmEdicao(null); setFormulario(true); }} />}
    </main>
  </>;
}
