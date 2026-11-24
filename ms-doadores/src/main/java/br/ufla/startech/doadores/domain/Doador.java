package br.ufla.startech.doadores.domain;

import java.time.Instant;
import java.time.LocalDate;
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
    @Column(name = "nome", nullable = false, length = 120)
    private String nome;

    @NotBlank
    @Pattern(regexp = "A[+-]|B[+-]|AB[+-]|O[+-]")
    @Column(name = "tipo_sanguineo", nullable = false, length = 3)
    private String tipoSanguineo;

    @Column(name = "sexo", nullable = false, length = 1)
    private String sexo;

    @Column(name = "data_ultima_doacao")
    private LocalDate dataUltimaDoacao;

    @Column(name = "criado_em", nullable = false, updatable = false)
    private Instant criadoEm;

    @Column(name = "atualizado_em", nullable = false)
    private Instant atualizadoEm;

    protected Doador() {
    }

    public Doador(UUID id, String nome, String tipoSanguineo, String sexo, LocalDate dataUltimaDoacao) {
        Instant agora = Instant.now();
        this.id = id;
        this.nome = nome.trim();
        this.tipoSanguineo = tipoSanguineo;
        this.sexo = sexo;
        this.dataUltimaDoacao = dataUltimaDoacao;
        this.criadoEm = agora;
        this.atualizadoEm = agora;
    }

    public void atualizarPerfil(String nome, String tipoSanguineo, String sexo, LocalDate dataUltimaDoacao) {
        this.nome = nome.trim();
        this.tipoSanguineo = tipoSanguineo;
        this.sexo = sexo;
        if (dataUltimaDoacao != null) {
            this.dataUltimaDoacao = dataUltimaDoacao;
        }
        this.atualizadoEm = Instant.now();
    }

    public UUID getId() {
        return id;
    }

    public String getNome() {
        return nome;
    }

    public String getTipoSanguineo() {
        return tipoSanguineo;
    }

    public Sexo getSexo() {
        return Sexo.valueOf(sexo);
    }

    /** {@code null} se o doador ainda não doou. */
    public LocalDate getDataUltimaDoacao() {
        return dataUltimaDoacao;
    }

    public void registrarDoacao(LocalDate data) {
        this.dataUltimaDoacao = data;
        this.atualizadoEm = Instant.now();
    }
}
