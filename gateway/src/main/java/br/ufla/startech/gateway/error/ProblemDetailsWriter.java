package br.ufla.startech.gateway.error;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

/**
 * Escreve respostas de erro HTTP padronizadas segundo a RFC 7807 (application/problem+json),
 * mantendo o mesmo contrato de erro utilizado pelos BFFs e microsservicos.
 */
@Component
public class ProblemDetailsWriter {

    private static final MediaType PROBLEM_JSON = MediaType.valueOf("application/problem+json");
    private final ObjectMapper objectMapper = new ObjectMapper();

    public Mono<Void> write(
            ServerWebExchange exchange,
            HttpStatus status,
            String errorTypeUrn,
            String title,
            String detail
    ) {
        var response = exchange.getResponse();
        response.setStatusCode(status);
        response.getHeaders().setContentType(PROBLEM_JSON);

        Map<String, Object> problemBody = new LinkedHashMap<>();
        problemBody.put("type", errorTypeUrn);
        problemBody.put("title", title);
        problemBody.put("status", status.value());
        problemBody.put("detail", detail);
        problemBody.put("instance", exchange.getRequest().getURI().getPath());

        byte[] serializedBytes = serialize(problemBody, status.value());
        DataBuffer buffer = response.bufferFactory().wrap(serializedBytes);
        return response.writeWith(Mono.just(buffer));
    }

    private byte[] serialize(Map<String, Object> problemBody, int fallbackStatus) {
        try {
            return objectMapper.writeValueAsBytes(problemBody);
        } catch (Exception ignored) {
            String fallback = "{\"status\":" + fallbackStatus + "}";
            return fallback.getBytes(StandardCharsets.UTF_8);
        }
    }
}
