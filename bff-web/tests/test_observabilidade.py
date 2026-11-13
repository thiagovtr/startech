import json
import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from bff_web.clients.hemocentros import HemocentrosClient, get_hemocentros_client
from bff_web.main import app
from bff_web.observabilidade import FormatadorJson, propagar_request_id, request_id_var


@pytest.fixture
def recebidos():
    vistos: list[str | None] = []

    def handler(req: httpx.Request):
        vistos.append(req.headers.get("x-request-id"))
        return httpx.Response(200, json=[])

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://hemo",
                             event_hooks={"request": [propagar_request_id]})
    app.dependency_overrides[get_hemocentros_client] = lambda: HemocentrosClient(http)
    yield vistos
    app.dependency_overrides.clear()


def test_request_id_recebido_volta_na_resposta_e_segue_para_o_servico(recebidos):
    r = TestClient(app).get("/bff-web/campanhas", headers={"X-Request-Id": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123" and recebidos == ["abc-123"]


def test_sem_request_id_um_novo_e_gerado_e_propagado(recebidos):
    r = TestClient(app).get("/bff-web/campanhas")
    rid = r.headers["x-request-id"]
    assert len(rid) == 32 and recebidos == [rid]


def test_request_id_malicioso_e_substituido(recebidos):
    r = TestClient(app).get("/bff-web/campanhas", headers={"X-Request-Id": "x\" injetado {"})
    assert r.headers["x-request-id"] != "x\" injetado {" and len(r.headers["x-request-id"]) == 32


def test_health_tambem_devolve_o_id():
    assert TestClient(app).get("/health", headers={"X-Request-Id": "h1"}).headers["x-request-id"] == "h1"


def test_log_json_tem_servico_e_request_id():
    token = request_id_var.set("r-9")
    try:
        rec = logging.LogRecord("x", logging.INFO, __file__, 1, "ola %s", ("mundo",), None)
        rec.request_id = request_id_var.get()
        rec.status = 200
        dados = json.loads(FormatadorJson().format(rec))
    finally:
        request_id_var.reset(token)
    assert dados["servico"] == "bff-web" and dados["request_id"] == "r-9"
    assert dados["msg"] == "ola mundo" and dados["status"] == 200
