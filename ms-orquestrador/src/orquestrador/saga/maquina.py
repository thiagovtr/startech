"""Máquina de estados da SAGA de agendamento (ADR-006 §5.3). Funções puras, sem IO.

Fluxo:  STARTED -1-> SLOT_RESERVED -2-> AWAITING_COMUNICACAO -3-> CONFIRMING -4-> CONFIRMED
        (com `aguardar_resposta_passo3=False`, o passo 2 vai direto para CONFIRMING)

- O executor pergunta `proxima_acao(estado)`, grava a intenção, executa a chamada e devolve o resultado
  como evento em `transicionar(estado, evento, politica)`, que diz o novo estado e o que fazer em seguida.
- Recusa de negócio não é retentada. Falha técnica é retentada com backoff até `max_retries`.
- Compensação: em COMPENSATING, `passo` é o próximo a desfazer, descendo até o passo 1. Como as
  compensações são idempotentes, um passo com resultado incerto (falha técnica esgotada) também é desfeito.
- O passo 3 é desfeito publicando o cancelamento no Outbox na própria transição (sem chamada HTTP).
- O passo 4 não tem compensação: falhar nele desfaz os passos 3, 2 e 1.
"""

from orquestrador.saga.estados import (
    STATUS_TERMINAIS,
    Acao,
    AgendarRetentativa,
    AguardarResposta,
    CompensacaoConcluida,
    CompensarPasso,
    Direcao,
    EstadoSaga,
    Evento,
    ExecutarPasso,
    FalhaTecnica,
    Passo,
    PassoConcluido,
    PassoRecusado,
    Politica,
    PublicarMensagem,
    Registro,
    RespostaComunicacao,
    StatusSaga,
    TimeoutPasso3,
    TipoMensagem,
    Transicao,
)

# Status em que o passo indicado está pendente (ação positiva)
_STATUS_DO_PASSO = {
    Passo.STEP1: StatusSaga.STARTED,
    Passo.STEP2: StatusSaga.SLOT_RESERVED,
    Passo.STEP4: StatusSaga.CONFIRMING,
}
_PASSO_ANTERIOR = {Passo.STEP4: Passo.STEP3, Passo.STEP3: Passo.STEP2, Passo.STEP2: Passo.STEP1}


def inicial() -> EstadoSaga:
    return EstadoSaga(StatusSaga.STARTED, Passo.STEP1)


def proxima_acao(estado: EstadoSaga) -> ExecutarPasso | CompensarPasso | None:
    """Chamada externa pendente no estado atual (None: aguardando resposta ou SAGA finalizada)."""
    if estado.status in STATUS_TERMINAIS or estado.status == StatusSaga.AWAITING_COMUNICACAO:
        return None
    if estado.status == StatusSaga.COMPENSATING:
        return CompensarPasso(estado.passo)
    return ExecutarPasso(estado.passo)


def backoff_ms(tentativa: int, politica: Politica) -> int:
    """Espera antes da tentativa seguinte: 2^tentativa * base (tentativa começa em 0)."""
    return (2**tentativa) * politica.backoff_base_ms


def transicionar(estado: EstadoSaga, evento: Evento, politica: Politica) -> Transicao:
    if estado.status in STATUS_TERMINAIS:
        return _ignorar(estado)
    if estado.status == StatusSaga.COMPENSATING:
        return _na_compensacao(estado, evento, politica)
    if estado.status == StatusSaga.AWAITING_COMUNICACAO:
        return _aguardando_comunicacao(estado, evento)
    return _no_passo(estado, evento, politica)


# ---------------------------------------------------------------- ações positivas


def _no_passo(estado: EstadoSaga, evento: Evento, politica: Politica) -> Transicao:
    passo = estado.passo
    if not isinstance(evento, PassoConcluido | PassoRecusado | FalhaTecnica) or evento.passo != passo:
        return _ignorar(estado)

    if isinstance(evento, PassoConcluido):
        ok = Registro(passo, Direcao.FORWARD, "OK", evento.dados or None)
        dados = evento.dados or None
        if passo == Passo.STEP1:
            return Transicao(
                EstadoSaga(StatusSaga.SLOT_RESERVED, Passo.STEP2), (ExecutarPasso(Passo.STEP2),), (ok,), dados=dados
            )
        if passo == Passo.STEP2:
            return _enviar_passo3(ok, politica, dados)
        return Transicao(  # passo 4
            EstadoSaga(StatusSaga.CONFIRMED, Passo.STEP4),
            (PublicarMensagem(TipoMensagem.AGENDAMENTO_CONFIRMADO),), (ok,), dados=dados,
        )

    if isinstance(evento, PassoRecusado):
        recusado = Registro(passo, Direcao.FORWARD, "RECUSADO", evento.problema or None)
        if passo == Passo.STEP1:  # nada foi feito ainda
            return Transicao(EstadoSaga(StatusSaga.REJECTED, passo), (), (recusado,), recusa=evento.problema)
        # A ação recusada não teve efeito: desfaz a partir do passo anterior.
        return _compensar_a_partir(_PASSO_ANTERIOR[passo], (recusado,), recusa=evento.problema)

    # Falha técnica: tenta de novo; esgotadas as tentativas, desfaz inclusive este passo (resultado incerto).
    tentativa = estado.retry_count
    if tentativa < politica.max_retries:
        falha = Registro(passo, Direcao.FORWARD, "FALHA", {"motivo": evento.motivo, "tentativa": tentativa + 1})
        return Transicao(
            EstadoSaga(estado.status, passo, tentativa + 1),
            (AgendarRetentativa(backoff_ms(tentativa, politica)),), (falha,),
        )
    desistiu = Registro(passo, Direcao.FORWARD, "DESISTIU", {"motivo": evento.motivo, "tentativas": tentativa + 1})
    inicio = Passo.STEP3 if passo == Passo.STEP4 else passo  # o passo 4 não tem compensação
    return _compensar_a_partir(inicio, (desistiu,))


def _enviar_passo3(registro_passo2: Registro, politica: Politica, dados: dict | None) -> Transicao:
    publicado = Registro(Passo.STEP3, Direcao.FORWARD, "PUBLICADO")
    programar = PublicarMensagem(TipoMensagem.PROGRAMAR_LEMBRETE)
    if politica.aguardar_resposta_passo3:
        return Transicao(
            EstadoSaga(StatusSaga.AWAITING_COMUNICACAO, Passo.STEP3),
            (programar, AguardarResposta(politica.timeout_passo3)), (registro_passo2, publicado), dados=dados,
        )
    # Sem ms-comunicacao: o comando gravado no Outbox tem entrega garantida; o passo 3 conta como concluído.
    return Transicao(
        EstadoSaga(StatusSaga.CONFIRMING, Passo.STEP4),
        (programar, ExecutarPasso(Passo.STEP4)), (registro_passo2, publicado), dados=dados,
    )


def _aguardando_comunicacao(estado: EstadoSaga, evento: Evento) -> Transicao:
    if isinstance(evento, RespostaComunicacao) and evento.ok:
        ok = Registro(Passo.STEP3, Direcao.FORWARD, "OK")
        return Transicao(EstadoSaga(StatusSaga.CONFIRMING, Passo.STEP4), (ExecutarPasso(Passo.STEP4),), (ok,))
    if isinstance(evento, RespostaComunicacao):
        detalhe = {"motivo": evento.motivo} if evento.motivo else None
        falhou = Registro(Passo.STEP3, Direcao.FORWARD, "RECUSADO", detalhe)
        recusa = {"type": "urn:startech:error:lembrete-nao-programado", "detail": evento.motivo}
        return _compensar_a_partir(Passo.STEP3, (falhou,), recusa=recusa)
    if isinstance(evento, TimeoutPasso3):
        return _compensar_a_partir(Passo.STEP3, (Registro(Passo.STEP3, Direcao.FORWARD, "TIMEOUT"),))
    return _ignorar(estado)


# ---------------------------------------------------------------- compensações


def _compensar_a_partir(
    passo: Passo, registros: tuple[Registro, ...], recusa: dict | None = None, acoes: tuple[Acao, ...] = ()
) -> Transicao:
    """Entra (ou segue) em COMPENSATING com `passo` como o próximo a desfazer."""
    if passo == Passo.STEP3:  # desfeito na própria transição: cancelamento gravado no Outbox
        cancelado = Registro(Passo.STEP3, Direcao.COMPENSATE, "PUBLICADO")
        return _compensar_a_partir(
            Passo.STEP2, registros + (cancelado,), recusa, acoes + (PublicarMensagem(TipoMensagem.CANCELAR_LEMBRETE),)
        )
    return Transicao(
        EstadoSaga(StatusSaga.COMPENSATING, passo), acoes + (CompensarPasso(passo),), registros, recusa=recusa
    )


def _na_compensacao(estado: EstadoSaga, evento: Evento, politica: Politica) -> Transicao:
    passo = estado.passo
    if isinstance(evento, CompensacaoConcluida) and evento.passo == passo:
        ok = Registro(passo, Direcao.COMPENSATE, "OK")
        if passo == Passo.STEP1:
            return Transicao(
                EstadoSaga(StatusSaga.COMPENSATED, Passo.STEP1),
                (PublicarMensagem(TipoMensagem.AGENDAMENTO_COMPENSADO),), (ok,),
            )
        return _compensar_a_partir(_PASSO_ANTERIOR[passo], (ok,))

    if isinstance(evento, FalhaTecnica | PassoRecusado) and evento.passo == passo:
        # Compensações não podem ser recusadas pelo negócio: qualquer erro é tratado como falha técnica.
        motivo = evento.motivo if isinstance(evento, FalhaTecnica) else f"recusa inesperada: {evento.problema}"
        tentativa = estado.retry_count
        if tentativa < politica.max_retries:
            falha = Registro(passo, Direcao.COMPENSATE, "FALHA", {"motivo": motivo, "tentativa": tentativa + 1})
            return Transicao(
                EstadoSaga(StatusSaga.COMPENSATING, passo, tentativa + 1),
                (AgendarRetentativa(backoff_ms(tentativa, politica)),), (falha,),
            )
        desistiu = Registro(passo, Direcao.COMPENSATE, "DESISTIU", {"motivo": motivo, "tentativas": tentativa + 1})
        return Transicao(
            EstadoSaga(StatusSaga.COMPENSATION_FAILED, passo),
            (PublicarMensagem(TipoMensagem.COMPENSACAO_FALHOU),), (desistiu,),
        )
    return _ignorar(estado)


def _ignorar(estado: EstadoSaga) -> Transicao:
    return Transicao(estado, ignorado=True)
