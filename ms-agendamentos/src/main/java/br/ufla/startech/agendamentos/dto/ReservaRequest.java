package br.ufla.startech.agendamentos.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** Corpo de {@code POST /api/v1/slots/{slotId}/reservas} (passo 1 da SAGA). */
public record ReservaRequest(
        @NotBlank @Size(max = 64) String agendamentoId,
        @NotBlank @Size(max = 64) String doadorId) {
}
