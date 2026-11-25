"""Ferramenta "Onde posso doar hoje?" (Bloco 17): campanhas vigentes no ms-hemocentros.

A pergunta é roteada para cá por intenção (regra simples), e não por *tool calling* do modelo: um LLM de 1,5B
escolhe ferramentas de forma instável, e a resposta precisa caber no timeout de 4 s. A ferramenta continua sendo
uma `Tool` do LangChain (reutilizável por um agente no futuro); a resposta é montada de forma determinística.
"""

import re
import unicodedata
from datetime import date
from typing import Any

import httpx
from langchain_core.tools import StructuredTool

_INTENCAO = re.compile(
    r"\bonde\b.*\b(doar|doacao|hemocentro|campanha)|\b(campanhas?|hemocentros?)\b.*\b(hoje|perto|ativas?|abertas?|vigentes?)"
)

_SAUDACAO = re.compile(
    r"^\s*(oi+|ola+|opa+|e\s+ai|salve|bom\s+dia|boa\s+tarde|boa\s+noite|tudo\s+bem|como\s+vai|obrigad[oa]|valeu)\b"
)

_AJUDA_APP = re.compile(
    r"\b(app|aplicativo|startech|plataforma|sistema)\b|\b(como\s+funciona|do\s+que\s+se\s+trata|o\s+que\s+(voce|vc|ele)\s+faz|preciso\s+de\s+ajuda|queria\s+ajuda|to\s+perdido|estou\s+perdido|me\s+ajuda|como\s+usar|como\s+agendar)\b"
)


# Radicais de termos do domínio (doação de sangue e critérios da Portaria). Pergunta sem nenhum deles está fora
# do escopo do assistente e é recusada sem chamar o LLM.
_DOMINIO = (
    "doa", "doad", "sangu", "hemo", "transfus", "triag", "apt", "inapt", "impedi", "tatu", "piercing", "maquiag",
    "gripe", "gripad", "resfri", "febre", "dengu", "zika", "chikunguny", "alcool", "bebi", "cervej", "vinho",
    "gravid", "gestant", "parto", "cesar", "amament", "dente", "dentar", "odont", "canal", "endoscop", "colonoscop",
    "vacin", "hemoglobin", "anemi", "peso", "quilo", "kg", "idade", "anos", "menor", "idos", "interval", "frequen",
    "vezes", "doenc", "remedi", "medicament", "antibiot", "cirurg", "diabet", "insul", "hipertens", "hepatit", "hiv",
    "aids", "chagas", "htlv", "malar", "pressao", "jejum", "aliment", "documento", "drog", "injetav", "sering",
    "agulh", "maconh", "cocain", "crack", "academi", "exercic", "esforc", "fisic", "taxa", "pagar", "gratuit",
    "volum", "recuper", "etap", "process", "agend", "horari", "cancel", "reagend",
)


def e_do_dominio(pergunta: str) -> bool:
    palavras = re.findall(r"[a-z0-9]+", _normalizar(pergunta))
    return any(p.startswith(r) for p in palavras for r in _DOMINIO)


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


def e_pergunta_de_campanhas(pergunta: str) -> bool:
    return bool(_INTENCAO.search(_normalizar(pergunta)))


def e_saudacao(pergunta: str) -> bool:
    """Identifica cumprimentos curtos para responder com boas-vindas sem acionar recusa fria."""
    return bool(_SAUDACAO.search(_normalizar(pergunta)))


def e_pergunta_sobre_app(pergunta: str) -> bool:
    """Identifica dúvidas sobre o propósito ou uso do aplicativo StarTech."""
    return bool(_AJUDA_APP.search(_normalizar(pergunta)))


async def buscar_campanhas(cliente: httpx.AsyncClient, tipo_sanguineo: str | None, limite: int) -> list[dict[str, Any]]:
    """Campanhas ATIVAS e vigentes (data_fim >= hoje), da leitura CQRS no MongoDB."""
    params: dict[str, Any] = {"status": "ATIVA", "vigentes": "true", "limit": limite}
    if tipo_sanguineo:
        params["tipo_sanguineo"] = tipo_sanguineo
    r = await cliente.get("/api/v1/campanhas", params=params)
    r.raise_for_status()
    hoje = date.today().isoformat()
    # Filtro defensivo (o contrato antigo não filtrava vigência): só ativas e não encerradas.
    campanhas = [c for c in r.json() if c.get("status") == "ATIVA" and str(c.get("data_fim", "")) >= hoje]
    return campanhas[:limite]


def formatar(campanhas: list[dict[str, Any]], tipo_sanguineo: str | None) -> str:
    alvo = f" para o tipo {tipo_sanguineo}" if tipo_sanguineo else ""
    if not campanhas:
        return (f"No momento não há campanhas ativas{alvo}. Você ainda pode procurar o hemocentro mais próximo "
                "para doar: o estoque de todos os tipos sanguíneos precisa de reposição contínua.")
    linhas = [f"Campanhas ativas{alvo}:"]
    for c in campanhas:
        urg = f", urgência {c['urgencia']}" if c.get("urgencia") else ""
        linhas.append(f"- {c.get('titulo')} — {c.get('hemocentro')} (tipo {c.get('tipo_sanguineo')}{urg}, "
                      f"até {c.get('data_fim')})")
    return "\n".join(linhas)


def criar_tool(cliente: httpx.AsyncClient, limite: int) -> StructuredTool:
    async def campanhas_vigentes(tipo_sanguineo: str | None = None) -> str:
        """Lista as campanhas de doação de sangue ativas hoje, opcionalmente filtradas pelo tipo sanguíneo."""
        return formatar(await buscar_campanhas(cliente, tipo_sanguineo, limite), tipo_sanguineo)

    return StructuredTool.from_function(coroutine=campanhas_vigentes, name="campanhas_vigentes")
