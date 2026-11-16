"""Clientes HTTP dos participantes: caminhos, cabeçalhos, corpo e classificação das respostas."""

import asyncio
import json
import uuid

import httpx
import pytest

from orquestrador.clients.agendamentos import AgendamentosClient
from orquestrador.clients.base import Falha, Recusa, Sucesso, chave
from orquestrador.clients.doadores import DoadoresClient

SAGA = uuid.UUID("11111111-1111-1111-1111-111111111111")
RESERVA = {"agendamentoId": "ag-1", "slotId": "slot-1", "dataHoraInicio": "2026-11-25T14:00:00Z",
           "dataHoraFim": "2026-11-25T14:20:00Z", "status": "CRIADO_PROVISORIO"}


class Participante:
    """Participante simulado: registra as requisições e responde com o handler dado."""

    def __init__(self, handler):
        self.requisicoes: list[httpx.Request] = []
        self._handler = handler

    def http(self) -> httpx.AsyncClient:
        def _registrar(req: httpx.Request):
            self.requisicoes.append(req)
            return self._handler(req)
        return httpx.AsyncClient(transport=httpx.MockTransport(_registrar), base_url="http://participante")


def _resp(status, corpo=None, problem=False):
    def handler(_req):
        if corpo is None:
            return httpx.Response(status)
        headers = {"content-type": "application/problem+json"} if problem else None
        return httpx.Response(status, json=corpo, headers=headers)
    return handler


def _erro(exc):
    def handler(req):
        raise exc("falhou", request=req)
    return handler


def _rodar(coro):
    return asyncio.run(coro)


# ------------------------------------------------------------------ requisições montadas conforme o contrato


def test_reservar_vaga_monta_a_requisicao_do_passo1():
    p = Participante(_resp(201, RESERVA))
    r = _rodar(AgendamentosClient(p.http()).reservar_vaga(SAGA, "slot-1", "ag-1", "doador-1", "req-abc"))
    assert r == Sucesso(RESERVA)
    (req,) = p.requisicoes
    assert (req.method, req.url.path) == ("POST", "/api/v1/slots/slot-1/reservas")
    assert json.loads(req.content) == {"agendamentoId": "ag-1", "doadorId": "doador-1"}
    assert req.headers["Idempotency-Key"] == f"saga-{SAGA}-step1"
    assert req.headers["X-Request-Id"] == "req-abc"


def test_liberar_vaga_monta_a_compensacao_do_passo1():
    p = Participante(_resp(204))
    r = _rodar(AgendamentosClient(p.http()).liberar_vaga(SAGA, "slot-1", "ag-1"))
    assert r == Sucesso({})
    (req,) = p.requisicoes
    assert (req.method, req.url.path) == ("DELETE", "/api/v1/slots/slot-1/reservas/ag-1")
    assert req.headers["Idempotency-Key"] == f"saga-{SAGA}-step1-comp"
    assert "X-Request-Id" not in req.headers  # sem correlation id, nada é inventado


def test_confirmar_monta_o_passo4():
    p = Participante(_resp(200, {"id": "ag-1", "status": "CONFIRMADO"}))
    r = _rodar(AgendamentosClient(p.http()).confirmar(SAGA, "ag-1"))
    assert isinstance(r, Sucesso)
    (req,) = p.requisicoes
    assert (req.method, req.url.path) == ("POST", "/api/v1/agendamentos/ag-1/confirmacao")
    assert req.headers["Idempotency-Key"] == f"saga-{SAGA}-step4"


def test_reservar_elegibilidade_monta_o_passo2():
    p = Participante(_resp(200, {"doadorId": "doador-1", "travado": True}))
    r = _rodar(DoadoresClient(p.http()).reservar_elegibilidade(SAGA, "doador-1", "ag-1", "2026-11-25T14:00:00Z"))
    assert isinstance(r, Sucesso)
    (req,) = p.requisicoes
    assert (req.method, req.url.path) == ("POST", "/api/v1/doadores/doador-1/reservas-elegibilidade")
    assert json.loads(req.content) == {"agendamentoId": "ag-1", "dataSlot": "2026-11-25T14:00:00Z"}
    assert req.headers["Idempotency-Key"] == f"saga-{SAGA}-step2"


def test_liberar_elegibilidade_monta_a_compensacao_do_passo2():
    p = Participante(_resp(204))
    _rodar(DoadoresClient(p.http()).liberar_elegibilidade(SAGA, "doador-1", "ag-1"))
    (req,) = p.requisicoes
    assert (req.method, req.url.path) == ("DELETE", "/api/v1/doadores/doador-1/reservas-elegibilidade/ag-1")
    assert req.headers["Idempotency-Key"] == f"saga-{SAGA}-step2-comp"


# ------------------------------------------------------------------ classificação das respostas


def test_recusa_rn01_preserva_o_problem_json():
    problema = {"type": "urn:startech:error:intervalo-minimo", "title": "Doador inapto", "status": 422,
                "detail": "Doação há 10 dias; mínimo de 60 dias."}
    p = Participante(_resp(422, problema, problem=True))
    r = _rodar(DoadoresClient(p.http()).reservar_elegibilidade(SAGA, "d", "a", "2026-11-25"))
    assert r == Recusa(problema)


@pytest.mark.parametrize("status", [404, 409, 422])
def test_recusas_de_negocio_na_acao_positiva(status):
    p = Participante(_resp(status, {"title": "recusado"}))
    r = _rodar(AgendamentosClient(p.http()).confirmar(SAGA, "ag-1"))
    assert r == Recusa({"status": status, "title": "recusado"})


def test_recusa_sem_corpo_ganha_problema_minimo():
    p = Participante(_resp(409))
    r = _rodar(AgendamentosClient(p.http()).confirmar(SAGA, "ag-1"))
    assert isinstance(r, Recusa) and r.problema["status"] == 409 and r.problema["title"]


@pytest.mark.parametrize("status", [500, 502, 503])
def test_5xx_e_falha_tecnica(status):
    p = Participante(_resp(status))
    r = _rodar(AgendamentosClient(p.http()).confirmar(SAGA, "ag-1"))
    assert r == Falha(f"ms-agendamentos: HTTP {status}")


def test_400_e_falha_de_contrato_registrada_em_log(caplog):
    p = Participante(_resp(400, {"title": "payload inválido"}))
    r = _rodar(DoadoresClient(p.http()).reservar_elegibilidade(SAGA, "d", "a", "x"))
    assert r == Falha("ms-doadores: HTTP 400")
    assert "divergência de contrato" in caplog.text


@pytest.mark.parametrize("exc,motivo", [
    (httpx.ConnectTimeout, "ms-agendamentos: timeout"),
    (httpx.ReadTimeout, "ms-agendamentos: timeout"),
    (httpx.ConnectError, "ms-agendamentos: indisponível (ConnectError)"),
])
def test_rede_e_falha_tecnica(exc, motivo):
    p = Participante(_erro(exc))
    assert _rodar(AgendamentosClient(p.http()).confirmar(SAGA, "ag-1")) == Falha(motivo)


def test_404_na_compensacao_e_sucesso_idempotente():
    p = Participante(_resp(404, {"title": "reserva não encontrada"}))
    assert _rodar(AgendamentosClient(p.http()).liberar_vaga(SAGA, "s", "a")) == Sucesso()
    assert _rodar(DoadoresClient(p.http()).liberar_elegibilidade(SAGA, "d", "a")) == Sucesso()


def test_409_na_compensacao_e_falha_nao_recusa():
    p = Participante(_resp(409))
    assert isinstance(_rodar(AgendamentosClient(p.http()).liberar_vaga(SAGA, "s", "a")), Falha)


def test_reserva_sem_data_do_slot_e_falha():
    # Sem dataHoraInicio a SAGA não consegue montar os passos 2 e 3: trata como falha (contratos §2).
    p = Participante(_resp(201, {"agendamentoId": "ag-1"}))
    r = _rodar(AgendamentosClient(p.http()).reservar_vaga(SAGA, "s", "ag-1", "d"))
    assert r == Falha("ms-agendamentos: resposta da reserva sem dataHoraInicio")


def test_sucesso_com_corpo_invalido_vira_dados_vazios():
    p = Participante(lambda _r: httpx.Response(200, content=b"ok"))
    assert _rodar(AgendamentosClient(p.http()).confirmar(SAGA, "ag-1")) == Sucesso({})


def test_chave_de_idempotencia():
    assert chave("s1", 2) == "saga-s1-step2"
    assert chave("s1", 1, compensacao=True) == "saga-s1-step1-comp"
