import asyncio
import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from comunicacao.config import Settings, get_settings
from comunicacao.models.orm import Lembrete, Notificacao
from comunicacao.services.comandos import CANCELAR, PROGRAMAR, Comando, processar_comando
from comunicacao.services.lembretes import enviar_vencidos
from comunicacao.services.notificacoes import EventoInvalido, montar_notificacao, processar_evento

AGORA = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
S = Settings(postgres_url="postgresql+asyncpg://x:y@h/d", rabbitmq_url="amqp://x:y@h/")


@pytest.fixture
def factory(pg_engine):
    return async_sessionmaker(pg_engine, expire_on_commit=False)


def _programar(factory, ag: str, inicio: datetime, doador="d1"):
    cmd = Comando(PROGRAMAR, "s-" + ag, ag, doador, "slot", inicio.isoformat())
    return asyncio.run(processar_comando(factory, S, cmd, f"m-{ag}", agora=AGORA))


# ---- lembretes D-1 ----

def test_envia_so_lembretes_vencidos_e_nao_cancelados(factory):
    _programar(factory, "a1", AGORA + timedelta(days=1, hours=1))  # vence em 1 h
    _programar(factory, "a2", AGORA + timedelta(days=3))  # ainda não vence
    _programar(factory, "a3", AGORA + timedelta(days=1, minutes=30))
    asyncio.run(processar_comando(factory, S, Comando(CANCELAR, "s-a3", "a3", "d1", None, None), "c-a3", agora=AGORA))

    assert asyncio.run(enviar_vencidos(factory, agora=AGORA + timedelta(hours=2))) == 1
    assert asyncio.run(enviar_vencidos(factory, agora=AGORA + timedelta(hours=2))) == 0  # não reenvia

    async def ler():
        async with factory() as s:
            return {lem.agendamento_id: lem.status for lem in (await s.scalars(select(Lembrete))).all()}

    assert asyncio.run(ler()) == {"a1": "ENVIADO", "a2": "PROGRAMADO", "a3": "CANCELADO"}


def test_replicas_concorrentes_nao_enviam_em_dobro(factory):
    for i in range(20):
        _programar(factory, f"a{i}", AGORA + timedelta(days=1, minutes=1))

    async def go():
        return await asyncio.gather(*[enviar_vencidos(factory, lote=5, agora=AGORA + timedelta(hours=1)) for _ in range(4)])

    enviados = sum(asyncio.run(go()))
    enviados += asyncio.run(enviar_vencidos(factory, lote=50, agora=AGORA + timedelta(hours=1)))

    async def contar():
        async with factory() as s:
            return await s.scalar(select(func.count()).select_from(Notificacao).where(Notificacao.tipo == "LEMBRETE"))

    assert enviados == 20 and asyncio.run(contar()) == 20


# ---- histórico ----

def test_historico_do_doador(factory, monkeypatch):
    from tests.conftest import TEST_PG_URL

    _programar(factory, "a1", AGORA + timedelta(days=5), doador="d1")
    _programar(factory, "a2", AGORA + timedelta(days=6), doador="d1")
    _programar(factory, "a3", AGORA + timedelta(days=6), doador="outro")
    monkeypatch.setenv("COMUNICACAO_POSTGRES_URL", TEST_PG_URL)
    get_settings.cache_clear()
    try:
        from comunicacao.main import app

        with TestClient(app) as client:
            r = client.get("/api/v1/comunicacao/historico/d1?tamanho=1")
            vazio = client.get("/api/v1/comunicacao/historico/ninguem")
            invalido = client.get("/api/v1/comunicacao/historico/d1?tamanho=0")
    finally:
        get_settings.cache_clear()
    corpo = r.json()
    assert r.status_code == 200 and corpo["total"] == 2 and len(corpo["itens"]) == 1
    assert corpo["itens"][0]["agendamentoId"] == "a2" and corpo["itens"][0]["tipo"] == "CONFIRMACAO"
    assert vazio.status_code == 200 and vazio.json()["itens"] == []
    assert invalido.status_code == 400 and invalido.headers["content-type"] == "application/problem+json"


# ---- notificações de eventos de domínio ----

def test_desfecho_da_saga_vira_notificacao(factory):
    corpo = json.dumps({"sagaId": "s1", "agendamentoId": "a1", "doadorId": "d1", "status": "COMPENSATED"}).encode()
    assert asyncio.run(processar_evento(factory, "saga.agendamento.compensado", corpo, "saga-s1-desfecho")) is True
    assert asyncio.run(processar_evento(factory, "saga.agendamento.compensado", corpo, "saga-s1-desfecho")) is False

    async def ler():
        async with factory() as s:
            return (await s.scalars(select(Notificacao))).all()

    [n] = asyncio.run(ler())
    assert (n.tipo, n.doador_id) == ("DESFECHO", "d1") and "Não foi possível" in n.conteudo


def test_campanha_criada_vira_aviso_geral():
    n = montar_notificacao("hemocentros.campanha.criada", json.dumps(
        {"titulo": "Estoque O-", "hemocentro": "Hemominas", "tipo_sanguineo": "O-", "urgencia": "ALTA"}).encode())
    assert n.tipo == "CAMPANHA" and n.doador_id is None and "Estoque O-" in n.conteudo


@pytest.mark.parametrize("rk,corpo", [
    ("saga.agendamento.confirmado", b"{x"),
    ("saga.agendamento.confirmado", b'{"sagaId": "s"}'),
    ("hemocentros.campanha.criada", b"{}"),
    ("outra.coisa", b"{}"),
])
def test_evento_invalido(rk, corpo):
    with pytest.raises(EventoInvalido):
        montar_notificacao(rk, corpo)
