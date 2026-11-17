import json

import httpx
from fastapi.testclient import TestClient

from bff_mobile.api.assistente import FALLBACK, get_doadores, get_rag
from bff_mobile.clients.servicos import DoadoresClient, RagClient
from bff_mobile.main import app

USUARIO = {"X-User-Id": "doador-1", "X-User-Roles": "doador"}


def _clientes(rag_handler, doadores_handler):
    rag_reqs: list[httpx.Request] = []

    def rag_reg(req):
        rag_reqs.append(req)
        return rag_handler(req)

    rag = RagClient(httpx.AsyncClient(transport=httpx.MockTransport(rag_reg), base_url="http://r"))
    doa = DoadoresClient(httpx.AsyncClient(transport=httpx.MockTransport(doadores_handler), base_url="http://d"))
    app.dependency_overrides[get_rag] = lambda: rag
    app.dependency_overrides[get_doadores] = lambda: doa
    return TestClient(app), rag_reqs


def teardown_function():
    app.dependency_overrides.clear()


def test_injeta_o_tipo_sanguineo_do_perfil():
    client, reqs = _clientes(
        lambda r: httpx.Response(200, json={"resposta": "Campanhas...", "modo": "FERRAMENTA", "fontes": []}),
        lambda r: httpx.Response(200, json={"id": "doador-1", "tipoSanguineo": "O-"}),
    )
    r = client.post("/bff-mobile/assistente", json={"pergunta": "Onde posso doar hoje?"}, headers=USUARIO)
    assert r.status_code == 200 and r.json()["modo"] == "FERRAMENTA" and r.json()["degradado"] is False
    assert json.loads(reqs[0].content) == {"pergunta": "Onde posso doar hoje?", "usarRag": True, "tipoSanguineo": "O-"}


def test_perfil_fora_segue_sem_tipo():
    client, reqs = _clientes(
        lambda r: httpx.Response(200, json={"resposta": "50 kg", "modo": "RAG", "fontes": []}),
        lambda r: httpx.Response(503),
    )
    r = client.post("/bff-mobile/assistente", json={"pergunta": "Peso mínimo?"}, headers=USUARIO)
    assert r.status_code == 200 and "tipoSanguineo" not in json.loads(reqs[0].content)


def test_rag_fora_devolve_fallback_200():
    def falha(req):
        raise httpx.ConnectError("fora")

    client, _ = _clientes(falha, lambda r: httpx.Response(404))
    r = client.post("/bff-mobile/assistente", json={"pergunta": "Peso mínimo?"}, headers=USUARIO)
    assert r.status_code == 200 and r.json()["resposta"] == FALLBACK and r.json()["degradado"] is True


def test_sem_usuario_401_e_pergunta_invalida_400():
    client, _ = _clientes(lambda r: httpx.Response(200, json={}), lambda r: httpx.Response(404))
    assert client.post("/bff-mobile/assistente", json={"pergunta": "Peso?"},
                       headers={"X-User-Roles": "doador"}).status_code == 401
    assert client.post("/bff-mobile/assistente", json={"pergunta": "x"}, headers=USUARIO).status_code == 400
