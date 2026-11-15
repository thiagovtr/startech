package br.ufla.startech.doadores.dto;

import java.util.UUID;

public record DoadorPerfilResponse(UUID id, String tipoSanguineo) {
}
