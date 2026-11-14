package br.ufla.startech.gateway.config;

import br.ufla.startech.gateway.error.ProblemDetailsWriter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
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

/**
 * Configura a seguranca reativa na borda do API Gateway (ADR-005).
 * Valida tokens JWT RS256 do Keycloak e bloqueia acessos cruzados entre Mobile e Web.
 */
@Configuration
@EnableWebFluxSecurity
public class SecurityConfig {

    private static final String URN_UNAUTHENTICATED = "urn:startech:error:nao-autenticado";
    private static final String URN_ACCESS_DENIED = "urn:startech:error:acesso-negado";

    private final KeycloakJwtAuthenticationConverter jwtAuthenticationConverter;
    private final ProblemDetailsWriter problemDetailsWriter;

    public SecurityConfig(
            KeycloakJwtAuthenticationConverter jwtAuthenticationConverter,
            ProblemDetailsWriter problemDetailsWriter
    ) {
        this.jwtAuthenticationConverter = jwtAuthenticationConverter;
        this.problemDetailsWriter = problemDetailsWriter;
    }

    @Bean
    public SecurityWebFilterChain securityWebFilterChain(ServerHttpSecurity http) {
        ServerAuthenticationEntryPoint entryPoint = buildAuthenticationEntryPoint();
        ServerAccessDeniedHandler accessDeniedHandler = buildAccessDeniedHandler();

        return http
            .csrf(ServerHttpSecurity.CsrfSpec::disable)
            .httpBasic(ServerHttpSecurity.HttpBasicSpec::disable)
            .formLogin(ServerHttpSecurity.FormLoginSpec::disable)
            .authorizeExchange(exchanges -> exchanges
                .pathMatchers("/health", "/ready", "/actuator/health/**", "/realms/**").permitAll()
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
