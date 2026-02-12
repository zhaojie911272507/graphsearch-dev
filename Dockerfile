# ──────────────────────────────────────────
# Multi-stage build for Graph RAG System
# ──────────────────────────────────────────

# Stage 1: Base image with system dependencies
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Stage 2: Dependencies installation
FROM base AS deps

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Production image
FROM deps AS production

# Copy application code
COPY app/ ./app/

# Create non-root user
RUN groupadd -r graphrag && \
    useradd -r -g graphrag -d /app -s /sbin/nologin graphrag && \
    chown -R graphrag:graphrag /app

USER graphrag

# Model files will be mounted as a volume at runtime
VOLUME ["/app/model_files"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
