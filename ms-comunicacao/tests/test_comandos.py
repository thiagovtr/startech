import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from comunicacao.config import Settings
from comunicacao.models.orm import Lembrete, MensagemRejeitada, Notificacao, OutboxEvent
from comunicacao.services.comandos import (
    CANCELAR,
    PROGRAMAR,
    Comando,
    ComandoIlegivel,
    ler_comando,
    processar_comando,
    tratar_mensagem,
)

AGORA = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


def _settings(**extra) -> Settings:
    return Settings(postgres_url="postgresql+asyncpg://x:y@h/d", rabbitmq_url="amqp://x:y@h/", **extra)


def _cmd(tipo=PROGRAMAR, inicio: datetime | None = AGORA + timedelta(days=5), doador="d1", ag="ag-1") -> Comando:
    return Comando(tipo=tipo, saga_id="s-" + ag, agendamento_id=ag, doador_id=doador, slot_id="slot-1",
                   data_hora_inicio=inicio.isoformat().replace("+00:00", "Z") if inicio else None)


# ---- leitura do comando (sem banco) ----

def test_ler_comando_do_contrato():
    corpo = json.dumps({"tipo": PROGRAMAR, "sagaId": "s1", "agendamentoId": "a1", "doadorId": "d1",
                        "slotId": "x", "dataHoraInicio": "2026-11-25T14:00:00Z", "emitidoEm": "..."}).encode()
    cmd = ler_comando(corpo, "saga.comando.comunicacao.programar-lembrete", _settings())
    assert (cmd.tipo, cmd.saga_id, cmd.agendamento_id, cmd.data_hora_inicio) == (PROGRAMAR, "s1", "a1", "2026-11-25T14:00:00Z")


def test_tipo_ausente_usa_a_routing_key():
    corpo = json.dumps({"sagaId": "s1", "agendamentoId": "a1"}).encode()
    assert ler_comando(corpo, "saga.comando.comunicacao.cancelar-lembrete", _settings()).tipo == CANCELAR


@pytest.mark.parametrize("corpo", [b"{quebrado", b"[1]", b'{"tipo": "Outro", "sagaId": "s", "agendamentoId": "a"}',
                                   b'{"tipo": "CancelarLembreteAgendado", "agendamentoId": "a"}',
                                   b'{"tipo": "CancelarLembreteAgendado", "sagaId": "s"}'])
def test_comando_ilegivel(corpo):
    with pytest.raises(ComandoIlegivel):
        ler_comando(corpo, None, _settings())


# ---- processamento (PostgreSQL real) ----

@pytest.fixture
def factory(pg_engine):
    return async_sessionmaker(pg_engine, expire_on_commit=False)


async def _contar(factory, modelo, *filtros) -> int:
    async with factory() as s:
        return await s.scalar(select(func.count()).select_from(modelo).where(*filtros)) or 0


async def _respostas(factory) -> list[OutboxEvent]:
    async with factory() as s:
        return list((await s.scalars(select(OutboxEvent).order_by(OutboxEvent.created_at))).all())


def test_programar_grava_lembrete_d1_confirmacao_e_resposta(factory):
    r = asyncio.run(processar_comando(factory, _settings(), _cmd(), "m1", agora=AGORA))
    assert r.acao == "PROGRAMADO"

    async def ler():
        async with factory() as s:
            return await s.scalar(select(Lembrete)), await _respostas(factory)

    lembrete, respostas = asyncio.run(ler())
    assert lembrete.status == "PROGRAMADO" and lembrete.programado_para == AGORA + timedelta(days=4)
    assert asyncio.run(_contar(factory, Notificacao, Notificacao.tipo == "CONFIRMACAO")) == 1
    [resp] = respostas
    assert resp.routing_key == "comunicacao.lembrete.programado"
    assert resp.message_id == "saga-s-ag-1-step3-resposta"
    assert resp.payload["resultado"] == "PROGRAMADO" and resp.payload["agendamentoId"] == "ag-1"


def test_comando_duplicado_nao_repete_efeitos(factory):
    for _ in range(3):
        asyncio.run(processar_comando(factory, _settings(), _cmd(), "m1", agora=AGORA))
    assert asyncio.run(_contar(factory, Lembrete)) == 1
    assert asyncio.run(_contar(factory, Notificacao)) == 1
    assert len(asyncio.run(_respostas(factory))) == 1


def test_lembrete_d1_ja_vencido_e_programado_para_agora(factory):
    asyncio.run(processar_comando(factory, _settings(), _cmd(inicio=AGORA + timedelta(hours=3)), "m1", agora=AGORA))

    async def ler():
        async with factory() as s:
            return await s.scalar(select(Lembrete.programado_para))

    assert asyncio.run(ler()) == AGORA


@pytest.mark.parametrize("cmd,motivo", [
    (_cmd(inicio=None), "dataHoraInicio ausente"),
    (_cmd(inicio=AGORA - timedelta(minutes=1)), "já passou"),
    (_cmd(doador="d-falha"), "Falha simulada"),
])
def test_programacao_invalida_responde_falhou(factory, cmd, motivo):
    r = asyncio.run(processar_comando(factory, _settings(simular_falha_doadores="d-falha"), cmd, "m1", agora=AGORA))
    assert r.acao == "FALHOU" and motivo in (r.motivo or "")
    [resp] = asyncio.run(_respostas(factory))
    assert resp.routing_key == "comunicacao.lembrete.falhou" and resp.payload["resultado"] == "FALHOU"
    assert motivo in resp.payload["motivo"]
    assert asyncio.run(_contar(factory, Lembrete)) == 0


def test_comando_expirado_responde_falhou_sem_notificar(factory):
    cmd = Comando(PROGRAMAR, "s1", "ag-1", "d1", None, (AGORA + timedelta(days=5)).isoformat(),
                  emitido_em=(AGORA - timedelta(seconds=45)).isoformat())
    r = asyncio.run(processar_comando(factory, _settings(), cmd, "m1", agora=AGORA))
    assert r.acao == "FALHOU" and "expirado" in (r.motivo or "")
    assert asyncio.run(_contar(factory, Notificacao)) == 0 and asyncio.run(_contar(factory, Lembrete)) == 0


def test_comando_recente_e_programado(factory):
    cmd = Comando(PROGRAMAR, "s1", "ag-1", "d1", None, (AGORA + timedelta(days=5)).isoformat(),
                  emitido_em=(AGORA - timedelta(seconds=5)).isoformat())
    assert asyncio.run(processar_comando(factory, _settings(), cmd, "m1", agora=AGORA)).acao == "PROGRAMADO"


def test_cancelar_lembrete_programado(factory):
    asyncio.run(processar_comando(factory, _settings(), _cmd(), "m1", agora=AGORA))
    r = asyncio.run(processar_comando(factory, _settings(), _cmd(tipo=CANCELAR), "m2", agora=AGORA))
    assert r.acao == "CANCELADO"
    assert asyncio.run(_contar(factory, Lembrete, Lembrete.status == "CANCELADO")) == 1
    assert asyncio.run(_contar(factory, Notificacao, Notificacao.tipo == "CANCELAMENTO")) == 1
    assert len(asyncio.run(_respostas(factory))) == 1  # a compensação não tem resposta


def test_cancelar_antes_de_programar_impede_reativacao(factory):
    asyncio.run(processar_comando(factory, _settings(), _cmd(tipo=CANCELAR), "m2", agora=AGORA))
    r = asyncio.run(processar_comando(factory, _settings(), _cmd(), "m1", agora=AGORA))
    assert r.acao == "FALHOU"
    assert asyncio.run(_contar(factory, Lembrete, Lembrete.status == "CANCELADO")) == 1
    assert asyncio.run(_contar(factory, Notificacao)) == 0


def test_cancelar_duas_vezes_e_idempotente(factory):
    asyncio.run(processar_comando(factory, _settings(), _cmd(), "m1", agora=AGORA))
    asyncio.run(processar_comando(factory, _settings(), _cmd(tipo=CANCELAR), "m2", agora=AGORA))
    r = asyncio.run(processar_comando(factory, _settings(), _cmd(tipo=CANCELAR), "m3", agora=AGORA))
    assert r.acao == "CANCELADO" and r.motivo == "já estava cancelado"
    assert asyncio.run(_contar(factory, Notificacao, Notificacao.tipo == "CANCELAMENTO")) == 1


# ---- callback do consumidor (ack/nack/rejeitadas) ----

class _Msg:
    def __init__(self, corpo: bytes, message_id: str | None = None, routing_key: str | None = None):
        self.body, self.message_id, self.routing_key, self.correlation_id = corpo, message_id, routing_key, "rid-1"
        self.acks = self.nacks = 0

    async def ack(self):
        self.acks += 1

    async def nack(self, requeue: bool = True):
        self.nacks += 1


def test_mensagem_ilegivel_vai_para_rejeitadas_com_ack(factory):
    msg = _Msg(b"{quebrado", message_id=str(uuid.uuid4()))
    asyncio.run(tratar_mensagem(msg, factory, _settings()))
    assert (msg.acks, msg.nacks) == (1, 0)
    assert asyncio.run(_contar(factory, MensagemRejeitada)) == 1


def test_resposta_carrega_o_correlation_id_da_mensagem(factory):
    inicio = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    corpo = json.dumps({"tipo": PROGRAMAR, "sagaId": "s9", "agendamentoId": "a9", "doadorId": "d9",
                        "dataHoraInicio": inicio}).encode()
    msg = _Msg(corpo, message_id="saga-s9-step3")
    asyncio.run(tratar_mensagem(msg, factory, _settings()))
    assert msg.acks == 1
    [resp] = asyncio.run(_respostas(factory))
    assert resp.correlation_id == "rid-1"


def test_banco_fora_devolve_a_mensagem_a_fila():
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine("postgresql+asyncpg://u:p@127.0.0.1:1/x", connect_args={"timeout": 0.5})
    msg = _Msg(json.dumps({"tipo": CANCELAR, "sagaId": "s", "agendamentoId": "a"}).encode(), message_id="m")
    asyncio.run(tratar_mensagem(msg, async_sessionmaker(engine), _settings(consumidor_espera_erro=0)))
    assert (msg.acks, msg.nacks) == (0, 1)
