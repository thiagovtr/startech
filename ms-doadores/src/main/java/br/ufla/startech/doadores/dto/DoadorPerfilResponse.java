package br.ufla.startech.doadores.dto;

import java.time.LocalDate;
import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonFormat;

public record DoadorPerfilResponse(
        UUID id,
        String nome,
        String tipoSanguineo,
        String sexo,
        @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd")
        LocalDate dataUltimaDoacao
) {
}
