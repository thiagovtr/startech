package br.ufla.startech.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import br.ufla.startech.gateway.config.KeycloakJwtAuthenticationConverter;
import br.ufla.startech.gateway.filter.JwtHeaderEnrichmentFilter;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.HttpHeaders;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.test.web.reactive.server.SecurityMockServerConfigurers;
import org.springframework.test.web.reactive.server.WebTestClient;
import reactor.core.publisher.Mono;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureWebTestClient
class GatewaySecurityTests {

    @Autowired
    private WebTestClient webTestClient;

    @Autowired
    private KeycloakJwtAuthenticationConverter jwtConverter;

    @Autowired
    private JwtHeaderEnrichmentFilter headerEnrichmentFilter;

    @Test
    void healthEndpointDeveSerPublico() {
        webTestClient.get()
            .uri("/health")
            .exchange()
            .expectStatus().isOk()
            .expectBody()
            .jsonPath("$.status").isEqualTo("ok")
            .jsonPath("$.servico").isEqualTo("gateway");
    }

    @Test
    void requisicaoSemTokenParaMobileDeveRetornar401ProblemJson() {
        webTestClient.get()
            .uri("/api/mobile/home")
            .exchange()
            .expectStatus().isUnauthorized()
            .expectHeader().valueEquals("Content-Type", "application/problem+json")
            .expectBody()
            .jsonPath("$.type").isEqualTo("urn:startech:error:nao-autenticado")
            .jsonPath("$.title").isEqualTo("Autenticação Obrigatória")
            .jsonPath("$.status").isEqualTo(401);
    }

    @Test
    void doadorTentandoAcessarRotaWebDeveRetornar403Forbidden() {
        webTestClient
            .mutateWith(SecurityMockServerConfigurers.mockJwt()
                .jwt(jwt -> jwt
                    .subject("11111111-1111-1111-1111-111111111111")
                    .audience(List.of("bff-mobile"))
                    .claim("realm_access", Map.of("roles", List.of("doador")))
                )
                .authorities(
                    new SimpleGrantedAuthority("ROLE_doador"),
                    new SimpleGrantedAuthority("AUD_bff-mobile")
                )
            )
            .get()
            .uri("/api/web/campanhas")
            .exchange()
            .expectStatus().isForbidden()
            .expectHeader().valueEquals("Content-Type", "application/problem+json")
            .expectBody()
            .jsonPath("$.type").isEqualTo("urn:startech:error:acesso-negado")
            .jsonPath("$.title").isEqualTo("Acesso Negado na Borda")
            .jsonPath("$.status").isEqualTo(403);
    }

    @Test
    void operadorTentandoAcessarRotaMobileDeveRetornar403Forbidden() {
        webTestClient
            .mutateWith(SecurityMockServerConfigurers.mockJwt()
                .jwt(jwt -> jwt
                    .subject("22222222-2222-2222-2222-222222222222")
                    .audience(List.of("bff-web"))
                    .claim("realm_access", Map.of("roles", List.of("operador")))
                )
                .authorities(
                    new SimpleGrantedAuthority("ROLE_operador"),
                    new SimpleGrantedAuthority("AUD_bff-web")
                )
            )
            .get()
            .uri("/api/mobile/home")
            .exchange()
            .expectStatus().isForbidden()
            .expectHeader().valueEquals("Content-Type", "application/problem+json")
            .expectBody()
            .jsonPath("$.type").isEqualTo("urn:startech:error:acesso-negado")
            .jsonPath("$.title").isEqualTo("Acesso Negado na Borda")
            .jsonPath("$.status").isEqualTo(403);
    }

    @Test
    void conversorKeycloakDeveExtrairRolesEAudienceCorretamente() {
        Jwt sampleJwt = Jwt.withTokenValue("mock-token")
            .header("alg", "RS256")
            .subject("11111111-1111-1111-1111-111111111111")
            .audience(List.of("bff-mobile"))
            .claim("realm_access", Map.of("roles", List.of("doador")))
            .issuedAt(Instant.now())
            .expiresAt(Instant.now().plusSeconds(300))
            .build();

        var authToken = jwtConverter.convert(sampleJwt).block();
        assertThat(authToken).isNotNull();
        assertThat(authToken.getName()).isEqualTo("11111111-1111-1111-1111-111111111111");

        List<String> authorities = authToken.getAuthorities().stream()
            .map(GrantedAuthority::getAuthority)
            .toList();
        assertThat(authorities).containsExactlyInAnyOrder("ROLE_doador", "AUD_bff-mobile");
    }

    @Test
    void filtroDeCabecalhosDeveRemoverHeadersForjadosMesmoComReadOnlyHeaders() {
        MockServerHttpRequest forgedRequest = MockServerHttpRequest.post("/realms/startech/protocol/openid-connect/token")
            .header(JwtHeaderEnrichmentFilter.HEADER_USER_ID, "forged-id")
            .header(JwtHeaderEnrichmentFilter.HEADER_USER_ROLES, "operador")
            .build();
        MockServerWebExchange exchange = MockServerWebExchange.from(forgedRequest);

        AtomicReference<HttpHeaders> downstreamHeaders = new AtomicReference<>();
        headerEnrichmentFilter.filter(exchange, mutatedExchange -> {
            downstreamHeaders.set(mutatedExchange.getRequest().getHeaders());
            return Mono.empty();
        }).block();

        assertThat(downstreamHeaders.get()).isNotNull();
        assertThat(downstreamHeaders.get().getFirst(JwtHeaderEnrichmentFilter.HEADER_USER_ID)).isNull();
        assertThat(downstreamHeaders.get().getFirst(JwtHeaderEnrichmentFilter.HEADER_USER_ROLES)).isNull();
        assertThat(downstreamHeaders.get().getFirst(JwtHeaderEnrichmentFilter.HEADER_CORRELATION_ID)).isNotBlank();
    }
}
