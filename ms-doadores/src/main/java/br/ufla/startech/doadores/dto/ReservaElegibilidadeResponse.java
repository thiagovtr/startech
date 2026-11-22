package br.ufla.startech.doadores.dto;

import java.time.Instant;
import java.util.UUID;

public record ReservaElegibilidadeResponse(UUID doadorId, String agendamentoId, Instant dataSlot, boolean travado) {
}
