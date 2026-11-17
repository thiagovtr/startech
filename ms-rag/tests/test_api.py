import os

from fastapi.testclient import TestClient

# Ollama e ms-hemocentros inalcançáveis: a API deve degradar (fallback), nunca cair.
os.environ.setdefault("RAG_OLLAMA_URL", "http://127.0.0.1:1")
os.environ.setdefault("RAG_HEMOCENTROS_URL", "http://127.0.0.1:1")
os.environ.setdefault("RAG_AQUECER_MODELO", "false")
os.environ.setdefault("RAG_TIMEOUT_LLM", "1")

from rag.main import app  # noqa: E402


def test_sem_ollama_responde_fallback_200():
    with TestClient(app) as client:
        r = client.post("/api/v1/rag/perguntas", json={"pergunta": "Qual o peso mínimo para doar?"},
                        headers={"X-Request-Id": "abc-1"})
        h = client.get("/health").json()
    assert r.status_code == 200 and r.headers["X-Request-Id"] == "abc-1"
    assert r.json()["modo"] == "FALLBACK"
    assert h["status"] == "degradado" and h["indice"] == "pendente"


def test_ferramenta_sem_hemocentros_responde_fallback():
    with TestClient(app) as client:
        r = client.post("/api/v1/rag/perguntas", json={"pergunta": "Onde posso doar hoje?", "tipoSanguineo": "O-"})
    assert r.status_code == 200 and r.json()["modo"] == "FALLBACK"


def test_payload_invalido_problem_json():
    with TestClient(app) as client:
        r = client.post("/api/v1/rag/perguntas", json={"pergunta": "x", "tipoSanguineo": "Z+"})
        ready = client.get("/ready")
    assert r.status_code == 400 and r.headers["content-type"] == "application/problem+json"
    assert {p["name"] for p in r.json()["invalidParams"]} == {"pergunta", "tipoSanguineo"}
    assert ready.status_code == 200
