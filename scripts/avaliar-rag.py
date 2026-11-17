"""Avaliação do assistente RAG (plano Dev 4, Bloco 20): 5 perguntas, com e sem RAG, latência, tokens e custo.

Roda DENTRO do contêiner do ms-rag (o serviço não tem porta no host), com a stack no ar:

    docker compose up -d --build ms-rag
    docker compose exec -T ms-rag python - < scripts/avaliar-rag.py > docs/ia/avaliacao-rag.md

Variáveis opcionais: REPETICOES (padrão 5), RAG_URL, HEMOCENTROS_URL, PRECO_HORA_SERVIDOR (US$/h da máquina que
roda o Ollama), PRECO_API_ENTRADA / PRECO_API_SAIDA (US$ por milhão de tokens de uma API paga, para comparação).
Antes de medir, cria uma campanha O- no ms-hemocentros para a pergunta "Onde posso doar hoje?".
"""

import json
import os
import statistics
import time
import urllib.request
from datetime import date, timedelta

RAG = os.getenv("RAG_URL", "http://127.0.0.1:8005")
HEMO = os.getenv("HEMOCENTROS_URL", "http://ms-hemocentros:8000")
N = int(os.getenv("REPETICOES", "5"))
PRECO_HORA = float(os.getenv("PRECO_HORA_SERVIDOR", "0.20"))
PRECO_ENT = float(os.getenv("PRECO_API_ENTRADA", "1.00"))
PRECO_SAI = float(os.getenv("PRECO_API_SAIDA", "5.00"))

# (pergunta, termos que uma resposta correta precisa conter segundo a Portaria)
PERGUNTAS = [
    ("Qual o peso mínimo para doar sangue?", ["50 kg"]),
    ("Qual o intervalo mínimo entre doações para homens e para mulheres?", ["60 dias", "90 dias"]),
    ("Fiz uma tatuagem recentemente. Quanto tempo preciso esperar para doar sangue?", ["12 meses"]),
    ("Estou gripado. Quanto tempo depois posso doar sangue?", ["7 dias"]),
    ("Onde posso doar hoje?", ["Hemocentro Regional de Lavras"]),
]


def post(url: str, corpo: dict, timeout: float = 30) -> dict:
    req = urllib.request.Request(url, data=json.dumps(corpo).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def criar_campanha() -> None:
    hoje = date.today()
    try:
        post(f"{HEMO}/api/v1/campanhas", {
            "titulo": "Estoque crítico O- (avaliação RAG)", "hemocentro": "Hemocentro Regional de Lavras",
            "tipo_sanguineo": "O-", "urgencia": "CRITICO", "data_inicio": hoje.isoformat(),
            "data_fim": (hoje + timedelta(days=30)).isoformat(),
        })
        time.sleep(2)  # consistência eventual da projeção CQRS no MongoDB
    except Exception as exc:  # noqa: BLE001 - a avaliação segue; a pergunta 5 ficará sem campanha
        print(f"<!-- campanha não criada: {exc} -->")


def acertou(resposta: str, termos: list[str]) -> bool:
    texto = resposta.lower().replace(" ", " ")
    return all(t.lower() in texto for t in termos)


def medir(pergunta: str, usar_rag: bool) -> list[dict]:
    out = []
    for _ in range(N):
        inicio = time.perf_counter()
        r = post(f"{RAG}/api/v1/rag/perguntas", {"pergunta": pergunta, "usarRag": usar_rag, "tipoSanguineo": "O-"})
        r["_total_ms"] = (time.perf_counter() - inicio) * 1000
        out.append(r)
    return out


def p95(v: list[float]) -> float:
    return sorted(v)[max(0, round(0.95 * len(v)) - 1)]


def main() -> None:
    criar_campanha()
    linhas, todas = [], {True: [], False: []}
    detalhes = []
    for pergunta, termos in PERGUNTAS:
        for usar in (False, True):
            rs = medir(pergunta, usar)
            todas[usar].extend(rs)
            lat = [r["latenciaMs"] for r in rs]
            ok = sum(acertou(r["resposta"], termos) for r in rs)
            modo = rs[0]["modo"]
            fb = sum(r["modo"] == "FALLBACK" for r in rs)
            linhas.append(f"| {pergunta} | {'com' if usar else 'sem'} | {modo} | {ok}/{N} | "
                          f"{statistics.mean(lat):.0f} | {p95(lat):.0f} | {fb} |")
            detalhes.append((pergunta, usar, rs[0]["resposta"].split("\n\n")[0], termos))

    def resumo(rs: list[dict]) -> tuple[float, float, float, float, float]:
        lat = [r["latenciaMs"] for r in rs]
        com_uso = [r["uso"] for r in rs if r.get("uso")]
        ent = statistics.mean(u["tokensEntrada"] for u in com_uso) if com_uso else 0
        sai = statistics.mean(u["tokensSaida"] for u in com_uso) if com_uso else 0
        return statistics.mean(lat), statistics.median(lat), p95(lat), ent, sai

    print("# Avaliação do assistente RAG — StarTech\n")
    print(f"Gerado por `scripts/avaliar-rag.py` em {date.today().isoformat()}. Cada pergunta foi feita {N} vezes "
          "em cada modo, com o modelo já carregado. Modelo de chat `qwen2.5:1.5b` e embeddings `nomic-embed-text`, "
          "via Ollama em CPU, com `temperature=0`, timeout de 4 s e circuit breaker.\n")
    print("**Critério de acerto:** a resposta contém os valores exatos da Portaria de Consolidação MS nº 5/2017, "
          "Anexo IV (por exemplo, `50 kg`, `60 dias` e `90 dias`). Para a pergunta 5, o acerto é citar o hemocentro "
          "de uma campanha real, criada no `ms-hemocentros` antes da medição.\n")
    print("## Resultados por pergunta\n")
    print("| Pergunta | RAG | Modo | Acertos | Latência média (ms) | p95 (ms) | Fallbacks |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    print("\n".join(linhas))
    print("\n## Respostas (primeira repetição)\n")
    for pergunta, usar, resposta, termos in detalhes:
        print(f"- **{'Com' if usar else 'Sem'} RAG — {pergunta}** (esperado: {', '.join(termos)})  \n  > "
              + resposta.replace("\n", " "))
    print("\n## Latência e tokens\n")
    print("| Modo | Média (ms) | Mediana (ms) | p95 (ms) | Tokens de entrada (média) | Tokens de saída (média) |")
    print("| --- | --- | --- | --- | --- | --- |")
    for usar in (False, True):
        m, md, p, e, s = resumo(todas[usar])
        print(f"| {'Com RAG' if usar else 'Sem RAG'} | {m:.0f} | {md:.0f} | {p:.0f} | {e:.0f} | {s:.0f} |")

    m, _, _, e, s = resumo(todas[True])
    por_hora = 3600 / (m / 1000)  # perguntas/h de uma instância atendendo em série
    custo_local = PRECO_HORA / por_hora * 1000
    custo_api = (e * PRECO_ENT + s * PRECO_SAI) / 1e6 * 1000
    print("\n## Projeção de custo\n")
    print(f"- **Local (Ollama em CPU):** cerca de {por_hora:.0f} perguntas/h por instância, atendendo em série com "
          f"média de {m / 1000:.2f} s. Com uma máquina de US$ {PRECO_HORA:.2f}/h, o custo é de ~US$ {custo_local:.3f} "
          "por 1.000 perguntas, se a instância estiver ocupada o tempo todo. O custo é fixo por hora: escalar exige "
          "mais réplicas do Ollama, cada uma com ~2 GB de RAM.")
    print(f"- **API paga (comparação):** com {e:.0f} tokens de entrada e {s:.0f} de saída por pergunta, a "
          f"US$ {PRECO_ENT:.2f} e US$ {PRECO_SAI:.2f} por milhão de tokens, o custo seria de ~US$ {custo_api:.3f} "
          "por 1.000 perguntas. O custo é variável e cresce linearmente com o uso, sem servidor dedicado.")
    print("- Os preços são **parâmetros da projeção**, não cotações. Ajuste `PRECO_HORA_SERVIDOR`, "
          "`PRECO_API_ENTRADA` e `PRECO_API_SAIDA` com valores atuais antes de apresentar.")


if __name__ == "__main__":
    main()
