"""Executor e worker de recuperação (PostgreSQL real + participantes simulados com httpx.MockTransport)."""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from orquestrador.clients.agendamentos import AgendamentosClient
from orquestrador.clients.doadores import DoadoresClient
from orquestrador.config import get_settings
from orquestrador.models.orm import OutboxEvent
from orquestrador.repositories import sagas as repo
from orquestrador.saga.estados import Passo, PassoConcluido, Politica, RespostaComunicacao
from orquestrador.saga.executor import Executor
from orquestrador.saga.maquina import transicionar
from orquestrador.services.recuperacao import executar_ciclo
from tests.conftest import TEST_PG_URL

T0 = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
RESERVA = {"agendamentoId": "x", "slotId": "slot-1", "dataHoraInicio": "2026-11-25T14:00:00Z",
           "dataHoraFim": "2026-11-25T14:20:00Z", "status": "CRIADO_PROVISORIO", "extra": "ignorado"}
RN01 = {"type": "urn:startech:error:intervalo-minimo", "title": "Doador inapto", "status": 422,
        "detail": "Doação há 10 dias; mínimo de 60."}


class Relogio:
    def __init__(self):
        self.agora = T0

    def __call__(self):
        return self.agora

    def avancar(self, **kw):
        self.agora += timedelta(**kw)


class Participantes:
    """ms-agendamentos e ms-doadores simulados. `respostas[(metodo, prefixo)]` = lista consumida em ordem."""

    def __init__(self, **respostas):
        self.chamadas: list[tuple[str, str, dict]] = []
        self.respostas = {
            ("POST", "/api/v1/slots"): [httpx.Response(201, json=RESERVA)],
            ("DELETE", "/api/v1/slots"): [httpx.Response(204)],
            ("POST", "/api/v1/agendamentos"): [httpx.Response(200, json={"status": "CONFIRMADO"})],
            ("POST", "/api/v1/doadores"): [httpx.Response(200, json={})],
            ("DELETE", "/api/v1/doadores"): [httpx.Response(204)],
        }
        nomes = {"reservar": ("POST", "/api/v1/slots"), "liberar_vaga": ("DELETE", "/api/v1/slots"),
                 "confirmar": ("POST", "/api/v1/agendamentos"), "elegibilidade": ("POST", "/api/v1/doadores"),
                 "liberar_elegibilidade": ("DELETE", "/api/v1/doadores")}
        for nome, lista in respostas.items():
            self.respostas[nomes[nome]] = lista

    def _handler(self, req: httpx.Request) -> httpx.Response:
        corpo = json.loads(req.content) if req.content else {}
        self.chamadas.append((req.method, req.url.path, {"key": req.headers.get("Idempotency-Key"), **corpo}))
        for (metodo, prefixo), lista in self.respostas.items():
            if req.method == metodo and req.url.path.startswith(prefixo):
                resposta = lista.pop(0) if len(lista) > 1 else lista[0]  # a última se repete
                if isinstance(resposta, Exception):
                    raise resposta
                return resposta
        raise AssertionError(f"chamada inesperada {req.method} {req.url.path}")

    def http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self._handler), base_url="http://p")

    def rotas(self) -> list[tuple[str, str]]:
        return [(m, p) for m, p, _ in self.chamadas]


@pytest.fixture
def sessoes(pg_engine):
    return async_sessionmaker(pg_engine, expire_on_commit=False)


def _executor(sessoes, participantes, relogio, politica=None):
    return Executor(
        sessoes, AgendamentosClient(participantes.http()), DoadoresClient(participantes.http()),
        politica or Politica(aguardar_resposta_passo3=False, max_retries=2), prazo_reivindicacao=15,
        relogio=relogio, jitter=lambda _ms: 0,
    )


async def _nova(sessoes, relogio, doador="doador-1"):
    criacao = await repo.criar(sessoes, doador_id=doador, slot_id="slot-1", agora=relogio(), max_retries=2,
                               correlation_id="req-1")
    return criacao.saga


async def _log(sessoes, saga_id):
    return [(r.step, r.acao, r.resultado) for r in await repo.listar_log(sessoes, saga_id)]


async def _outbox(sessoes):
    async with sessoes() as s:
        return [e.routing_key for e in await s.scalars(select(OutboxEvent).order_by(OutboxEvent.created_at))]


def _run(coro):
    return asyncio.run(coro)


# ------------------------------------------------------------------ caminho feliz


def test_caminho_feliz_sem_aguardar_comunicacao(sessoes):
    rel, part = Relogio(), Participantes()
    ex = _executor(sessoes, part, rel)

    async def go():
        saga = await _nova(sessoes, rel)
        final = await ex.avancar(saga.saga_id)
        return saga, final, await _log(sessoes, saga.saga_id), await _outbox(sessoes)

    saga, final, log, outbox = _run(go())
    assert final.status == "CONFIRMED" and final.next_attempt_at is None
    assert part.rotas() == [
        ("POST", "/api/v1/slots/slot-1/reservas"),
        ("POST", "/api/v1/doadores/doador-1/reservas-elegibilidade"),
        ("POST", f"/api/v1/agendamentos/{saga.agendamento_id}/confirmacao"),
    ]
    assert part.chamadas[1][2] == {"key": f"saga-{saga.saga_id}-step2", "agendamentoId": saga.agendamento_id,
                                   "dataSlot": "2026-11-25T14:00:00Z"}  # data do slot vinda do passo 1
    assert final.payload == {"dataHoraInicio": "2026-11-25T14:00:00Z", "dataHoraFim": "2026-11-25T14:20:00Z"}
    assert log == [("STEP1", "FORWARD", "OK"), ("STEP2", "FORWARD", "OK"), ("STEP3", "FORWARD", "PUBLICADO"),
                   ("STEP4", "FORWARD", "OK")]
    assert outbox == ["saga.comando.comunicacao.programar-lembrete", "saga.agendamento.confirmado"]


def test_aguardando_comunicacao_para_e_retoma_com_a_resposta(sessoes):
    rel, part = Relogio(), Participantes()
    ex = _executor(sessoes, part, rel, Politica(aguardar_resposta_passo3=True))

    async def go():
        saga = await _nova(sessoes, rel)
        parada = await ex.avancar(saga.saga_id)
        # resposta do ms-comunicacao (o consumidor do B9 fará isto)
        t = transicionar(repo.estado_de(parada), RespostaComunicacao(ok=True), ex.politica)
        await repo.aplicar_transicao(sessoes, parada, t, agora=rel())
        return parada, await ex.avancar(saga.saga_id)

    parada, final = _run(go())
    assert parada.status == "AWAITING_COMUNICACAO" and parada.deadline_at == T0 + timedelta(seconds=30)
    assert final.status == "CONFIRMED"


# ------------------------------------------------------------------ recusas e compensação


def test_slot_esgotado_rejeita_sem_compensar(sessoes):
    rel = Relogio()
    part = Participantes(reservar=[httpx.Response(409, json={"title": "Slot esgotado"})])

    async def go():
        saga = await _nova(sessoes, rel)
        return await _executor(sessoes, part, rel).avancar(saga.saga_id)

    final = _run(go())
    assert final.status == "REJECTED" and final.recusa == {"status": 409, "title": "Slot esgotado"}
    assert part.rotas() == [("POST", "/api/v1/slots/slot-1/reservas")]  # nenhum DELETE


def test_doador_inapto_rn01_libera_a_vaga_e_compensa(sessoes):
    rel = Relogio()
    part = Participantes(elegibilidade=[httpx.Response(422, json=RN01)])

    async def go():
        saga = await _nova(sessoes, rel)
        final = await _executor(sessoes, part, rel).avancar(saga.saga_id)
        return saga, final, await _log(sessoes, saga.saga_id), await _outbox(sessoes)

    saga, final, log, outbox = _run(go())
    assert final.status == "COMPENSATED" and final.recusa == RN01
    assert part.rotas()[-1] == ("DELETE", f"/api/v1/slots/slot-1/reservas/{saga.agendamento_id}")
    assert part.chamadas[-1][2]["key"] == f"saga-{saga.saga_id}-step1-comp"
    assert log == [("STEP1", "FORWARD", "OK"), ("STEP2", "FORWARD", "RECUSADO"), ("STEP1", "COMPENSATE", "OK")]
    assert outbox == ["saga.agendamento.compensado"]


# ------------------------------------------------------------------ falhas técnicas e retentativas


def test_falha_tecnica_agenda_retentativa_e_a_recuperacao_conclui(sessoes):
    rel = Relogio()
    part = Participantes(reservar=[httpx.Response(503), httpx.Response(201, json=RESERVA)])
    ex = _executor(sessoes, part, rel)

    async def go():
        saga = await _nova(sessoes, rel)
        parada = await ex.avancar(saga.saga_id)
        cedo = await executar_ciclo(ex, sessoes, rel(), 15, 10)  # backoff ainda não venceu
        rel.avancar(seconds=1)
        n = await executar_ciclo(ex, sessoes, rel(), 15, 10)
        return parada, cedo, n, await repo.obter(sessoes, saga.saga_id)

    parada, cedo, n, final = _run(go())
    assert (parada.status, parada.retry_count, parada.error_detail) == ("STARTED", 1, "ms-agendamentos: HTTP 503")
    assert parada.next_attempt_at == T0 + timedelta(milliseconds=500)
    assert cedo == 0 and n == 1 and final.status == "CONFIRMED"


def test_falha_tecnica_esgotada_compensa_inclusive_o_passo_incerto(sessoes):
    rel = Relogio()
    part = Participantes(elegibilidade=[httpx.ReadTimeout("lento")])
    ex = _executor(sessoes, part, rel)  # max_retries=2

    async def go():
        saga = await _nova(sessoes, rel)
        await ex.avancar(saga.saga_id)
        for _ in range(5):
            rel.avancar(seconds=10)
            await executar_ciclo(ex, sessoes, rel(), 15, 10)
        return saga, await repo.obter(sessoes, saga.saga_id)

    saga, final = _run(go())
    assert final.status == "COMPENSATED"
    assert part.rotas().count(("POST", "/api/v1/doadores/doador-1/reservas-elegibilidade")) == 3  # 1 + 2 retentativas
    assert part.rotas()[-2:] == [
        ("DELETE", f"/api/v1/doadores/doador-1/reservas-elegibilidade/{saga.agendamento_id}"),
        ("DELETE", f"/api/v1/slots/slot-1/reservas/{saga.agendamento_id}"),
    ]


def test_compensacao_que_nunca_funciona_vai_para_a_dlq(sessoes):
    rel = Relogio()
    part = Participantes(elegibilidade=[httpx.Response(422, json=RN01)], liberar_vaga=[httpx.Response(500)])
    ex = _executor(sessoes, part, rel)

    async def go():
        saga = await _nova(sessoes, rel)
        await ex.avancar(saga.saga_id)
        for _ in range(5):
            rel.avancar(seconds=10)
            await executar_ciclo(ex, sessoes, rel(), 15, 10)
        return await repo.obter(sessoes, saga.saga_id), await _outbox(sessoes)

    final, outbox = _run(go())
    assert final.status == "COMPENSATION_FAILED" and final.next_attempt_at is None
    assert outbox == ["saga.compensacao.falhou"]


# ------------------------------------------------------------------ recuperação e concorrência


def test_saga_interrompida_e_retomada_pela_recuperacao(sessoes):
    """Processo caiu depois do passo 1: a SAGA ficou em SLOT_RESERVED, reivindicada por um prazo que venceu."""
    rel, part = Relogio(), Participantes()
    ex = _executor(sessoes, part, rel)

    async def go():
        saga = await _nova(sessoes, rel)
        t = transicionar(repo.estado_de(saga), PassoConcluido(Passo.STEP1, {"dataHoraInicio": "2026-11-25T14:00:00Z"}), ex.politica)
        saga = await repo.aplicar_transicao(sessoes, saga, t, agora=rel())
        await repo.reivindicar(sessoes, saga.saga_id, rel(), prazo_s=15)  # ... e o processo morreu aqui
        antes = await executar_ciclo(ex, sessoes, rel() + timedelta(seconds=5), 15, 10)
        rel.avancar(seconds=16)
        depois = await executar_ciclo(ex, sessoes, rel(), 15, 10)
        return antes, depois, await repo.obter(sessoes, saga.saga_id)

    antes, depois, final = _run(go())
    assert antes == 0 and depois == 1 and final.status == "CONFIRMED"
    assert ("POST", "/api/v1/slots/slot-1/reservas") not in part.rotas()  # o passo 1 não é repetido


def test_prazo_do_passo3_vencido_compensa_tudo(sessoes):
    rel, part = Relogio(), Participantes()
    ex = _executor(sessoes, part, rel, Politica(aguardar_resposta_passo3=True, timeout_passo3=30))

    async def go():
        saga = await _nova(sessoes, rel)
        await ex.avancar(saga.saga_id)
        rel.avancar(seconds=31)
        await executar_ciclo(ex, sessoes, rel(), 15, 10)
        return saga, await repo.obter(sessoes, saga.saga_id), await _log(sessoes, saga.saga_id), await _outbox(sessoes)

    saga, final, log, outbox = _run(go())
    assert final.status == "COMPENSATED"
    assert ("STEP3", "FORWARD", "TIMEOUT") in log and ("STEP3", "COMPENSATE", "PUBLICADO") in log
    assert "saga.comando.comunicacao.cancelar-lembrete" in outbox
    assert [m for m, _ in part.rotas()].count("DELETE") == 2


def test_dois_executores_na_mesma_saga_chamam_cada_passo_uma_vez(sessoes):
    rel = Relogio()
    lento = Participantes()
    ex = _executor(sessoes, lento, rel)

    async def go():
        saga = await _nova(sessoes, rel)
        await asyncio.gather(ex.avancar(saga.saga_id), ex.avancar(saga.saga_id))
        return await repo.obter(sessoes, saga.saga_id)

    final = _run(go())
    assert final.status == "CONFIRMED"
    assert len(lento.chamadas) == 3  # reservar, elegibilidade, confirmar: nenhuma em dobro


def test_erro_inesperado_no_cliente_vira_falha_tecnica(sessoes):
    rel = Relogio()
    part = Participantes(reservar=[RuntimeError("bug")])

    async def go():
        saga = await _nova(sessoes, rel)
        return await _executor(sessoes, part, rel).avancar(saga.saga_id)

    final = _run(go())
    assert final.status == "STARTED" and final.retry_count == 1 and "erro interno" in final.error_detail


# ------------------------------------------------------------------ disparo pelo POST da API


def test_post_da_api_dispara_a_saga_em_segundo_plano(pg_engine, monkeypatch):
    from orquestrador.main import app

    monkeypatch.setenv("ORQUESTRADOR_POSTGRES_URL", TEST_PG_URL)
    get_settings.cache_clear()
    part = Participantes()
    try:
        with TestClient(app) as client:
            app.state.executor = Executor(
                app.state.session_factory, AgendamentosClient(part.http()), DoadoresClient(part.http()),
                Politica(aguardar_resposta_passo3=False), prazo_reivindicacao=15,
            )
            saga_id = client.post("/api/v1/sagas/agendamento", json={"doadorId": "d1", "slotId": "slot-1"}).json()["sagaId"]
            for _ in range(50):
                corpo = client.get(f"/api/v1/sagas/{saga_id}").json()
                if corpo["finalizada"]:
                    break
                client.portal.call(asyncio.sleep, 0.05)
    finally:
        get_settings.cache_clear()
    assert corpo["status"] == "CONFIRMED"
    assert [p["passo"] for p in corpo["passos"]] == ["STEP1", "STEP2", "STEP3", "STEP4"]
    uuid.UUID(saga_id)


# ------------------------------------------------------------------ laço do worker


def test_laco_da_recuperacao_processa_e_sobrevive_a_banco_fora(sessoes):
    from types import SimpleNamespace

    from orquestrador.services.recuperacao import executar_recuperacao

    part = Participantes(reservar=[httpx.Response(503), httpx.Response(201, json=RESERVA)])
    ex = Executor(sessoes, AgendamentosClient(part.http()), DoadoresClient(part.http()),
                  Politica(aguardar_resposta_passo3=False, backoff_base_ms=10), prazo_reivindicacao=15)
    config = SimpleNamespace(prazo_reivindicacao=15, recuperacao_lote=10, recuperacao_intervalo=0.02)

    async def go():
        saga = await repo.criar(sessoes, doador_id="d1", slot_id="slot-1", agora=datetime.now(UTC), max_retries=5)
        await ex.avancar(saga.saga.saga_id)  # 503 no passo 1: retentativa em ~10 ms
        app = SimpleNamespace(state=SimpleNamespace(settings=config, executor=ex, session_factory=sessoes))
        tarefa = asyncio.create_task(executar_recuperacao(app))
        for _ in range(100):
            await asyncio.sleep(0.02)
            final = await repo.obter(sessoes, saga.saga.saga_id)
            if final.status == "CONFIRMED":
                break
        app.state.session_factory = None  # "banco fora": o laço registra e continua vivo
        await asyncio.sleep(0.1)
        vivo = not tarefa.done()
        tarefa.cancel()
        await asyncio.gather(tarefa, return_exceptions=True)
        return final, vivo

    final, vivo = _run(go())
    assert final.status == "CONFIRMED" and vivo


def test_workers_iniciam_conforme_configuracao():
    from types import SimpleNamespace

    from orquestrador.services.workers import iniciar_workers, parar_workers

    async def go():
        ligado = SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(recuperacao_habilitada=True)))
        desligado = SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(recuperacao_habilitada=False)))
        tarefas = iniciar_workers(ligado)
        nomes = [t.get_name() for t in tarefas]
        await parar_workers(tarefas)
        return nomes, iniciar_workers(desligado)

    nomes, nenhuma = _run(go())
    assert nomes == ["saga-recuperacao"] and nenhuma == []
