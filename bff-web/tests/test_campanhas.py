from fastapi.testclient import TestClient

from bff_web.main import app


def test_campanhas_mock():
    r = TestClient(app).get("/bff-web/campanhas")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert len(r.json()["campanhas"]) == 2
