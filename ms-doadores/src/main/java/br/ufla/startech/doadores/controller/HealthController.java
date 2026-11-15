package br.ufla.startech.doadores.controller;

import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {

    private static final Map<String, String> HEALTHY_RESPONSE = Map.of(
            "status", "ok",
            "servico", "ms-doadores"
    );

    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(HEALTHY_RESPONSE);
    }

    @GetMapping("/ready")
    public ResponseEntity<Map<String, String>> ready() {
        return ResponseEntity.ok(HEALTHY_RESPONSE);
    }
}
