"""Vocabulário da SAGA de agendamento: status, passos, eventos e ações (ADR-006 §5.2 e §5.3).

Módulo puro (sem IO): usado pela máquina de estados, pelo executor e pelo modelo do banco.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class StatusSaga(StrEnum):
    STARTED = "STARTED"  # passo 1 (reservar vaga) pendente
    SLOT_RESERVED = "SLOT_RESERVED"  # passo 2 (elegibilidade) pendente
    AWAITING_COMUNICACAO = "AWAITING_COMUNICACAO"  # comando do passo 3 no Outbox; aguardando resposta
    CONFIRMING = "CONFIRMING"  # passo 4 (confirmar agendamento) pendente
    COMPENSATING = "COMPENSATING"  # desfazendo passos concluídos, do `passo` atual até o passo 1
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"  # recusa de negócio no passo 1: nada a desfazer
    COMPENSATED = "COMPENSATED"
    COMPENSATION_FAILED = "COMPENSATION_FAILED"  # compensação esgotou as tentativas: vai para a DLQ


STATUS_TERMINAIS = frozenset(
    {StatusSaga.CONFIRMED, StatusSaga.REJECTED, StatusSaga.COMPENSATED, StatusSaga.COMPENSATION_FAILED}
)


class Passo(StrEnum):
    STEP1 = "STEP1"  # ms-agendamentos: reservar / liberar vaga (HTTP)
    STEP2 = "STEP2"  # ms-doadores: reservar / liberar elegibilidade (HTTP)
    STEP3 = "STEP3"  # ms-comunicacao: programar / cancelar lembrete (RabbitMQ via Outbox)
    STEP4 = "STEP4"  # ms-agendamentos: confirmar agendamento (HTTP; sem compensação)


class Direcao(StrEnum):
    FORWARD = "FORWARD"
    COMPENSATE = "COMPENSATE"


class TipoMensagem(StrEnum):
    """Mensagens que a SAGA grava no Outbox (routing keys e corpos: contratos §2.1)."""

    PROGRAMAR_LEMBRETE = "PROGRAMAR_LEMBRETE"
    CANCELAR_LEMBRETE = "CANCELAR_LEMBRETE"
    AGENDAMENTO_CONFIRMADO = "AGENDAMENTO_CONFIRMADO"
    AGENDAMENTO_COMPENSADO = "AGENDAMENTO_COMPENSADO"
    COMPENSACAO_FALHOU = "COMPENSACAO_FALHOU"


# ---------------------------------------------------------------- estado e política


@dataclass(frozen=True)
class EstadoSaga:
    status: StatusSaga
    passo: Passo
    retry_count: int = 0


@dataclass(frozen=True)
class Politica:
    max_retries: int = 5  # falhas técnicas toleradas por passo antes de desistir (ADR-002 §5.3)
    backoff_base_ms: int = 500  # espera = 2^tentativa * base (o jitter é somado por quem agenda)
    aguardar_resposta_passo3: bool = True  # False: passo 3 conclui ao gravar o comando no Outbox
    timeout_passo3: float = 30.0  # segundos


# ---------------------------------------------------------------- eventos (resultado do que foi executado)


@dataclass(frozen=True)
class PassoConcluido:
    passo: Passo
    dados: dict = field(default_factory=dict)  # ex.: dataHoraInicio devolvida pelo passo 1


@dataclass(frozen=True)
class PassoRecusado:
    """Recusa de negócio (409 vaga esgotada / RN09, 422 RN01): não se tenta de novo."""

    passo: Passo
    problema: dict = field(default_factory=dict)  # corpo problem+json do participante


@dataclass(frozen=True)
class FalhaTecnica:
    """Timeout, 5xx ou falha de conexão (na ação positiva ou na compensação do `passo`)."""

    passo: Passo
    motivo: str = ""


@dataclass(frozen=True)
class CompensacaoConcluida:
    passo: Passo


@dataclass(frozen=True)
class RespostaComunicacao:
    ok: bool
    motivo: str = ""


@dataclass(frozen=True)
class TimeoutPasso3:
    pass


Evento = PassoConcluido | PassoRecusado | FalhaTecnica | CompensacaoConcluida | RespostaComunicacao | TimeoutPasso3


# ---------------------------------------------------------------- ações (o que o executor deve fazer)


@dataclass(frozen=True)
class ExecutarPasso:
    """Chamada HTTP da ação positiva (passos 1, 2 e 4), feita DEPOIS de gravar a transição."""

    passo: Passo


@dataclass(frozen=True)
class CompensarPasso:
    """Chamada HTTP de compensação (passos 1 e 2), feita DEPOIS de gravar a transição."""

    passo: Passo


@dataclass(frozen=True)
class PublicarMensagem:
    """Insere a mensagem no Outbox NA MESMA transação da mudança de estado."""

    tipo: TipoMensagem


@dataclass(frozen=True)
class AgendarRetentativa:
    espera_ms: int


@dataclass(frozen=True)
class AguardarResposta:
    timeout_s: float


Acao = ExecutarPasso | CompensarPasso | PublicarMensagem | AgendarRetentativa | AguardarResposta


@dataclass(frozen=True)
class Registro:
    """Linha do saga_step_log."""

    passo: Passo
    direcao: Direcao
    resultado: str  # OK | RECUSADO | FALHA | DESISTIU | PUBLICADO | TIMEOUT
    detalhe: dict | None = None


@dataclass(frozen=True)
class Transicao:
    estado: EstadoSaga
    acoes: tuple[Acao, ...] = ()
    registros: tuple[Registro, ...] = ()
    recusa: dict | None = None  # problem+json da recusa de negócio, para o GET da SAGA
    dados: dict | None = None  # dados a acumular no payload da SAGA
    ignorado: bool = False  # evento fora de ordem, duplicado ou após status final: nada muda

    @property
    def terminal(self) -> bool:
        return self.estado.status in STATUS_TERMINAIS
