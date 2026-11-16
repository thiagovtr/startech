import httpx
from fastapi.testclient import TestClient

from bff_mobile.api.home import get_doadores, get_hemocentros
from bff_mobile.clients.servicos import DoadoresClient, HemocentrosClient
from bff_mobile.main import app
from bff_mobile.observabilidade import propagar_request_id


def test_request_id_chega_ao_doadores_e_ao_hemocentros():
    vistos = []

    def handler(req: httpx.Request):
        vistos.append((req.url.path, req.headers.get("x-request-id")))
        if req.url.path.startswith("/api/v1/doadores"):
            return httpx.Response(200, json={"id": "1", "tipoSanguineo": "O-"})
        return httpx.Response(200, json=[])

    def cliente():
        return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://x",
                                 event_hooks={"request": [propagar_request_id]})

    app.dependency_overrides[get_doadores] = lambda: DoadoresClient(cliente())
    app.dependency_overrides[get_hemocentros] = lambda: HemocentrosClient(cliente())
    try:
        r = TestClient(app).get("/bff-mobile/home", headers={"X-User-Id": "1", "X-Request-Id": "m-42"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200 and r.headers["x-request-id"] == "m-42"
    assert [rid for _, rid in vistos] == ["m-42", "m-42"]
