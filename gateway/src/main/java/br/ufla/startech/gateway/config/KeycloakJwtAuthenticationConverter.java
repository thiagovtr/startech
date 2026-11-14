package br.ufla.startech.gateway.config;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.core.convert.converter.Converter;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

/**
 * Converte um token JWT do Keycloak em um token de autenticacao do Spring Security,
 * mapeando os papeis do realm para `ROLE_<papel>` e os audiences para `AUD_<audience>`.
 */
@Component
public class KeycloakJwtAuthenticationConverter implements Converter<Jwt, Mono<AbstractAuthenticationToken>> {

    public static final String ROLE_PREFIX = "ROLE_";
    public static final String AUDIENCE_PREFIX = "AUD_";

    @Override
    public Mono<AbstractAuthenticationToken> convert(Jwt jwt) {
        List<GrantedAuthority> authorities = new ArrayList<>();
        extractRealmRoles(jwt, authorities);
        extractAudiences(jwt, authorities);

        return Mono.just(new JwtAuthenticationToken(jwt, authorities, jwt.getSubject()));
    }

    private void extractRealmRoles(Jwt jwt, List<GrantedAuthority> targetAuthorities) {
        Map<String, Object> realmAccess = jwt.getClaimAsMap("realm_access");
        if (realmAccess == null || !(realmAccess.get("roles") instanceof Collection<?> rawRoles)) {
            return;
        }
        for (Object role : rawRoles) {
            if (role != null) {
                String normalizedRole = role.toString().trim().toLowerCase(Locale.ROOT);
                if (!normalizedRole.isEmpty()) {
                    targetAuthorities.add(new SimpleGrantedAuthority(ROLE_PREFIX + normalizedRole));
                }
            }
        }
    }

    private void extractAudiences(Jwt jwt, List<GrantedAuthority> targetAuthorities) {
        List<String> audiences = jwt.getAudience();
        if (audiences == null) {
            return;
        }
        for (String audience : audiences) {
            if (audience != null && !audience.isBlank()) {
                targetAuthorities.add(new SimpleGrantedAuthority(AUDIENCE_PREFIX + audience.trim()));
            }
        }
    }
}
