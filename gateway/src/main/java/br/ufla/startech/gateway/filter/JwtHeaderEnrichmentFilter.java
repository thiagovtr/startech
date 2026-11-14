package br.ufla.startech.gateway.filter;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Consumer;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpHeaders;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpRequestDecorator;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.ReactiveSecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

/**
 * Filtro global que remove cabecalhos de identidade vindos do cliente externo (Header Stripping)
 * e injeta X-User-Id, X-User-Roles (do JWT validado) e X-Correlation-Id para os BFFs.
 */
@Component
public class JwtHeaderEnrichmentFilter implements GlobalFilter, Ordered {

    public static final String HEADER_USER_ID = "X-User-Id";
    public static final String HEADER_USER_ROLES = "X-User-Roles";
    public static final String HEADER_CORRELATION_ID = "X-Correlation-Id";

    @Override
    public int getOrder() {
        // Executa no inicio do roteamento (apos a autenticacao WebFlux Security)
        return -50;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String correlationId = resolveOrGenerateCorrelationId(exchange);
        exchange.getResponse().getHeaders().set(HEADER_CORRELATION_ID, correlationId);

        return ReactiveSecurityContextHolder.getContext()
            .flatMap(ctx -> Mono.justOrEmpty(ctx.getAuthentication()))
            .filter(auth -> auth.getPrincipal() instanceof Jwt)
            .map(Authentication::getPrincipal)
            .cast(Jwt.class)
            .map(jwt -> enrichRequestWithJwt(exchange, jwt, correlationId))
            .switchIfEmpty(Mono.fromSupplier(() -> stripForgedHeadersOnly(exchange, correlationId)))
            .flatMap(chain::filter);
    }

    private String resolveOrGenerateCorrelationId(ServerWebExchange exchange) {
        String incoming = exchange.getRequest().getHeaders().getFirst(HEADER_CORRELATION_ID);
        if (incoming != null && !incoming.isBlank()) {
            return incoming.trim();
        }
        return UUID.randomUUID().toString();
    }

    private ServerWebExchange enrichRequestWithJwt(ServerWebExchange exchange, Jwt jwt, String correlationId) {
        String userId = jwt.getSubject() != null ? jwt.getSubject() : "";
        String rolesCsv = String.join(",", extractRoles(jwt));

        return mutateRequestHeaders(exchange, headers -> {
            headers.remove(HEADER_USER_ID);
            headers.remove(HEADER_USER_ROLES);
            headers.set(HEADER_USER_ID, userId);
            headers.set(HEADER_USER_ROLES, rolesCsv);
            headers.set(HEADER_CORRELATION_ID, correlationId);
        });
    }

    private ServerWebExchange stripForgedHeadersOnly(ServerWebExchange exchange, String correlationId) {
        return mutateRequestHeaders(exchange, headers -> {
            headers.remove(HEADER_USER_ID);
            headers.remove(HEADER_USER_ROLES);
            headers.set(HEADER_CORRELATION_ID, correlationId);
        });
    }

    /**
     * Cria uma copia mutavel de HttpHeaders via ServerHttpRequestDecorator, evitando
     * UnsupportedOperationException em ReadOnlyHttpHeaders do Spring WebFlux 6.1+.
     */
    private ServerWebExchange mutateRequestHeaders(
            ServerWebExchange exchange,
            Consumer<HttpHeaders> headerMutator
    ) {
        HttpHeaders writableHeaders = new HttpHeaders();
        writableHeaders.putAll(exchange.getRequest().getHeaders());
        headerMutator.accept(writableHeaders);

        ServerHttpRequest decoratedRequest = new ServerHttpRequestDecorator(exchange.getRequest()) {
            @Override
            public HttpHeaders getHeaders() {
                return writableHeaders;
            }
        };
        return exchange.mutate().request(decoratedRequest).build();
    }

    private List<String> extractRoles(Jwt jwt) {
        List<String> roles = new ArrayList<>();
        Map<String, Object> realmAccess = jwt.getClaimAsMap("realm_access");
        if (realmAccess != null && realmAccess.get("roles") instanceof Collection<?> rawRoles) {
            for (Object role : rawRoles) {
                if (role != null && !role.toString().isBlank()) {
                    roles.add(role.toString().trim());
                }
            }
        }
        return roles;
    }
}
