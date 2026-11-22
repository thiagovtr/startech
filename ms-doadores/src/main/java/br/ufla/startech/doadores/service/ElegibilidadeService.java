package br.ufla.startech.doadores.service;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import br.ufla.startech.doadores.domain.Doador;
import br.ufla.startech.doadores.domain.RegraIntervaloDoacao;
import br.ufla.startech.doadores.domain.TravaElegibilidade;
import br.ufla.startech.doadores.dto.ReservaElegibilidadeRequest;
import br.ufla.startech.doadores.dto.ReservaElegibilidadeResponse;
import br.ufla.startech.doadores.repository.DoadorRepository;
import br.ufla.startech.doadores.repository.TravaElegibilidadeRepository;

/**
 * Passo 2 da SAGA de agendamento (contratos §2): valida a RN01 e trava a data, e a compensação remove a trava.
 *
 * <p>Os dois são idempotentes pelo {@code agendamentoId}, que o orquestrador gera uma vez por SAGA: repetir a
 * reserva devolve a mesma trava, e remover uma trava que não existe também responde sucesso. A
 * {@code Idempotency-Key} ({@code saga-{id}-step2}) identifica a mesma operação.
 *
 * <p>A trava registra a elegibilidade reservada para a SAGA e é o que a compensação desfaz. Ela não entra no
 * cálculo da RN01 de outros pedidos: duas SAGAs simultâneas do mesmo doador já são barradas no passo 1 (RN09), e o
 * cancelamento pelo doador não chega a este serviço, então contar a trava bloquearia quem cancelou.
 */
@Service
public class ElegibilidadeService {

    private final DoadorRepository doadores;
    private final TravaElegibilidadeRepository travas;
    private final Clock clock;

    public ElegibilidadeService(DoadorRepository doadores, TravaElegibilidadeRepository travas, Clock clock) {
        this.doadores = doadores;
        this.travas = travas;
        this.clock = clock;
    }

    @Transactional
    public ReservaElegibilidadeResponse reservar(UUID doadorId, ReservaElegibilidadeRequest pedido) {
        Doador doador = doadores.buscarParaAtualizacao(doadorId)
                .orElseThrow(() -> new DoadorNaoEncontradoException(doadorId));

        var existente = travas.findById(pedido.agendamentoId());
        if (existente.isPresent()) {
            TravaElegibilidade trava = existente.get();
            if (!trava.getDoadorId().equals(doadorId)) {
                throw new TravaDeOutroDoadorException(pedido.agendamentoId());
            }
            return resposta(trava);
        }

        RegraIntervaloDoacao.avaliar(doador.getSexo(), doador.getDataUltimaDoacao(), dia(pedido.dataSlot()))
                .ifPresent(violacao -> {
                    throw new DoadorInaptoException(violacao);
                });

        TravaElegibilidade trava = travas.save(
                new TravaElegibilidade(pedido.agendamentoId(), doadorId, pedido.dataSlot(), clock.instant()));
        return resposta(trava);
    }

    /** Compensação do passo 2. Trava inexistente (ou de outro doador) já conta como liberada. */
    @Transactional
    public void liberar(UUID doadorId, String agendamentoId) {
        travas.findById(agendamentoId)
                .filter(trava -> trava.getDoadorId().equals(doadorId))
                .ifPresent(travas::delete);
    }

    private static LocalDate dia(Instant instante) {
        return LocalDate.ofInstant(instante, ZoneOffset.UTC);
    }

    private static ReservaElegibilidadeResponse resposta(TravaElegibilidade trava) {
        return new ReservaElegibilidadeResponse(trava.getDoadorId(), trava.getAgendamentoId(), trava.getDataSlot(),
                true);
    }
}
