"""Critério de aceite do Bloco 18: escrita reflete no MongoDB em menos de 2 s (ADR aceita 1-3 s)."""

import statistics
import time
import uuid

from fastapi.testclient import TestClient

from hemocentros.config import get_settings
from hemocentros.main import app
from tests.conftest import TEST_MONGO_DB, TEST_MONGO_URL, TEST_PG_URL

LIMITE_S = 2.0
AMOSTRAS = 20


def test_escrita_reflete_na_view_em_menos_de_2s(pg_engine, mongo_view, amqp_url, monkeypatch, capsys):
    sufixo = uuid.uuid4().hex[:8]
    for k, v in {
        "POSTGRES_URL": TEST_PG_URL, "MONGO_URL": TEST_MONGO_URL, "MONGO_DB": TEST_MONGO_DB,
        "RABBITMQ_URL": amqp_url, "RABBITMQ_EXCHANGE": f"test.{sufixo}", "RABBITMQ_QUEUE": f"test.cqrs.{sufixo}",
        "OUTBOX_WORKER_HABILITADO": "true", "CONSUMIDOR_HABILITADO": "true", "OUTBOX_INTERVALO": "0.2",
    }.items():
        monkeypatch.setenv(f"HEMOCENTROS_{k}", v)
    get_settings.cache_clear()
    latencias = []
    try:
        with TestClient(app) as c:
            time.sleep(1.5)  # conexões dos workers
            for i in range(AMOSTRAS):
                t0 = time.perf_counter()
                r = c.post("/api/v1/campanhas", json={
                    "titulo": f"Campanha {i}", "hemocentro": "Lavras", "tipo_sanguineo": "O-",
                    "data_inicio": "2026-11-10", "data_fim": "2026-11-30"})
                assert r.status_code == 201
                cid = r.json()["id"]
                while time.perf_counter() - t0 < 5:
                    if cid in {x["id"] for x in c.get("/api/v1/campanhas", params={"tipo_sanguineo": "O-"}).json()}:
                        break
                    time.sleep(0.02)
                else:
                    raise AssertionError(f"campanha {cid} não chegou à view em 5 s")
                latencias.append(time.perf_counter() - t0)
    finally:
        get_settings.cache_clear()
    with capsys.disabled():
        print(f"\n[latência escrita->leitura] n={AMOSTRAS} mediana={statistics.median(latencias):.3f}s "
              f"p95={sorted(latencias)[int(AMOSTRAS * 0.95) - 1]:.3f}s max={max(latencias):.3f}s")
    assert max(latencias) < LIMITE_S
