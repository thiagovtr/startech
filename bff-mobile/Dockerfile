# syntax=docker/dockerfile:1

# ---- Stage 1: build das wheels (com toolchain) ----
FROM python:3.12-slim AS builder
WORKDIR /build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
COPY pyproject.toml ./
COPY src ./src
RUN pip wheel --wheel-dir /wheels .

# ---- Stage 2: runtime slim, sem compiladores ----
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
# Aplica as correções de segurança da distro publicadas depois da imagem base (varredura Trivy no CI).
RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/*
RUN useradd --system --uid 10001 --no-create-home app
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels bff-mobile && rm -rf /wheels
USER app
EXPOSE 8001
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=2).status==200 else 1)"
CMD ["uvicorn", "bff_mobile.main:app", "--host", "0.0.0.0", "--port", "8001"]
