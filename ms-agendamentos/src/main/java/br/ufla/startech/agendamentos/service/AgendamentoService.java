package br.ufla.startech.agendamentos.service;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import br.ufla.startech.agendamentos.domain.Agendamento;
import br.ufla.startech.agendamentos.domain.StatusAgendamento;
import br.ufla.startech.agendamentos.repository.AgendamentoRepository;

/**
 * Consulta e cancelamento de agendamentos (contratos §2 e §3).
 *
 * <p>Só um agendamento {@code CONFIRMADO} pode ser cancelado pelo doador, e até {@link #ANTECEDENCIA_MINIMA}
 * antes do início. {@code CRIADO_PROVISORIO} pertence à SAGA em andamento (quem desfaz é a compensação do
 * passo 1); cancelado não pode ser cancelado de novo; e depois do prazo o agendamento é tratado como concluído.
 */
@Service
public class AgendamentoService {

    public static final Duration ANTECEDENCIA_MINIMA = Duration.ofHours(2);

    private final AgendamentoRepository agendamentos;
    private final Clock clock;

    public AgendamentoService(AgendamentoRepository agendamentos, Clock clock) {
        this.agendamentos = agendamentos;
        this.clock = clock;
    }

    @Transactional(readOnly = true)
    public Agendamento buscar(String id) {
        return agendamentos.buscarComSlot(id).orElseThrow(() -> new AgendamentoNaoEncontradoException(id));
    }

    @Transactional(readOnly = true)
    public List<Agendamento> listarPorDoador(String doadorId) {
        return agendamentos.listarPorDoador(doadorId);
    }

    /** Se o agendamento ainda aceita cancelamento pelo doador agora (decide o link {@code cancelar}). */
    public boolean cancelavel(Agendamento agendamento) {
        return agendamento.getStatus() == StatusAgendamento.CONFIRMADO && dentroDoPrazo(agendamento);
    }

    /** Se o horário do agendamento já passou (confirmado e encerrado: sem ações). */
    public boolean concluido(Agendamento agendamento) {
        return agendamento.getStatus() == StatusAgendamento.CONFIRMADO
                && !agendamento.getSlot().getDataHoraFim().isAfter(agora());
    }

    @Transactional
    public Agendamento cancelar(String id, String motivo) {
        Agendamento agendamento = agendamentos.buscarParaAtualizacao(id)
                .orElseThrow(() -> new AgendamentoNaoEncontradoException(id));
        if (agendamento.getStatus().cancelado()) {
            throw new CancelamentoRecusadoException("agendamento-ja-cancelado", "Agendamento já cancelado",
                    "O agendamento " + id + " já está " + agendamento.getStatus() + ".");
        }
        if (agendamento.getStatus() != StatusAgendamento.CONFIRMADO) {
            throw new CancelamentoRecusadoException("agendamento-nao-cancelavel", "Agendamento ainda em processamento",
                    "O agendamento " + id + " ainda não foi confirmado; acompanhe a solicitação até o fim.");
        }
        if (!dentroDoPrazo(agendamento)) {
            throw new CancelamentoRecusadoException("prazo-cancelamento-expirado", "Prazo de cancelamento encerrado",
                    "O cancelamento é permitido até " + ANTECEDENCIA_MINIMA.toHours()
                            + " horas antes do horário agendado.");
        }
        // o slot é carregado pela associação na mesma transação; o @Version dele evita perda de atualização
        // concorrente com uma reserva (passo 1 da SAGA) no mesmo slot
        agendamento.cancelarPeloDoador(motivo, agora());
        return agendamento;
    }

    private boolean dentroDoPrazo(Agendamento agendamento) {
        return agora().isBefore(agendamento.getSlot().getDataHoraInicio().minus(ANTECEDENCIA_MINIMA));
    }

    private Instant agora() {
        return clock.instant();
    }
}
