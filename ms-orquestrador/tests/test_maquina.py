"""Máquina de estados da SAGA (funções puras): uma verificação por transição de ADR-006 §5.3."""

import pytest

from orquestrador.saga.estados import (
    STATUS_TERMINAIS,
    AgendarRetentativa,
    AguardarResposta,
    CompensacaoConcluida,
    CompensarPasso,
    Direcao,
    EstadoSaga,
    ExecutarPasso,
    FalhaTecnica,
    Passo,
    PassoConcluido,
    PassoRecusado,
    Politica,
    PublicarMensagem,
    RespostaComunicacao,
    StatusSaga,
    TimeoutPasso3,
    TipoMensagem,
)
from orquestrador.saga.maquina import backoff_ms, inicial, proxima_acao, transicionar

P = Politica()  # padrão: 5 retentativas, base 500 ms, aguarda resposta do passo 3 por 30 s
SEM_COMUNICACAO = Politica(aguardar_resposta_passo3=False)
S, PS = StatusSaga, Passo


def _estado(status, passo, retry=0):
    return EstadoSaga(status, passo, retry)


def _executar(eventos, politica=P, estado=None):
    """Aplica uma sequência de eventos e devolve (estado final, todas as transições)."""
    estado = estado or inicial()
    transicoes = []
    for ev in eventos:
        t = transicionar(estado, ev, politica)
        transicoes.append(t)
        estado = t.estado
    return estado, transicoes


def _resultados(transicoes):
    return [(r.passo, r.direcao, r.resultado) for t in transicoes for r in t.registros]


# ------------------------------------------------------------------ caminho feliz


def test_caminho_feliz_aguardando_resposta_da_comunicacao():
    final, ts = _executar([
        PassoConcluido(PS.STEP1, {"dataHoraInicio": "2026-11-25T14:00:00Z"}),
        PassoConcluido(PS.STEP2),
        RespostaComunicacao(ok=True),
        PassoConcluido(PS.STEP4),
    ])
    assert final == EstadoSaga(S.CONFIRMED, PS.STEP4)
    assert [t.estado.status for t in ts] == [S.SLOT_RESERVED, S.AWAITING_COMUNICACAO, S.CONFIRMING, S.CONFIRMED]
    assert ts[0].acoes == (ExecutarPasso(PS.STEP2),)
    assert ts[0].dados == {"dataHoraInicio": "2026-11-25T14:00:00Z"}
    assert ts[1].acoes == (PublicarMensagem(TipoMensagem.PROGRAMAR_LEMBRETE), AguardarResposta(30.0))
    assert ts[2].acoes == (ExecutarPasso(PS.STEP4),)
    assert ts[3].acoes == (PublicarMensagem(TipoMensagem.AGENDAMENTO_CONFIRMADO),)
    assert ts[3].terminal
    assert _resultados(ts) == [
        (PS.STEP1, Direcao.FORWARD, "OK"), (PS.STEP2, Direcao.FORWARD, "OK"), (PS.STEP3, Direcao.FORWARD, "PUBLICADO"),
        (PS.STEP3, Direcao.FORWARD, "OK"), (PS.STEP4, Direcao.FORWARD, "OK"),
    ]


def test_caminho_feliz_sem_aguardar_comunicacao_conclui_passo3_ao_gravar_no_outbox():
    final, ts = _executar([PassoConcluido(PS.STEP1), PassoConcluido(PS.STEP2), PassoConcluido(PS.STEP4)], SEM_COMUNICACAO)
    assert final.status == S.CONFIRMED
    assert ts[1].estado == EstadoSaga(S.CONFIRMING, PS.STEP4)
    assert ts[1].acoes == (PublicarMensagem(TipoMensagem.PROGRAMAR_LEMBRETE), ExecutarPasso(PS.STEP4))


# ------------------------------------------------------------------ recusas de negócio


def test_recusa_no_passo1_rejeita_sem_compensar():
    problema = {"status": 409, "type": "urn:startech:error:slot-esgotado"}
    t = transicionar(inicial(), PassoRecusado(PS.STEP1, problema), P)
    assert t.estado.status == S.REJECTED and t.terminal
    assert t.acoes == () and t.recusa == problema


def test_recusa_rn01_no_passo2_libera_a_vaga_e_compensa():
    problema = {"status": 422, "type": "urn:startech:error:intervalo-minimo"}
    final, ts = _executar([
        PassoConcluido(PS.STEP1), PassoRecusado(PS.STEP2, problema), CompensacaoConcluida(PS.STEP1),
    ])
    assert ts[1].estado == EstadoSaga(S.COMPENSATING, PS.STEP1)  # o passo 2 recusado não teve efeito
    assert ts[1].acoes == (CompensarPasso(PS.STEP1),) and ts[1].recusa == problema
    assert final.status == S.COMPENSATED
    assert ts[2].acoes == (PublicarMensagem(TipoMensagem.AGENDAMENTO_COMPENSADO),)


def test_comunicacao_falhou_cancela_lembrete_e_desfaz_passos_2_e_1():
    final, ts = _executar([
        PassoConcluido(PS.STEP1), PassoConcluido(PS.STEP2), RespostaComunicacao(ok=False, motivo="e-mail inválido"),
        CompensacaoConcluida(PS.STEP2), CompensacaoConcluida(PS.STEP1),
    ])
    assert ts[2].estado == EstadoSaga(S.COMPENSATING, PS.STEP2)
    assert ts[2].acoes == (PublicarMensagem(TipoMensagem.CANCELAR_LEMBRETE), CompensarPasso(PS.STEP2))
    assert ts[3].acoes == (CompensarPasso(PS.STEP1),)
    assert final.status == S.COMPENSATED
    assert [r for r in _resultados(ts) if r[1] == Direcao.COMPENSATE] == [
        (PS.STEP3, Direcao.COMPENSATE, "PUBLICADO"), (PS.STEP2, Direcao.COMPENSATE, "OK"), (PS.STEP1, Direcao.COMPENSATE, "OK"),
    ]


def test_timeout_do_passo3_compensa():
    _, ts = _executar([PassoConcluido(PS.STEP1), PassoConcluido(PS.STEP2), TimeoutPasso3()])
    assert ts[2].estado == EstadoSaga(S.COMPENSATING, PS.STEP2)
    assert PublicarMensagem(TipoMensagem.CANCELAR_LEMBRETE) in ts[2].acoes
    assert (PS.STEP3, Direcao.FORWARD, "TIMEOUT") in _resultados(ts)


def test_recusa_no_passo4_desfaz_3_2_e_1():
    t = transicionar(_estado(S.CONFIRMING, PS.STEP4), PassoRecusado(PS.STEP4, {"status": 409}), P)
    assert t.estado == EstadoSaga(S.COMPENSATING, PS.STEP2)
    assert t.acoes == (PublicarMensagem(TipoMensagem.CANCELAR_LEMBRETE), CompensarPasso(PS.STEP2))


# ------------------------------------------------------------------ falhas técnicas e retentativas


def test_falha_tecnica_retenta_com_backoff_exponencial():
    estado = inicial()
    esperas = []
    for _ in range(5):
        t = transicionar(estado, FalhaTecnica(PS.STEP1, "timeout"), P)
        assert t.estado.status == S.STARTED
        (acao,) = t.acoes
        assert isinstance(acao, AgendarRetentativa)
        esperas.append(acao.espera_ms)
        estado = t.estado
    assert esperas == [500, 1000, 2000, 4000, 8000]  # T = 2^tentativa * 500 ms (ADR-002 §5.3)
    assert estado.retry_count == 5


def test_sucesso_depois_de_falhas_zera_as_tentativas():
    final, _ = _executar([FalhaTecnica(PS.STEP1), FalhaTecnica(PS.STEP1), PassoConcluido(PS.STEP1)])
    assert final == EstadoSaga(S.SLOT_RESERVED, PS.STEP2, 0)


def test_falha_tecnica_esgotada_no_passo1_desfaz_o_proprio_passo1():
    # Resultado incerto (o participante pode ter reservado a vaga): a compensação idempotente resolve.
    t = transicionar(_estado(S.STARTED, PS.STEP1, retry=5), FalhaTecnica(PS.STEP1, "timeout"), P)
    assert t.estado == EstadoSaga(S.COMPENSATING, PS.STEP1)
    assert t.acoes == (CompensarPasso(PS.STEP1),)
    assert t.registros[0].resultado == "DESISTIU"


def test_falha_tecnica_esgotada_no_passo2_desfaz_2_e_1():
    t = transicionar(_estado(S.SLOT_RESERVED, PS.STEP2, retry=5), FalhaTecnica(PS.STEP2), P)
    assert t.estado == EstadoSaga(S.COMPENSATING, PS.STEP2)


def test_falha_tecnica_esgotada_no_passo4_desfaz_3_2_e_1():
    t = transicionar(_estado(S.CONFIRMING, PS.STEP4, retry=5), FalhaTecnica(PS.STEP4), P)
    assert t.estado == EstadoSaga(S.COMPENSATING, PS.STEP2)
    assert PublicarMensagem(TipoMensagem.CANCELAR_LEMBRETE) in t.acoes


def test_compensacao_com_falha_retenta_e_depois_vai_para_a_dlq():
    estado = _estado(S.COMPENSATING, PS.STEP1)
    for n in range(5):
        t = transicionar(estado, FalhaTecnica(PS.STEP1, "503"), P)
        assert t.estado == EstadoSaga(S.COMPENSATING, PS.STEP1, n + 1)
        assert t.acoes == (AgendarRetentativa(backoff_ms(n, P)),)
        estado = t.estado
    t = transicionar(estado, FalhaTecnica(PS.STEP1, "503"), P)
    assert t.estado.status == S.COMPENSATION_FAILED and t.terminal
    assert t.acoes == (PublicarMensagem(TipoMensagem.COMPENSACAO_FALHOU),)


def test_recusa_inesperada_na_compensacao_conta_como_falha():
    t = transicionar(_estado(S.COMPENSATING, PS.STEP2), PassoRecusado(PS.STEP2, {"status": 409}), P)
    assert t.estado == EstadoSaga(S.COMPENSATING, PS.STEP2, 1)
    assert isinstance(t.acoes[0], AgendarRetentativa)


def test_tentativas_da_compensacao_recomecam_a_cada_passo():
    t = transicionar(_estado(S.COMPENSATING, PS.STEP2, retry=3), CompensacaoConcluida(PS.STEP2), P)
    assert t.estado == EstadoSaga(S.COMPENSATING, PS.STEP1, 0)


# ------------------------------------------------------------------ idempotência e eventos fora de ordem


@pytest.mark.parametrize("final", sorted(STATUS_TERMINAIS))
def test_eventos_apos_status_final_sao_ignorados(final):
    estado = _estado(final, PS.STEP1)
    for ev in (PassoConcluido(PS.STEP1), RespostaComunicacao(ok=True), TimeoutPasso3(), CompensacaoConcluida(PS.STEP1)):
        t = transicionar(estado, ev, P)
        assert t.ignorado and t.estado == estado and t.acoes == ()


@pytest.mark.parametrize("estado,evento", [
    (EstadoSaga(S.STARTED, PS.STEP1), PassoConcluido(PS.STEP2)),  # passo errado
    (EstadoSaga(S.STARTED, PS.STEP1), RespostaComunicacao(ok=True)),
    (EstadoSaga(S.STARTED, PS.STEP1), TimeoutPasso3()),
    (EstadoSaga(S.AWAITING_COMUNICACAO, PS.STEP3), PassoConcluido(PS.STEP2)),  # resposta HTTP atrasada
    (EstadoSaga(S.CONFIRMING, PS.STEP4), RespostaComunicacao(ok=False)),  # resposta duplicada do passo 3
    (EstadoSaga(S.COMPENSATING, PS.STEP1), CompensacaoConcluida(PS.STEP2)),  # compensação já registrada
    (EstadoSaga(S.COMPENSATING, PS.STEP1), PassoConcluido(PS.STEP1)),
])
def test_eventos_fora_de_ordem_ou_duplicados_sao_ignorados(estado, evento):
    t = transicionar(estado, evento, P)
    assert t.ignorado and t.estado == estado and t.acoes == () and t.registros == ()


# ------------------------------------------------------------------ próxima ação (executor e recuperação)


@pytest.mark.parametrize("estado,esperado", [
    (EstadoSaga(S.STARTED, PS.STEP1), ExecutarPasso(PS.STEP1)),
    (EstadoSaga(S.SLOT_RESERVED, PS.STEP2), ExecutarPasso(PS.STEP2)),
    (EstadoSaga(S.CONFIRMING, PS.STEP4), ExecutarPasso(PS.STEP4)),
    (EstadoSaga(S.COMPENSATING, PS.STEP2), CompensarPasso(PS.STEP2)),
    (EstadoSaga(S.COMPENSATING, PS.STEP1), CompensarPasso(PS.STEP1)),
    (EstadoSaga(S.AWAITING_COMUNICACAO, PS.STEP3), None),
    (EstadoSaga(S.CONFIRMED, PS.STEP4), None),
    (EstadoSaga(S.COMPENSATION_FAILED, PS.STEP1), None),
])
def test_proxima_acao(estado, esperado):
    assert proxima_acao(estado) == esperado


def test_compensacao_nunca_pede_http_para_o_passo3():
    """O passo 3 é desfeito pelo Outbox; nenhum estado alcançável fica em COMPENSATING no passo 3 ou 4."""
    alcancados = set()
    for ev in (PassoRecusado(PS.STEP2), RespostaComunicacao(ok=False), TimeoutPasso3()):
        for estado in (EstadoSaga(S.SLOT_RESERVED, PS.STEP2), EstadoSaga(S.AWAITING_COMUNICACAO, PS.STEP3)):
            t = transicionar(estado, ev, P)
            if t.estado.status == S.COMPENSATING:
                alcancados.add(t.estado.passo)
    assert alcancados <= {PS.STEP1, PS.STEP2}
