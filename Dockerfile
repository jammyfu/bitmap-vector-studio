# syntax=docker/dockerfile:1
# Bitmap Vector Studio — Multi-stage Dockerfile
# Targets:
#   runtime (default) : API server on port 8000
#   cli               : Interactive CLI
# =============================================================================

# ------------------------------------------------------------------------------
# Stage 1: builder
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Install build-time system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2-dev \
    libffi-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip / setuptools / wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /build

# Copy dependency metadata first for layer caching
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install Python dependencies (api + smart) and build wheel
RUN pip install --no-cache-dir \
    "cairosvg>=2.7" \
    "fastapi>=0.110" \
    "uvicorn[standard]>=0.29" \
    "python-multipart>=0.0.9" \
    "numpy>=1.24" \
    && pip wheel --no-cache-dir --wheel-dir /build/wheels \
    -e ".[api,smart]"

# ------------------------------------------------------------------------------
# Stage 2: runtime
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Install runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libffi8 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

WORKDIR /app

# Copy and install the pre-built wheel
COPY --from=builder /build/wheels /tmp/wheels
RUN pip install --no-cache-dir --find-links /tmp/wheels \
    bitmap-vector-studio[api,smart] \
    && rm -rf /tmp/wheels

# Create directories for mounted volumes
RUN mkdir -p /app/inputs /app/outputs

# Expose API port
EXPOSE 8000

# Health check for API mode
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default: run API server
CMD ["vector-studio", "api", "--host", "0.0.0.0", "--port", "8000"]

# ------------------------------------------------------------------------------
# Stage 3: cli
# ------------------------------------------------------------------------------
FROM runtime AS cli

# Override default command for interactive CLI usage
CMD ["vector-studio"]
