export const tiposSanguineos = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"] as const;

export interface NovaCampanha {
  titulo: string;
  hemocentro: string;
  tipo_sanguineo: string;
  urgencia: string;
  data_inicio: string;
  data_fim: string;
}

export interface Campanha extends NovaCampanha {
  id: string;
  status: string;
}

export interface Filtros {
  tipo: string;
  status: string;
  vigentes: boolean;
}

export const tamanhoPagina = 10;
export const semFiltros: Filtros = { tipo: "", status: "", vigentes: false };

const errosHttp: Record<number, string> = {
  400: "Confira os campos informados.",
  401: "Sua sessão expirou. Entre novamente.",
  403: "Seu usuário não tem permissão para acessar as campanhas.",
  502: "Falha na resposta do serviço de campanhas.",
  503: "Serviço de campanhas indisponível.",
  504: "O serviço demorou para responder."
};

export class ErroCampanhas extends Error {
  status: number;
  constructor(status: number, mensagem: string) {
    super(mensagem);
    this.status = status;
  }
}

async function verificarResposta(resposta: Response) {
  if (resposta.ok) return;
  const problema = await resposta.json().catch(() => null);
  const detalhes = [problema?.title, problema?.detail].filter((v) => typeof v === "string" && v);
  if (Array.isArray(problema?.invalidParams)) {
    for (const campo of problema.invalidParams) {
      if (campo?.name && campo?.reason) detalhes.push(campo.name + ": " + campo.reason);
    }
  }
  const resumo = errosHttp[resposta.status] || "Não foi possível concluir a solicitação.";
  throw new ErroCampanhas(resposta.status, ["HTTP " + resposta.status + " — " + resumo, ...detalhes].join(" "));
}

export function clienteCampanhas(gateway: string, obterToken: () => Promise<string>) {
  const rota = new URL("/api/web/campanhas", gateway);
  async function enviar(url: URL, opcoes: RequestInit) {
    const token = await obterToken();
    const headers = new Headers(opcoes.headers);
    headers.set("Authorization", "Bearer " + token);
    headers.set("Accept", "application/json, application/problem+json");
    let resposta: Response;
    try {
      resposta = await fetch(url, { ...opcoes, headers });
    } catch (erro) {
      if (opcoes.signal?.aborted) throw erro;
      throw new ErroCampanhas(0, "Não foi possível conectar ao Gateway.");
    }
    await verificarResposta(resposta);
    return resposta;
  }
  return {
    async listar(filtros: Filtros, pagina: number, signal?: AbortSignal) {
      const url = new URL(rota);
      url.searchParams.set("limit", String(tamanhoPagina));
      url.searchParams.set("offset", String(pagina * tamanhoPagina));
      if (filtros.tipo) url.searchParams.set("tipo_sanguineo", filtros.tipo);
      if (filtros.status) url.searchParams.set("status", filtros.status);
      if (filtros.vigentes) url.searchParams.set("vigentes", "true");
      const resposta = await enviar(url, { signal });
      const contagem = resposta.headers.get("X-Total-Count");
      const itens: Campanha[] = await resposta.json();
      return { itens, total: contagem !== null && /^\d+$/.test(contagem) ? Number(contagem) : null };
    },
    async criar(campanha: NovaCampanha): Promise<Campanha> {
      const resposta = await enviar(rota, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(campanha)
      });
      return resposta.json();
    }
  };
}

export function mensagemErro(erro: unknown) {
  return erro instanceof Error ? erro.message : "Não foi possível concluir a solicitação.";
}
