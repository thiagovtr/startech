package br.ufla.startech.doadores.controller;

import java.util.UUID;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import br.ufla.startech.doadores.dto.DoadorPerfilRequest;
import br.ufla.startech.doadores.dto.DoadorPerfilResponse;
import br.ufla.startech.doadores.service.DoadorService;

@RestController
@RequestMapping("/api/v1/doadores")
public class DoadorController {

    private final DoadorService doadorService;

    public DoadorController(DoadorService doadorService) {
        this.doadorService = doadorService;
    }

    @GetMapping("/{id}")
    public DoadorPerfilResponse buscarPorId(@PathVariable UUID id) {
        return doadorService.buscarPerfil(id);
    }

    @PutMapping("/{id}")
    public DoadorPerfilResponse salvarPorId(@PathVariable UUID id, @Valid @RequestBody DoadorPerfilRequest request) {
        return doadorService.salvarPerfil(id, request);
    }
}
