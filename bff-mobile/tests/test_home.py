from fastapi.testclient import TestClient

from bff_mobile.main import app


def test_home_mock():
    r = TestClient(app).get("/bff-mobile/home")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["doador"]["tipo_sanguineo"] == "O-"
    assert len(body["campanhas"]) == 1
