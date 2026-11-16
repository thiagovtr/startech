package br.ufla.startech.doadores.controller;

import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {

    private static final Map<String, String> HEALTHY_RESPONSE = Map.of(
            "status", "ok",
            "servico", "ms-doadores"
    );
    private final JdbcTemplate jdbcTemplate;

    public HealthController(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(HEALTHY_RESPONSE);
    }

    @GetMapping("/ready")
    public ResponseEntity<Map<String, String>> ready() {
        try {
            jdbcTemplate.queryForObject("SELECT 1", Integer.class);
        } catch (RuntimeException exception) {
            throw new BancoIndisponivelException(exception);
        }
        return ResponseEntity.ok(HEALTHY_RESPONSE);
    }
}
