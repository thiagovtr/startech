package br.ufla.startech.doadores.controller;

import java.util.UUID;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import br.ufla.startech.doadores.dto.ReservaElegibilidadeRequest;
import br.ufla.startech.doadores.dto.ReservaElegibilidadeResponse;
import br.ufla.startech.doadores.service.ElegibilidadeService;

/** Passo 2 da SAGA e sua compensação, chamados só pelo {@code ms-orquestrador} (contratos §2). */
@RestController
@RequestMapping("/api/v1/doadores/{id}/reservas-elegibilidade")
public class ElegibilidadeController {

    private final ElegibilidadeService elegibilidade;

    public ElegibilidadeController(ElegibilidadeService elegibilidade) {
        this.elegibilidade = elegibilidade;
    }

    @PostMapping
    public ReservaElegibilidadeResponse reservar(@PathVariable UUID id,
                                                 @Valid @RequestBody ReservaElegibilidadeRequest pedido) {
        return elegibilidade.reservar(id, pedido);
    }

    @DeleteMapping("/{agendamentoId}")
    public ResponseEntity<Void> liberar(@PathVariable UUID id, @PathVariable String agendamentoId) {
        elegibilidade.liberar(id, agendamentoId);
        return ResponseEntity.noContent().build();
    }
}
