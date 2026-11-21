package br.ufla.startech.agendamentos.controller;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import jakarta.validation.Valid;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import br.ufla.startech.agendamentos.domain.Agendamento;
import br.ufla.startech.agendamentos.domain.Slot;
import br.ufla.startech.agendamentos.dto.AgendamentoRepresentacao;
import br.ufla.startech.agendamentos.dto.ReservaRequest;
import br.ufla.startech.agendamentos.service.AgendamentoService;
import br.ufla.startech.agendamentos.service.ReservaService;

/** Grade de horários e endpoints da SAGA (passos 1 e 4 e a compensação do passo 1). Contratos §2. */
@RestController
public class ReservaController {

    private final ReservaService reservas;
    private final AgendamentoService agendamentos;

    public ReservaController(ReservaService reservas, AgendamentoService agendamentos) {
        this.reservas = reservas;
        this.agendamentos = agendamentos;
    }

    @GetMapping(path = "/api/v1/slots", produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> listarSlots(
            @RequestParam(required = false) String postoId,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant de,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant ate) {
        List<Map<String, Object>> itens = reservas.listarDisponiveis(postoId, de, ate).stream()
                .map(ReservaController::slot)
                .toList();
        return Map.of("itens", itens, "_links", Map.of("self", Map.of("href", "/api/v1/slots", "method", "GET")));
    }

    @PostMapping(path = "/api/v1/slots/{slotId}/reservas", produces = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<Map<String, Object>> reservar(
            @PathVariable String slotId, @Valid @RequestBody ReservaRequest corpo) {
        Agendamento agendamento = reservas.reservar(slotId, corpo.agendamentoId(), corpo.doadorId());
        Slot slot = agendamento.getSlot();
        Map<String, Object> resposta = new LinkedHashMap<>();
        resposta.put("agendamentoId", agendamento.getId());
        resposta.put("slotId", slot.getId());
        resposta.put("dataHoraInicio", slot.getDataHoraInicio().toString());
        resposta.put("dataHoraFim", slot.getDataHoraFim().toString());
        resposta.put("status", agendamento.getStatus().name());
        return ResponseEntity.status(HttpStatus.CREATED).body(resposta);
    }

    @DeleteMapping("/api/v1/slots/{slotId}/reservas/{agendamentoId}")
    public ResponseEntity<Void> liberar(@PathVariable String slotId, @PathVariable String agendamentoId) {
        reservas.liberar(slotId, agendamentoId);
        return ResponseEntity.noContent().build();
    }

    @PostMapping(path = "/api/v1/agendamentos/{id}/confirmacao", produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> confirmar(@PathVariable String id) {
        reservas.confirmar(id);
        return AgendamentoRepresentacao.de(agendamentos.buscar(id), agendamentos);
    }

    private static Map<String, Object> slot(Slot slot) {
        Map<String, Object> corpo = new LinkedHashMap<>();
        corpo.put("slotId", slot.getId());
        corpo.put("postoId", slot.getPostoId());
        corpo.put("dataHoraInicio", slot.getDataHoraInicio().toString());
        corpo.put("dataHoraFim", slot.getDataHoraFim().toString());
        corpo.put("vagasDisponiveis", slot.getCapacidade() - slot.getVagasOcupadas());
        corpo.put("_links", Map.of("agendar", Map.of(
                "href", "/api/v1/sagas/agendamento", "method", "POST",
                "title", "Solicitar agendamento neste horário (corpo: {slotId})")));
        return corpo;
    }
}
