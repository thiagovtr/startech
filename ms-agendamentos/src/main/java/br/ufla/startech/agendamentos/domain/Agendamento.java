package br.ufla.startech.agendamentos.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

@Entity
@Table(name = "agendamentos")
public class Agendamento {

    @Id
    private String id;

    @Column(name = "doador_id", nullable = false, length = 64)
    private String doadorId;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "slot_id", nullable = false)
    private Slot slot;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private StatusAgendamento status;

    protected Agendamento() {
    }

    public Agendamento(String id, String doadorId, Slot slot, StatusAgendamento status) {
        this.id = id;
        this.doadorId = doadorId;
        this.slot = slot;
        this.status = status;
    }

    public String getId() {
        return id;
    }
}
