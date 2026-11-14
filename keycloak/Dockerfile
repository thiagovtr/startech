# syntax=docker/dockerfile:1

# ---- Stage 1: pré-compilação Quarkus (otimiza startup e consumo de RAM para PostgreSQL) ----
FROM quay.io/keycloak/keycloak:26.0 AS builder

ENV KC_HEALTH_ENABLED=true
ENV KC_METRICS_ENABLED=false
ENV KC_DB=postgres

WORKDIR /opt/keycloak
RUN /opt/keycloak/bin/kc.sh build

# ---- Stage 2: imagem final enxuta com o realm StarTech embutido ----
FROM quay.io/keycloak/keycloak:26.0 AS runtime

COPY --from=builder /opt/keycloak/ /opt/keycloak/
COPY realm-export.json /opt/keycloak/data/import/startech-realm.json

# Limita heap da JVM do Keycloak para ambientes locais e Kubernetes
ENV JAVA_OPTS_APPEND="-Xms128m -Xmx384m"
ENV KC_DB=postgres
ENV KC_HEALTH_ENABLED=true
ENV KC_HTTP_ENABLED=true

# Usuário não-root padrão da imagem (uid 1000)
USER 1000

EXPOSE 8080 9000

# No Keycloak 26+, o endpoint /health/ready responde na porta de management 9000 via bash /dev/tcp
HEALTHCHECK --interval=10s --timeout=5s --start-period=25s --retries=12 \
  CMD bash -c 'exec 3<>/dev/tcp/127.0.0.1/9000 && echo -e "GET /health/ready HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n" >&3 && grep -q "200 OK" <&3'

ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
CMD ["start", "--optimized", "--import-realm"]
