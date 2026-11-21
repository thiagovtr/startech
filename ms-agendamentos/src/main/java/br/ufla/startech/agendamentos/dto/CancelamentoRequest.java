package br.ufla.startech.agendamentos.dto;

import jakarta.validation.constraints.Size;

/** Corpo opcional de {@code POST /api/v1/agendamentos/{id}/cancelamento}. */
public record CancelamentoRequest(@Size(max = 255) String motivo) {
}
