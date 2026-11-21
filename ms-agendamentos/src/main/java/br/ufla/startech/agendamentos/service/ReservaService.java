package br.ufla.startech.agendamentos.service;

import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import br.ufla.startech.agendamentos.domain.Agendamento;
import br.ufla.startech.agendamentos.domain.Slot;
import br.ufla.startech.agendamentos.domain.StatusAgendamento;
import br.ufla.startech.agendamentos.repository.AgendamentoRepository;
import br.ufla.startech.agendamentos.repository.SlotRepository;

/**
 * Participação do ms-agendamentos na SAGA de agendamento (ADR-006, contratos §2).
 *
 * <ul>
 *   <li>Passo 1 ({@link #reservar}): cria o agendamento {@code CRIADO_PROVISORIO} e ocupa uma vaga;</li>
 *   <li>compensação do passo 1 ({@link #liberar}): devolve a vaga e marca {@code CANCELADO_COMPENSACAO_SAGA};</li>
 *   <li>passo 4 ({@link #confirmar}): {@code CRIADO_PROVISORIO} → {@code CONFIRMADO}.</li>
 * </ul>
 *
 * <p>Os três são idempotentes pelo {@code agendamentoId}, que o orquestrador gera uma vez por SAGA: repetir a
 * chamada (retentativa, recuperação, outra réplica) devolve o mesmo resultado sem ocupar ou devolver outra vaga.
 * A {@code Idempotency-Key} enviada pelo orquestrador ({@code saga-{id}-step{n}}) identifica a mesma operação.
 * O slot e o agendamento são travados com {@code SELECT ... FOR UPDATE}: duas reservas na última vaga não passam
 * as duas, e uma compensação concorrente com a confirmação é serializada.
 */
@Service
public class ReservaService {

    private final SlotRepository slots;
    private final AgendamentoRepository agendamentos;
    private final Clock clock;

    public ReservaService(SlotRepository slots, AgendamentoRepository agendamentos, Clock clock) {
        this.slots = slots;
        this.agendamentos = agendamentos;
        this.clock = clock;
    }

    @Transactional
    public Agendamento reservar(String slotId, String agendamentoId, String doadorId) {
        Optional<Agendamento> existente = agendamentos.buscarComSlot(agendamentoId);
        if (existente.isPresent()) {
            return repeticao(existente.get(), slotId, doadorId);
        }
        Slot slot = slots.buscarParaAtualizacao(slotId).orElseThrow(() -> new ReservaRecusadaException(
                HttpStatus.NOT_FOUND, "slot-nao-encontrado", "Slot não encontrado",
                "Não existe o slot " + slotId + "."));
        if (!slot.getDataHoraInicio().isAfter(clock.instant())) {
            throw new ReservaRecusadaException(HttpStatus.CONFLICT, "slot-encerrado", "Horário encerrado",
                    "O horário do slot " + slotId + " já passou.");
        }
        if (!slot.temVaga()) {
            throw new ReservaRecusadaException(HttpStatus.CONFLICT, "slot-esgotado", "Slot esgotado",
                    "Não há vagas no slot " + slotId + ".");
        }
        if (agendamentos.existeAtivoDoDoador(doadorId)) {
            throw agendamentoAtivo();
        }
        slot.ocuparVaga();
        // saveAndFlush: a violação do índice parcial (RN09, corrida entre duas SAGAs do mesmo doador) aparece aqui
        return agendamentos.saveAndFlush(
                new Agendamento(agendamentoId, doadorId, slot, StatusAgendamento.CRIADO_PROVISORIO));
    }

    @Transactional
    public void liberar(String slotId, String agendamentoId) {
        agendamentos.buscarParaAtualizacao(agendamentoId)
                .filter(a -> a.getSlot().getId().equals(slotId))
                .filter(a -> !a.getStatus().cancelado())
                .ifPresent(a -> a.compensar(clock.instant()));
    }

    @Transactional
    public Agendamento confirmar(String agendamentoId) {
        Agendamento agendamento = agendamentos.buscarParaAtualizacao(agendamentoId)
                .orElseThrow(() -> new AgendamentoNaoEncontradoException(agendamentoId));
        if (agendamento.getStatus().cancelado()) {
            throw new ReservaRecusadaException(HttpStatus.CONFLICT, "agendamento-ja-cancelado",
                    "Agendamento já cancelado", "O agendamento " + agendamentoId + " está "
                    + agendamento.getStatus() + " e não pode ser confirmado.");
        }
        if (agendamento.getStatus() == StatusAgendamento.CRIADO_PROVISORIO) {
            agendamento.confirmar(clock.instant());
        }
        return agendamento;
    }

    @Transactional(readOnly = true)
    public List<Slot> listarDisponiveis(String postoId, Instant de, Instant ate) {
        Instant agora = clock.instant();
        return slots.listarDisponiveis(postoId, de == null || de.isBefore(agora) ? agora : de,
                ate == null ? Instant.parse("9999-12-31T00:00:00Z") : ate);
    }

    private Agendamento repeticao(Agendamento existente, String slotId, String doadorId) {
        if (!existente.getSlot().getId().equals(slotId) || !existente.getDoadorId().equals(doadorId)) {
            throw new ReservaRecusadaException(HttpStatus.CONFLICT, "reserva-divergente", "Reserva divergente",
                    "O agendamento " + existente.getId() + " já existe com outro slot ou outro doador.");
        }
        return existente;
    }

    static ReservaRecusadaException agendamentoAtivo() {
        return new ReservaRecusadaException(HttpStatus.CONFLICT, "agendamento-ativo", "Agendamento ativo",
                "O doador já possui um agendamento em andamento ou confirmado (RN09).");
    }
}
