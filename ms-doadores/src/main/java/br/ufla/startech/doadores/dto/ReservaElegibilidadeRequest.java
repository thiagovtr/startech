package br.ufla.startech.doadores.dto;

import java.time.Instant;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/** Passo 2 da SAGA (contratos §2): o {@code agendamentoId} vem do orquestrador e a data é a do slot reservado. */
public record ReservaElegibilidadeRequest(@NotBlank @Size(max = 64) String agendamentoId, @NotNull Instant dataSlot) {
}
