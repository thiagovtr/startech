package br.ufla.startech.agendamentos.controller;

import java.util.List;
import java.util.Map;
import jakarta.validation.Valid;
import org.springframework.http.MediaType;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import br.ufla.startech.agendamentos.dto.AgendamentoRepresentacao;
import br.ufla.startech.agendamentos.dto.CancelamentoRequest;
import br.ufla.startech.agendamentos.service.AgendamentoService;

/**
 * Recurso Agendamento com HATEOAS (contratos §2 e §3). Uso interno: quem garante que o doador só vê e cancela
 * os próprios agendamentos é o BFF Mobile (compara {@code doadorId} com o {@code X-User-Id} do Gateway).
 */
@RestController
@Validated
@RequestMapping(path = "/api/v1/agendamentos", produces = MediaType.APPLICATION_JSON_VALUE)
public class AgendamentoController {

    private final AgendamentoService service;

    public AgendamentoController(AgendamentoService service) {
        this.service = service;
    }

    @GetMapping
    public Map<String, Object> listar(@RequestParam String doadorId) {
        List<Map<String, Object>> itens = service.listarPorDoador(doadorId).stream()
                .map(a -> AgendamentoRepresentacao.de(a, service))
                .toList();
        return Map.of(
                "itens", itens,
                "_links", Map.of("self", Map.of("href", "/api/v1/agendamentos?doadorId=" + doadorId, "method", "GET"))
        );
    }

    @GetMapping("/{id}")
    public Map<String, Object> consultar(@PathVariable String id) {
        return AgendamentoRepresentacao.de(service.buscar(id), service);
    }

    @PostMapping("/{id}/cancelamento")
    public Map<String, Object> cancelar(
            @PathVariable String id, @Valid @RequestBody(required = false) CancelamentoRequest corpo) {
        String motivo = corpo == null || corpo.motivo() == null || corpo.motivo().isBlank()
                ? "Cancelado pelo doador" : corpo.motivo().strip();
        service.cancelar(id, motivo);
        // relê fora da transação de escrita para devolver o estado gravado
        return AgendamentoRepresentacao.de(service.buscar(id), service);
    }
}
