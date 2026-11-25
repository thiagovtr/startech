package br.ufla.startech.doadores.dto;

import java.time.LocalDate;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Past;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/** Payload para cadastrar ou atualizar o perfil do doador autenticado (PUT /api/v1/doadores/{id}). */
public record DoadorPerfilRequest(
        @NotBlank @Size(min = 2, max = 120) String nome,
        @NotBlank @Pattern(regexp = "A[+-]|B[+-]|AB[+-]|O[+-]") String tipoSanguineo,
        @NotBlank @Pattern(regexp = "[MF]") String sexo,
        LocalDate dataUltimaDoacao,
        @Past LocalDate dataNascimento
) {
}
