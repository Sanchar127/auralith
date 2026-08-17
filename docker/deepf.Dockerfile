# ============================================================
# Stage 1: Builder
# ============================================================

FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:/root/.cargo/bin:$PATH"

WORKDIR /build

# ------------------------------------------------------------
# Build dependencies
# ------------------------------------------------------------

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    curl \
    git \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# Install Rust
# ------------------------------------------------------------

RUN curl --proto '=https' \
    --tlsv1.2 \
    -sSf https://sh.rustup.rs \
    | sh -s -- -y --profile minimal

# ------------------------------------------------------------
# Python virtual environment
# ------------------------------------------------------------

RUN python -m venv /opt/venv

ENV PATH="/opt/venv/bin:/root/.cargo/bin:$PATH"

# ------------------------------------------------------------
# Python dependencies
# ------------------------------------------------------------

COPY deepfilternet/requirements.txt /tmp/requirements.txt

RUN pip install --upgrade pip setuptools wheel

RUN pip install -r /tmp/requirements.txt

# ------------------------------------------------------------
# Application source
# ------------------------------------------------------------

COPY deepfilternet /app


# ============================================================
# Stage 2: Runtime
# ============================================================

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# ------------------------------------------------------------
# Runtime dependencies
# ------------------------------------------------------------

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# Copy Python environment from builder
# ------------------------------------------------------------

COPY --from=builder /opt/venv /opt/venv

# ------------------------------------------------------------
# Copy application
# ------------------------------------------------------------

COPY --from=builder /app /app

# ------------------------------------------------------------
# Runtime directories
# ------------------------------------------------------------

RUN mkdir -p \
    /app/output \
    /app/logs

# ------------------------------------------------------------
# Ports
# ------------------------------------------------------------

EXPOSE 8001
EXPOSE 50053

# ------------------------------------------------------------
# Default command
# ------------------------------------------------------------

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]