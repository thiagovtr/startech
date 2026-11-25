"""Base de conhecimento (Bloco 15): Portaria MS nº 5/2017, Anexo IV, em trechos por seção.

Cada seção `## Título` do Markdown vira um documento (o título vai junto do texto, o que melhora a busca).
Os embeddings vêm do Ollama (`nomic-embed-text`) e ficam num `InMemoryVectorStore` do LangChain: a base tem
poucas dezenas de trechos, então um índice em memória, montado na subida em poucos segundos, dispensa um
banco vetorial à parte (Chroma/FAISS) e um volume persistente.
"""

import asyncio
import logging
import re
import unicodedata
from importlib import resources

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore

logger = logging.getLogger(__name__)

ARQUIVOS = ("portaria-5-2017-anexo-iv.md",)
FONTE = "Portaria de Consolidação MS nº 5/2017, Anexo IV"

# Palavras muito frequentes em quase toda pergunta do domínio: removê-las da pontuação lexical evita que seções
# genéricas ("Idade para doar sangue") dominem buscas sobre temas específicos (jejum, dengue, academia, remédios).
_STOPWORDS = frozenset({
    "doar", "doacao", "doacoes", "doador", "doadora", "sangue", "sanguineo", "hemocentro", "hemocentros",
    "posso", "pode", "podem", "quero", "tenho", "estou", "preciso", "fazer", "faco", "consegue", "consigo",
    "para", "pela", "pelo", "pelas", "pelos", "com", "sem", "por", "que", "uma", "uns", "umas", "dos", "das",
    "nos", "nas", "como", "qual", "quais", "quanto", "quanta", "quantos", "tempo", "mais", "menos", "muito",
    "mesmo", "minha", "meu", "meus", "minhas", "voce", "dia", "dias", "mes", "meses", "ano", "anos", "ontem",
    "hoje", "amanha", "depois", "antes", "sobre", "existe", "esta", "estao", "estar", "sao", "ser", "ter",
    "sou", "tive", "fiz", "tomei", "tomo", "ir", "mim", "isso", "esse", "essa", "esta", "este", "aqui",
    "ainda", "agora", "quando", "onde", "porque", "causa", "apenas", "somente", "entre", "desde", "ate",
    "todos", "todas", "todo", "toda", "outro", "outra", "algum", "alguma", "recentemente", "proximo", "proxima",
})


def _tokens_relevantes(texto: str) -> list[str]:
    normalizado = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    brutos = re.findall(r"[a-z]+", normalizado)
    return [t for t in brutos if (len(t) >= 3 or t == "kg") and t not in _STOPWORDS]


def _casa_token(consulta: str, vocabulario: set[str]) -> bool:
    if consulta in vocabulario:
        return True
    if len(consulta) >= 5:
        raiz = consulta[:5]
        return any(v.startswith(raiz) for v in vocabulario)
    return False


def _score_lexical(tokens_pergunta: list[str], doc: Document) -> float:
    if not tokens_pergunta:
        return 0.0
    titulo = set(_tokens_relevantes(doc.metadata.get("secao", "")))
    corpo = set(_tokens_relevantes(doc.page_content))
    pontos = 0.0
    for tok in set(tokens_pergunta):
        if _casa_token(tok, titulo):
            pontos += 2.0
        elif _casa_token(tok, corpo):
            pontos += 1.0
    return pontos / len(set(tokens_pergunta))


def carregar_documentos() -> list[Document]:
    docs: list[Document] = []
    for nome in ARQUIVOS:
        texto = resources.files("rag.data").joinpath(nome).read_text(encoding="utf-8")
        for bloco in re.split(r"^## ", texto, flags=re.MULTILINE)[1:]:
            titulo, _, corpo = bloco.partition("\n")
            corpo = corpo.strip()
            if corpo:
                docs.append(Document(
                    page_content=f"{titulo.strip()}: {corpo}",
                    metadata={"secao": titulo.strip(), "fonte": FONTE, "arquivo": nome},
                ))
    return docs


class BaseConhecimento:
    def __init__(self, embeddings: Embeddings):
        self._embeddings = embeddings
        self._store: InMemoryVectorStore | None = None
        self._docs: list[Document] = []

    @property
    def pronta(self) -> bool:
        return self._store is not None

    async def montar(self) -> int:
        store = InMemoryVectorStore(self._embeddings)
        docs = carregar_documentos()
        await store.aadd_documents(docs)
        self._store = store
        self._docs = docs
        return len(docs)

    async def montar_com_retentativas(self, espera: float) -> None:
        """Tenta até conseguir (o Ollama pode subir depois ou ainda estar baixando o modelo)."""
        while True:
            try:
                n = await self.montar()
                logger.info("Base de conhecimento indexada: %d trechos", n)
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Índice não montado (%s). Nova tentativa em %.0fs", exc, espera)
                await asyncio.sleep(espera)

    async def buscar(self, pergunta: str, k: int) -> list[Document]:
        """Busca híbrida: combina ranking vetorial (embeddings) com pontuação lexical por palavras-chave."""
        if self._store is None:
            raise RuntimeError("base de conhecimento ainda não indexada")
        k_vetorial = min(len(self._docs), max(k * 3, 8)) if self._docs else k
        vetoriais = await self._store.asimilarity_search(pergunta, k=k_vetorial)
        tokens = _tokens_relevantes(pergunta)
        if not tokens or not self._docs:
            return vetoriais[:k]

        pontuacao: dict[str, float] = {}
        por_secao: dict[str, Document] = {}
        for pos, doc in enumerate(vetoriais):
            chave = doc.metadata.get("secao", doc.page_content[:60])
            por_secao[chave] = doc
            pontuacao[chave] = 1.0 / (pos + 1)

        for doc in self._docs:
            chave = doc.metadata.get("secao", doc.page_content[:60])
            lex = _score_lexical(tokens, doc)
            if lex > 0:
                por_secao.setdefault(chave, doc)
                pontuacao[chave] = pontuacao.get(chave, 0.0) + 2.5 * lex

        ordenados = sorted(pontuacao.items(), key=lambda item: item[1], reverse=True)
        return [por_secao[chave] for chave, _ in ordenados[:k]]
