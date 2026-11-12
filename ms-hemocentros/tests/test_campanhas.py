from fastapi.testclient import TestClient
from hemocentros.main import app

client = TestClient(app)


def test_lista_todas():
    r = client.get("/api/v1/campanhas")
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_filtra_por_tipo_sanguineo():
    r = client.get("/api/v1/campanhas", params={"tipo_sanguineo": "O-"})
    assert [c["id"] for c in r.json()] == ["camp-001"]


def test_openapi_documenta_rota():
    assert "/api/v1/campanhas" in client.get("/openapi.json").json()["paths"]
