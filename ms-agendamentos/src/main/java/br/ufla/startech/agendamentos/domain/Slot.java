package br.ufla.startech.agendamentos.domain;

import java.time.Instant;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;

@Entity
@Table(name = "slots")
public class Slot {

    @Id
    private String id;

    @Column(name = "posto_id", nullable = false, length = 64)
    private String postoId;

    @Column(name = "data_hora_inicio", nullable = false)
    private Instant dataHoraInicio;

    @Column(name = "data_hora_fim", nullable = false)
    private Instant dataHoraFim;

    @Column(nullable = false)
    private int capacidade;

    @Column(name = "vagas_ocupadas", nullable = false)
    private int vagasOcupadas;

    @Version
    @Column(nullable = false)
    private long version;

    protected Slot() {
    }

    public Slot(String id, String postoId, Instant dataHoraInicio, Instant dataHoraFim, int capacidade, int vagasOcupadas) {
        this.id = id;
        this.postoId = postoId;
        this.dataHoraInicio = dataHoraInicio;
        this.dataHoraFim = dataHoraFim;
        this.capacidade = capacidade;
        this.vagasOcupadas = vagasOcupadas;
    }

    /** Devolve uma vaga ao slot (cancelamento ou compensação). */
    public void liberarVaga() {
        if (vagasOcupadas > 0) {
            vagasOcupadas--;
        }
    }

    public String getId() {
        return id;
    }

    public String getPostoId() {
        return postoId;
    }

    public Instant getDataHoraInicio() {
        return dataHoraInicio;
    }

    public Instant getDataHoraFim() {
        return dataHoraFim;
    }

    public int getCapacidade() {
        return capacidade;
    }

    public int getVagasOcupadas() {
        return vagasOcupadas;
    }
}
