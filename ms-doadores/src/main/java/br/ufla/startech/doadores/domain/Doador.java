package br.ufla.startech.doadores.domain;

import java.time.Instant;
import java.util.UUID;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

@Entity
@Table(name = "doadores")
public class Doador {

    @Id
    private UUID id;

    @NotBlank
    @Pattern(regexp = "A[+-]|B[+-]|AB[+-]|O[+-]")
    @Column(name = "tipo_sanguineo", nullable = false, length = 3)
    private String tipoSanguineo;

    @Column(name = "criado_em", nullable = false, updatable = false)
    private Instant criadoEm;

    @Column(name = "atualizado_em", nullable = false)
    private Instant atualizadoEm;

    protected Doador() {
    }

    public UUID getId() {
        return id;
    }

    public String getTipoSanguineo() {
        return tipoSanguineo;
    }
}
