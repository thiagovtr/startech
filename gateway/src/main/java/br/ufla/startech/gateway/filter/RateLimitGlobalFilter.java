package br.ufla.startech.gateway.filter;

import br.ufla.startech.gateway.error.ProblemDetailsWriter;
import java.net.InetSocketAddress;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

/**
 * Rate Limiter baseado em Token Bucket na borda do API Gateway (ADR-005 / Secao 4.3).
 * Controla a vazao de requisicoes por usuario autenticado (X-User-Id) ou IP de origem.
 */
@Component
public class RateLimitGlobalFilter implements GlobalFilter, Ordered {

    private static final String URN_RATE_LIMIT = "urn:startech:error:rate-limit-excedido";
    private static final double NANOS_PER_SECOND = 1_000_000_000.0;

    private final ConcurrentHashMap<String, TokenBucket> bucketsByClient = new ConcurrentHashMap<>();
    private final ProblemDetailsWriter problemDetailsWriter;
    private final boolean enabled;
    private final int bucketCapacity;
    private final double refillTokensPerSecond;

    public RateLimitGlobalFilter(
            ProblemDetailsWriter problemDetailsWriter,
            @Value("${startech.gateway.rate-limit.enabled:true}") boolean enabled,
            @Value("${startech.gateway.rate-limit.capacity:60}") int bucketCapacity,
            @Value("${startech.gateway.rate-limit.refill-per-second:30}") double refillTokensPerSecond
    ) {
        this.problemDetailsWriter = problemDetailsWriter;
        this.enabled = enabled;
        this.bucketCapacity = bucketCapacity;
        this.refillTokensPerSecond = refillTokensPerSecond;
    }

    @Override
    public int getOrder() {
        // Executa logo apos o JwtHeaderEnrichmentFilter (-50) para ja dispor do X-User-Id confiavel
        return -40;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String requestPath = exchange.getRequest().getURI().getPath();
        if (!enabled || !requestPath.startsWith("/api/")) {
            return chain.filter(exchange);
        }

        String clientKey = resolveClientKey(exchange);
        TokenBucket clientBucket = bucketsByClient.computeIfAbsent(
            clientKey,
            key -> new TokenBucket(bucketCapacity, refillTokensPerSecond)
        );

        if (!clientBucket.tryConsumeOneToken()) {
            exchange.getResponse().getHeaders().set("Retry-After", "1");
            return problemDetailsWriter.write(
                exchange,
                HttpStatus.TOO_MANY_REQUESTS,
                URN_RATE_LIMIT,
                "Limite de Requisições Excedido",
                "A cota máxima de requisições por segundo foi atingida. Aguarde antes de tentar novamente."
            );
        }

        return chain.filter(exchange);
    }

    private String resolveClientKey(ServerWebExchange exchange) {
        String authenticatedUserId = exchange.getRequest().getHeaders().getFirst(JwtHeaderEnrichmentFilter.HEADER_USER_ID);
        if (authenticatedUserId != null && !authenticatedUserId.isBlank()) {
            return "user:" + authenticatedUserId;
        }
        String forwardedFor = exchange.getRequest().getHeaders().getFirst("X-Forwarded-For");
        if (forwardedFor != null && !forwardedFor.isBlank()) {
            return "ip:" + forwardedFor.split(",")[0].trim();
        }
        InetSocketAddress remoteAddress = exchange.getRequest().getRemoteAddress();
        if (remoteAddress != null && remoteAddress.getAddress() != null) {
            return "ip:" + remoteAddress.getAddress().getHostAddress();
        }
        return "ip:unknown";
    }

    static final class TokenBucket {
        private final double capacity;
        private final double refillTokensPerNano;
        private double availableTokens;
        private long lastRefillNano;

        TokenBucket(int capacity, double refillTokensPerSecond) {
            this.capacity = capacity;
            this.refillTokensPerNano = refillTokensPerSecond / NANOS_PER_SECOND;
            this.availableTokens = capacity;
            this.lastRefillNano = System.nanoTime();
        }

        synchronized boolean tryConsumeOneToken() {
            refill();
            if (availableTokens >= 1.0) {
                availableTokens -= 1.0;
                return true;
            }
            return false;
        }

        private void refill() {
            long nowNano = System.nanoTime();
            long elapsedNanos = Math.max(0L, nowNano - lastRefillNano);
            availableTokens = Math.min(capacity, availableTokens + elapsedNanos * refillTokensPerNano);
            lastRefillNano = nowNano;
        }
    }
}
