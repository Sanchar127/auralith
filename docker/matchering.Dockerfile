# ==========================================================
# Stage 1 - Builder
# ==========================================================
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /build

# ----------------------------------------------------------
# System dependencies
# ----------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------------------------------------
# Create virtual environment
# ----------------------------------------------------------
RUN python -m venv /opt/venv

ENV PATH="/opt/venv/bin:${PATH}"

# ----------------------------------------------------------
# Upgrade pip
# ----------------------------------------------------------
RUN pip install --upgrade pip setuptools wheel

# ----------------------------------------------------------
# Install Python dependencies
# ----------------------------------------------------------
COPY services/matchering/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ----------------------------------------------------------
# Copy FastAPI service
# ----------------------------------------------------------
COPY services/matchering/ .

# ==========================================================
# Stage 2 - Runtime
# ==========================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

# ----------------------------------------------------------
# Runtime dependencies
# ----------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------------------------------------
# Copy Python virtual environment
# ----------------------------------------------------------
COPY --from=builder /opt/venv /opt/venv

# ----------------------------------------------------------
# Copy application
# ----------------------------------------------------------
COPY --from=builder /build /app

# ----------------------------------------------------------
# Runtime directories
# ----------------------------------------------------------
RUN mkdir -p \
    /app/input \
    /app/reference \
    /app/output \
    /app/temp

# ----------------------------------------------------------
# Expose FastAPI
# ----------------------------------------------------------
EXPOSE 8003

# ----------------------------------------------------------
# Health Check
# ----------------------------------------------------------
HEALTHCHECK --interval=30s \
            --timeout=5s \
            --start-period=20s \
            --retries=3 \
CMD curl -fs http://localhost:8003/health || exit 1

# ----------------------------------------------------------
# Start API
# ----------------------------------------------------------
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8003"]