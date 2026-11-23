import asyncio
import time

import pytest

from rag.services import ferramentas
from rag.services.assistente import FALLBACK_CAMPANHAS, FALLBACK_LLM
from rag.services.base_conhecimento import BaseConhecimento, carregar_documentos
from rag.services.circuito import ABERTO, FECHADO, MEIO_ABERTO, Circuito, CircuitoAberto
from tests.conftest import LLMLento, hemocentros_fake, llm_fake, montar_assistente

# ---- base de conhecimento ----


def test_documentos_por_secao_com_fonte():
    docs = carregar_documentos()
    secoes = {d.metadata["secao"] for d in docs}
    assert {"Peso mínimo", "Intervalo entre doações e frequência anual", "Tatuagem, maquiagem definitiva e piercing",
            "Gripe, resfriado e febre"} <= secoes
    assert all("Portaria de Consolidação MS nº 5/2017" in d.metadata["fonte"] for d in docs)


@pytest.mark.parametrize("pergunta,secao", [
    ("Qual o peso mínimo para doar sangue?", "Peso mínimo"),
    ("Fiz uma tatuagem há 3 meses, posso doar?", "Tatuagem, maquiagem definitiva e piercing"),
    ("Qual o intervalo entre doações para homens e mulheres?", "Intervalo entre doações e frequência anual"),
    ("Estou com gripe, quando posso doar?", "Gripe, resfriado e febre"),
])
def test_recuperacao_traz_a_secao_certa(base, pergunta, secao):
    docs = asyncio.run(base.buscar(pergunta, k=3))
    assert docs[0].metadata["secao"] == secao


def test_base_nao_montada_falha_na_busca():
    from tests.conftest import EmbeddingsPalavras

    with pytest.raises(RuntimeError):
        asyncio.run(BaseConhecimento(EmbeddingsPalavras()).buscar("peso", 3))


# ---- circuit breaker ----


class Relogio:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


async def _falha():
    raise ConnectionError("fora")


async def _ok():
    return "ok"


async def _lenta():
    await asyncio.sleep(1)


def test_circuito_abre_falha_rapido_e_fecha_no_teste():
    rel = Relogio()
    c = Circuito("t", limite=3, aberto_por=30, timeout=0.05, relogio=rel)

    async def go():
        for _ in range(2):
            with pytest.raises(ConnectionError):
                await c.chamar(_falha)
        assert c.estado == FECHADO
        with pytest.raises(TimeoutError):  # timeout também conta
            await c.chamar(_lenta)
        assert c.estado == ABERTO
        with pytest.raises(CircuitoAberto):
            await c.chamar(_ok)
        rel.t = 31
        assert c.estado == MEIO_ABERTO
        assert await c.chamar(_ok) == "ok"
        assert c.estado == FECHADO

    asyncio.run(go())


def test_falha_no_meio_aberto_reabre():
    rel = Relogio()
    c = Circuito("t", limite=1, aberto_por=10, timeout=1, relogio=rel)

    async def go():
        with pytest.raises(ConnectionError):
            await c.chamar(_falha)
        rel.t = 11
        with pytest.raises(ConnectionError):
            await c.chamar(_falha)
        assert c.estado == ABERTO

    asyncio.run(go())


def test_sucesso_zera_a_contagem():
    c = Circuito("t", limite=2, aberto_por=10, timeout=1)

    async def go():
        with pytest.raises(ConnectionError):
            await c.chamar(_falha)
        await c.chamar(_ok)
        with pytest.raises(ConnectionError):
            await c.chamar(_falha)
        assert c.estado == FECHADO

    asyncio.run(go())


# ---- ferramenta de campanhas ----


@pytest.mark.parametrize("pergunta", ["Onde posso doar hoje?", "onde consigo doar sangue", "Quais campanhas ativas?",
                                      "Tem hemocentro perto de mim hoje?"])
def test_intencao_de_campanhas(pergunta):
    assert ferramentas.e_pergunta_de_campanhas(pergunta)


@pytest.mark.parametrize("pergunta", ["Qual o peso mínimo?", "Fiz tatuagem, posso doar?", "Quantas vezes por ano posso doar?",
                                      "Bebi cerveja ontem, posso doar hoje de manhã?"])
def test_outras_perguntas_nao_vao_para_a_ferramenta(pergunta):
    assert not ferramentas.e_pergunta_de_campanhas(pergunta)


@pytest.mark.parametrize("pergunta,dentro", [
    ("Qual a capital da França?", False), ("Como fazer um bolo de chocolate?", False),
    ("Quem ganhou a copa de 2002?", False), ("Qual o melhor time de futebol?", False),
    ("Fiz uma tatuagem há 3 meses", True), ("Bebi cerveja ontem, posso doar?", True),
    ("Tenho 17 anos", True), ("Arranquei um dente", True), ("Tenho diabetes", True),
])
def test_filtro_de_dominio(pergunta, dentro):
    assert ferramentas.e_do_dominio(pergunta) is dentro


def test_pergunta_fora_do_escopo_recusa_sem_llm(base):
    lento = LLMLento(messages=iter([]), atraso=5)  # se fosse chamado, cairia no timeout
    r = asyncio.run(montar_assistente(base, llm=lento, timeout=0.2).responder("Qual a capital da França?"))
    assert r.modo == "FORA_DO_ESCOPO" and r.resposta.startswith("Não encontrei") and r.uso is None


def test_saudacao_e_ajuda_sobre_o_app_respondem_de_forma_amigavel(base):
    lento = LLMLento(messages=iter([]), atraso=5)
    assistente = montar_assistente(base, llm=lento, timeout=0.2)

    r_oi = asyncio.run(assistente.responder("Olá, boa noite!"))
    assert r_oi.modo == "RAG" and "assistente virtual da StarTech" in r_oi.resposta

    r_app = asyncio.run(assistente.responder("Queria ajuda sobre esse app. Do que ele se trata? Tô perdido"))
    assert r_app.modo == "RAG" and "plataforma de apoio à doação de sangue" in r_app.resposta
    assert r_app.fontes[0]["secao"] == "Sobre a StarTech"


def test_saudacao_com_pergunta_de_dominio_segue_para_rag(base):
    r = asyncio.run(montar_assistente(base).responder("Olá, boa noite! Qual o peso mínimo para doar?"))
    assert r.modo == "RAG" and "50 kg" in r.resposta and r.fontes[0]["secao"] == "Peso mínimo"


def test_ferramenta_filtra_vigentes_e_passa_os_filtros():
    chamadas: list = []

    async def go():
        return await ferramentas.buscar_campanhas(hemocentros_fake(chamadas=chamadas), "O-", 5)

    campanhas = asyncio.run(go())
    assert [c["id"] for c in campanhas] == ["1"]  # a encerrada sai mesmo se o serviço a devolver
    params = dict(chamadas[0].url.params)
    assert params == {"status": "ATIVA", "vigentes": "true", "limit": "5", "tipo_sanguineo": "O-"}


# ---- assistente ----


def test_rag_responde_com_fontes_e_uso(base):
    r = asyncio.run(montar_assistente(base).responder("Qual o peso mínimo para doar?"))
    assert r.modo == "RAG" and "50 kg" in r.resposta and "triagem" in r.resposta
    assert r.fontes[0]["secao"] == "Peso mínimo"
    assert r.uso == {"tokensEntrada": 300, "tokensSaida": 20}


def test_prompt_rag_leva_o_contexto_e_a_instrucao_de_recusa(base):
    llm = llm_fake()
    asyncio.run(montar_assistente(base, llm=llm).responder("Qual o peso mínimo para doar?"))
    # GenericFakeChatModel não guarda a entrada; verificamos o prompt montado diretamente
    from rag.services.assistente import PROMPT_RAG

    texto = PROMPT_RAG.format(fonte="F", contexto="[Peso mínimo] 50 kg", pergunta="p")
    assert "SOMENTE as regras do CONTEXTO" in texto and "não invente" in texto and "50 kg" in texto


def test_sem_rag_nao_usa_contexto(base):
    r = asyncio.run(montar_assistente(base, llm=llm_fake("Uns 45 kg.")).responder("Peso mínimo?", usar_rag=False))
    assert r.modo == "SEM_RAG" and r.fontes == [] and r.resposta == "Uns 45 kg."


def test_llm_lento_cai_no_fallback_dentro_do_timeout_com_o_trecho(base):
    lento = LLMLento(messages=iter([]), atraso=5)
    inicio = time.perf_counter()
    r = asyncio.run(montar_assistente(base, llm=lento, timeout=0.3).responder("Qual o peso mínimo para doar?"))
    assert time.perf_counter() - inicio < 2
    assert r.modo == "FALLBACK" and r.motivo_fallback == "timeout"
    assert r.resposta.startswith(FALLBACK_LLM) and "50 kg" in r.resposta  # trecho recuperado, sem LLM


def test_circuito_aberto_responde_na_hora(base):
    a = montar_assistente(base, llm=LLMLento(messages=iter([]), atraso=5), timeout=0.1)

    async def go():
        for _ in range(3):
            await a.responder("Qual o peso mínimo?")
        inicio = time.perf_counter()
        r = await a.responder("Qual o peso mínimo?")
        return r, time.perf_counter() - inicio

    r, duracao = asyncio.run(go())
    assert r.motivo_fallback == "circuito aberto" and duracao < 0.1


def test_ollama_fora_na_busca_abre_o_circuito(base):
    class EmbeddingsFora:
        def embed_query(self, _):
            raise ConnectionError("ollama fora")

    a = montar_assistente(base)
    base._store.embedding = EmbeddingsFora()  # type: ignore[union-attr]

    async def go():
        return [await a.responder("Qual o peso mínimo?") for _ in range(4)]

    rs = asyncio.run(go())
    assert all(r.modo == "FALLBACK" for r in rs)
    assert rs[-1].motivo_fallback == "busca: circuito aberto" and a.circuito_busca.estado == ABERTO


def test_pergunta_de_campanhas_usa_a_ferramenta(base):
    r = asyncio.run(montar_assistente(base).responder("Onde posso doar hoje?", tipo_sanguineo="O-"))
    assert r.modo == "FERRAMENTA" and "Hemominas Lavras" in r.resposta and "encerrada" not in r.resposta


def test_hemocentros_fora_cai_no_fallback(base):
    r = asyncio.run(montar_assistente(base, hemocentros=hemocentros_fake(503)).responder("Onde posso doar hoje?"))
    assert r.modo == "FALLBACK" and r.resposta == FALLBACK_CAMPANHAS


def test_indice_pendente_cai_no_fallback():
    from tests.conftest import EmbeddingsPalavras

    vazia = BaseConhecimento(EmbeddingsPalavras())
    r = asyncio.run(montar_assistente(vazia).responder("Qual o peso mínimo?"))
    assert r.modo == "FALLBACK" and r.motivo_fallback.startswith("busca")


def test_fluxo_usa_chains_lcel(base):
    from langchain_core.runnables import RunnableSequence

    a = montar_assistente(base)
    assert isinstance(a.cadeia_rag, RunnableSequence) and isinstance(a.cadeia_sem_rag, RunnableSequence)
