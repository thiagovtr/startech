package br.ufla.startech.gateway.config;

import br.ufla.startech.gateway.error.ProblemDetailsWriter;
import java.util.Arrays;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.security.authorization.AuthorizationDecision;
import org.springframework.security.authorization.ReactiveAuthorizationManager;
import org.springframework.security.config.annotation.web.reactive.EnableWebFluxSecurity;
import org.springframework.security.config.web.server.ServerHttpSecurity;
import org.springframework.security.core.Authentication;
import org.springframework.security.web.server.SecurityWebFilterChain;
import org.springframework.security.web.server.ServerAuthenticationEntryPoint;
import org.springframework.security.web.server.authorization.AuthorizationContext;
import org.springframework.security.web.server.authorization.ServerAccessDeniedHandler;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.reactive.CorsConfigurationSource;
import org.springframework.web.cors.reactive.UrlBasedCorsConfigurationSource;

/**
 * Configura a seguranca reativa e CORS na borda do API Gateway (ADR-005).
 * Valida tokens JWT RS256 do Keycloak e bloqueia acessos cruzados entre Mobile e Web.
 */
@Configuration
@EnableWebFluxSecurity
public class SecurityConfig {

    private static final String URN_UNAUTHENTICATED = "urn:startech:error:nao-autenticado";
    private static final String URN_ACCESS_DENIED = "urn:startech:error:acesso-negado";

    private final KeycloakJwtAuthenticationConverter jwtAuthenticationConverter;
    private final ProblemDetailsWriter problemDetailsWriter;
    private final List<String> allowedOrigins;

    public SecurityConfig(
            KeycloakJwtAuthenticationConverter jwtAuthenticationConverter,
            ProblemDetailsWriter problemDetailsWriter,
            @Value("${startech.gateway.cors.allowed-origins:http://localhost:5173,http://localhost:3000,http://localhost:8085}")
            String allowedOriginsCsv
    ) {
        this.jwtAuthenticationConverter = jwtAuthenticationConverter;
        this.problemDetailsWriter = problemDetailsWriter;
        this.allowedOrigins = Arrays.stream(allowedOriginsCsv.split(","))
            .map(String::trim)
            .filter(origin -> !origin.isEmpty())
            .toList();
    }

    @Bean
    public SecurityWebFilterChain securityWebFilterChain(ServerHttpSecurity http) {
        ServerAuthenticationEntryPoint entryPoint = buildAuthenticationEntryPoint();
        ServerAccessDeniedHandler accessDeniedHandler = buildAccessDeniedHandler();

        return http
            .cors(cors -> cors.configurationSource(corsConfigurationSource()))
            .csrf(ServerHttpSecurity.CsrfSpec::disable)
            .httpBasic(ServerHttpSecurity.HttpBasicSpec::disable)
            .formLogin(ServerHttpSecurity.FormLoginSpec::disable)
            .authorizeExchange(exchanges -> exchanges
                .pathMatchers(HttpMethod.OPTIONS, "/**").permitAll()
                .pathMatchers("/health", "/ready", "/actuator/health/**", "/realms/**", "/resources/**").permitAll()
                .pathMatchers("/api/mobile/**").access(requireRoleAndAudience("doador", "bff-mobile"))
                .pathMatchers("/api/web/**").access(requireRoleAndAudience("operador", "bff-web"))
                .anyExchange().authenticated()
            )
            .oauth2ResourceServer(oauth2 -> oauth2
                .jwt(jwt -> jwt.jwtAuthenticationConverter(jwtAuthenticationConverter))
                .authenticationEntryPoint(entryPoint)
                .accessDeniedHandler(accessDeniedHandler)
            )
            .exceptionHandling(exceptions -> exceptions
                .authenticationEntryPoint(entryPoint)
                .accessDeniedHandler(accessDeniedHandler)
            )
            .build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOrigins(allowedOrigins);
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
        config.setAllowedHeaders(List.of(
            "Authorization",
            "Content-Type",
            "Accept",
            "X-Correlation-Id",
            "X-Request-Id",
            "Idempotency-Key"
        ));
        config.setExposedHeaders(List.of(
            "X-Correlation-Id",
            "X-Request-Id",
            "X-Total-Count",
            "Location"
        ));
        config.setAllowCredentials(true);
        config.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return source;
    }

    private ReactiveAuthorizationManager<AuthorizationContext> requireRoleAndAudience(
            String requiredRole,
            String requiredAudience
    ) {
        String roleAuthority = KeycloakJwtAuthenticationConverter.ROLE_PREFIX + requiredRole;
        String audienceAuthority = KeycloakJwtAuthenticationConverter.AUDIENCE_PREFIX + requiredAudience;

        return (authenticationMono, context) -> authenticationMono
            .map(auth -> new AuthorizationDecision(
                hasAuthority(auth, roleAuthority) && hasAuthority(auth, audienceAuthority)
            ))
            .defaultIfEmpty(new AuthorizationDecision(false));
    }

    private boolean hasAuthority(Authentication auth, String expectedAuthority) {
        if (auth == null || !auth.isAuthenticated() || auth.getAuthorities() == null) {
            return false;
        }
        return auth.getAuthorities().stream()
            .anyMatch(granted -> expectedAuthority.equals(granted.getAuthority()));
    }

    private ServerAuthenticationEntryPoint buildAuthenticationEntryPoint() {
        return (exchange, ex) -> problemDetailsWriter.write(
            exchange,
            HttpStatus.UNAUTHORIZED,
            URN_UNAUTHENTICATED,
            "Autenticação Obrigatória",
            "Token JWT ausente, expirado ou com assinatura inválida."
        );
    }

    private ServerAccessDeniedHandler buildAccessDeniedHandler() {
        return (exchange, ex) -> problemDetailsWriter.write(
            exchange,
            HttpStatus.FORBIDDEN,
            URN_ACCESS_DENIED,
            "Acesso Negado na Borda",
            "O token apresentado não possui o papel ou audience exigido para acessar esta rota."
        );
    }
}
