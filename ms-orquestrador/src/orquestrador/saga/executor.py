"""Executor da SAGA: liga a máquina de estados (pura) aos participantes e ao banco.

Ciclo de `avancar(saga_id)`:
  1. reivindica a SAGA por um prazo (só um processo executa a chamada pendente; se ele cair, o prazo vence
     e o worker de recuperação a retoma, repetindo a chamada idempotente);
  2. pergunta à máquina a próxima ação e a executa (HTTP; ou timeout do passo 3, se o prazo da resposta venceu);
  3. converte o resultado em evento, calcula a transição e a grava numa única transação (estado + log + Outbox);
  4. repete enquanto houver ação imediata; para em retentativa agendada, espera do passo 3 ou status final.
"""

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orquestrador.clients.agendamentos import AgendamentosClient
from orquestrador.clients.base import Falha, Recusa, Resultado, Sucesso
from orquestrador.clients.doadores import DoadoresClient
from orquestrador.models.orm import SagaExecucao
from orquestrador.observabilidade import request_id_var
from orquestrador.repositories import sagas as repo
from orquestrador.saga.estados import (
    CompensacaoConcluida,
    CompensarPasso,
    Evento,
    ExecutarPasso,
    FalhaTecnica,
    Passo,
    PassoConcluido,
    PassoRecusado,
    Politica,
    StatusSaga,
    TimeoutPasso3,
)
from orquestrador.saga.maquina import proxima_acao, transicionar

logger = logging.getLogger(__name__)

# Dados devolvidos pelo passo 1 que a SAGA guarda (usados nos passos 2 e 3)
_DADOS_DA_RESERVA = ("dataHoraInicio", "dataHoraFim")


def _agora() -> datetime:
    return datetime.now(UTC)


class Executor:
    def __init__(
        self,
        sessoes: async_sessionmaker[AsyncSession],
        agendamentos: AgendamentosClient,
        doadores: DoadoresClient,
        politica: Politica,
        prazo_reivindicacao: float,
        relogio: Callable[[], datetime] = _agora,
        jitter: Callable[[int], int] | None = None,
    ):
        self._sessoes = sessoes
        self._agendamentos = agendamentos
        self._doadores = doadores
        self.politica = politica
        self._prazo = prazo_reivindicacao
        self._relogio = relogio
        self._jitter = jitter or repo.jitter_padrao

    async def avancar(self, saga_id: uuid.UUID, reivindicada: bool = False) -> SagaExecucao | None:
        """Leva a SAGA adiante até não haver ação imediata. Devolve o último estado gravado.

        `reivindicada=True`: quem chama já reservou a SAGA (worker de recuperação, `selecionar_pendentes`).
        """
        saga: SagaExecucao | None = None
        while True:
            if reivindicada:
                atual = await repo.obter(self._sessoes, saga_id)
                reivindicada = False
            else:
                atual = await repo.reivindicar(self._sessoes, saga_id, self._relogio(), self._prazo)
            if atual is None:  # finalizada, aguardando retentativa/resposta, ou outra réplica está nela
                return saga
            saga = atual
            token = request_id_var.set(saga.correlation_id)
            try:
                evento = await self._executar(saga)
                if evento is None:
                    return saga
                transicao = transicionar(repo.estado_de(saga), evento, self.politica)
                try:
                    saga = await repo.aplicar_transicao(
                        self._sessoes, saga, transicao, agora=self._relogio(), jitter=self._jitter
                    )
                except repo.ConflitoVersao:
                    logger.info("SAGA %s mudou durante o passo (evento concorrente); seguindo o estado novo", saga_id)
                    continue
                if not transicao.ignorado:
                    logger.info(
                        "SAGA %s: %s -> %s (%s)", saga_id, atual.status, saga.status,
                        ", ".join(f"{r.passo} {r.direcao} {r.resultado}" for r in transicao.registros),
                    )
            finally:
                request_id_var.reset(token)
            if transicao.ignorado or transicao.terminal:
                return saga

    async def _executar(self, saga: SagaExecucao) -> Evento | None:
        estado = repo.estado_de(saga)
        acao = proxima_acao(estado)
        if acao is None:
            # Só se chega aqui reivindicando uma SAGA que aguarda o passo 3 com o prazo vencido.
            return TimeoutPasso3() if estado.status == StatusSaga.AWAITING_COMUNICACAO else None
        try:
            resultado = await self._chamar(saga, acao)
        except Exception as exc:  # erro inesperado não pode deixar a SAGA parada
            logger.exception("Erro inesperado ao executar %s da SAGA %s", acao, saga.saga_id)
            resultado = Falha(f"erro interno: {type(exc).__name__}")
        return _evento(acao, resultado)

    async def _chamar(self, saga: SagaExecucao, acao: ExecutarPasso | CompensarPasso) -> Resultado:
        sid, ag, corr = saga.saga_id, saga.agendamento_id, saga.correlation_id
        if isinstance(acao, ExecutarPasso):
            if acao.passo == Passo.STEP1:
                return await self._agendamentos.reservar_vaga(sid, saga.slot_id, ag, saga.doador_id, corr)
            if acao.passo == Passo.STEP2:
                data_slot = (saga.payload or {}).get("dataHoraInicio", "")
                return await self._doadores.reservar_elegibilidade(sid, saga.doador_id, ag, data_slot, corr)
            if acao.passo == Passo.STEP4:
                return await self._agendamentos.confirmar(sid, ag, corr)
        else:
            if acao.passo == Passo.STEP1:
                return await self._agendamentos.liberar_vaga(sid, saga.slot_id, ag, corr)
            if acao.passo == Passo.STEP2:
                return await self._doadores.liberar_elegibilidade(sid, saga.doador_id, ag, corr)
        raise ValueError(f"ação sem chamada HTTP: {acao}")


def _evento(acao: ExecutarPasso | CompensarPasso, resultado: Resultado) -> Evento:
    passo = acao.passo
    if isinstance(resultado, Sucesso):
        if isinstance(acao, CompensarPasso):
            return CompensacaoConcluida(passo)
        dados = {k: resultado.dados[k] for k in _DADOS_DA_RESERVA if k in resultado.dados}
        return PassoConcluido(passo, dados if passo == Passo.STEP1 else {})
    if isinstance(resultado, Recusa):
        return PassoRecusado(passo, resultado.problema)
    return FalhaTecnica(passo, resultado.motivo)
