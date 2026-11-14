package br.ufla.startech.gateway.controller;

import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

@RestController
public class HealthController {

    @GetMapping("/health")
    public Mono<ResponseEntity<Map<String, String>>> health() {
        return Mono.just(ResponseEntity.ok(Map.of("status", "ok", "servico", "gateway")));
    }

    @GetMapping("/ready")
    public Mono<ResponseEntity<Map<String, String>>> ready() {
        return Mono.just(ResponseEntity.ok(Map.of("status", "ok", "servico", "gateway")));
    }
}
