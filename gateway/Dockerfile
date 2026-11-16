# syntax=docker/dockerfile:1

# ---- Stage 1: build Maven com JDK 21 (cache de dependencias separado do codigo-fonte) ----
FROM maven:3.9.9-eclipse-temurin-21-alpine AS builder
WORKDIR /build

COPY pom.xml ./
RUN mvn -B -q dependency:go-offline

COPY src ./src
RUN mvn -B -q package -DskipTests

# ---- Stage 2: runtime JRE 21 enxuto (sem compilador, sem Maven, usuario nao-root) ----
FROM eclipse-temurin:21-jre-alpine AS runtime
WORKDIR /app

# Atualiza pacotes da distro para mitigar vulnerabilidades CVEs (Trivy) e instala curl para o healthcheck
RUN apk update && apk upgrade --no-cache && apk add --no-cache curl \
    && addgroup -g 10001 -S app && adduser -u 10001 -S app -G app

COPY --from=builder /build/target/gateway.jar /app/gateway.jar

# Restricao explicita de memoria RAM conforme diretriz do projeto (AGENT.md / ADR-001)
ENV JAVA_TOOL_OPTIONS="-Xms128m -Xmx256m -XX:+UseSerialGC"

USER app
EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=6 \
  CMD curl -fsS http://127.0.0.1:8080/health >/dev/null || exit 1

ENTRYPOINT ["java", "-jar", "/app/gateway.jar"]
