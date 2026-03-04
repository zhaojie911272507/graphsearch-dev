# ============================================================
# Multi-stage Dockerfile for GraphSearchNeo4j
# Targets: development | production
# ============================================================

# ----------------------------------------------------------
# Stage 1: base — shared runtime foundation
# ----------------------------------------------------------
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        tini && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# ----------------------------------------------------------
# Stage 2: builder — install all Python dependencies
# ----------------------------------------------------------
FROM base AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --prefix=/install \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# ----------------------------------------------------------
# Stage 3: development — full toolchain for local dev
# ----------------------------------------------------------
FROM base AS development

COPY --from=builder /install /usr/local

COPY . .

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ----------------------------------------------------------
# Stage 4: production — lean, hardened runtime image
# ----------------------------------------------------------
FROM base AS production

LABEL maintainer="GraphSearchNeo4j Team" \
      description="Enterprise Graph RAG System" \
      version="0.1.0"

COPY --from=builder /install /usr/local

COPY app/ /app/app/
COPY pyproject.toml /app/

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["curl", "-f", "http://localhost:8000/health"]

ENTRYPOINT ["tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--timeout-keep-alive", "65", "--log-level", "info"]
