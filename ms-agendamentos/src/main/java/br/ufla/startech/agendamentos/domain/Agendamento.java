package br.ufla.startech.agendamentos.domain;

import java.time.Instant;
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

    @Column(name = "atualizado_em", nullable = false)
    private Instant atualizadoEm;

    @Column(name = "data_cancelamento")
    private Instant dataCancelamento;

    @Column(name = "motivo_cancelamento", length = 255)
    private String motivoCancelamento;

    protected Agendamento() {
    }

    public Agendamento(String id, String doadorId, Slot slot, StatusAgendamento status) {
        this.id = id;
        this.doadorId = doadorId;
        this.slot = slot;
        this.status = status;
        this.atualizadoEm = Instant.now();
    }

    /** Cancelamento pelo doador: muda o estado e devolve a vaga ao slot (o chamador valida as regras). */
    public void cancelarPeloDoador(String motivo, Instant agora) {
        slot.liberarVaga();
        this.status = StatusAgendamento.CANCELADO_DOADOR;
        this.motivoCancelamento = motivo;
        this.dataCancelamento = agora;
        this.atualizadoEm = agora;
    }

    public String getId() {
        return id;
    }

    public String getDoadorId() {
        return doadorId;
    }

    public Slot getSlot() {
        return slot;
    }

    public StatusAgendamento getStatus() {
        return status;
    }

    public Instant getDataCancelamento() {
        return dataCancelamento;
    }

    public String getMotivoCancelamento() {
        return motivoCancelamento;
    }
}
