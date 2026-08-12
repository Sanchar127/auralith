# ============================================================
# Stage 1 - Builder
# ============================================================
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /build

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    curl \
    git \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y

# Create virtual environment
RUN python -m venv /opt/venv

ENV PATH="/opt/venv/bin:${PATH}"

# Install Python dependencies
COPY deepfilternet/requirements.txt .

RUN pip install --upgrade pip

RUN pip install -r requirements.txt

# Copy source
COPY deepfilternet/ .

# ============================================================
# Stage 2 - Runtime
# ============================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

# Runtime libraries only
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment
COPY --from=builder /opt/venv /opt/venv

# Copy application
COPY --from=builder /build /app

EXPOSE 8001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]