package br.ufla.startech.doadores.domain;

import java.time.Instant;
import java.util.UUID;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** Trava temporal do passo 2 da SAGA: a elegibilidade reservada para um agendamento, desfeita pela compensação. */
@Entity
@Table(name = "travas_elegibilidade")
public class TravaElegibilidade {

    @Id
    @Column(name = "agendamento_id", length = 64)
    private String agendamentoId;

    @Column(name = "doador_id", nullable = false)
    private UUID doadorId;

    @Column(name = "data_slot", nullable = false)
    private Instant dataSlot;

    @Column(name = "criado_em", nullable = false, updatable = false)
    private Instant criadoEm;

    protected TravaElegibilidade() {
    }

    public TravaElegibilidade(String agendamentoId, UUID doadorId, Instant dataSlot, Instant criadoEm) {
        this.agendamentoId = agendamentoId;
        this.doadorId = doadorId;
        this.dataSlot = dataSlot;
        this.criadoEm = criadoEm;
    }

    public String getAgendamentoId() {
        return agendamentoId;
    }

    public UUID getDoadorId() {
        return doadorId;
    }

    public Instant getDataSlot() {
        return dataSlot;
    }
}
