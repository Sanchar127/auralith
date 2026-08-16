#!/usr/bin/env bash

set -Eeuo pipefail

log() {
    printf '\n\033[1;34m[SMOKE]\033[0m %s\n' "$1"
}

pass() {
    printf '\033[1;32m[PASS]\033[0m %s\n' "$1"
}

fail() {
    printf '\033[1;31m[FAIL]\033[0m %s\n' "$1"
    exit 1
}

# ------------------------------------------------------------
# API health
# ------------------------------------------------------------

log "Testing API health endpoint..."

response="$(
    curl \
        --fail-with-body \
        --silent \
        --show-error \
        http://localhost:8000/health
)"

echo "$response"

pass "API health endpoint passed."

# ------------------------------------------------------------
# MinIO
# ------------------------------------------------------------

log "Testing MinIO..."

curl \
    --fail \
    --silent \
    --show-error \
    http://localhost:9000/minio/health/live \
    >/dev/null

pass "MinIO smoke test passed."

# ------------------------------------------------------------
# Qdrant
# ------------------------------------------------------------

log "Testing Qdrant..."

curl \
    --fail \
    --silent \
    --show-error \
    http://localhost:6333/healthz \
    >/dev/null

pass "Qdrant smoke test passed."

# ------------------------------------------------------------
# Ollama
# ------------------------------------------------------------

log "Testing Ollama..."

ollama_response="$(
    curl \
        --fail-with-body \
        --silent \
        --show-error \
        http://localhost:11434/api/tags
)"

echo "$ollama_response"

pass "Ollama smoke test passed."

# ------------------------------------------------------------
# RabbitMQ
# ------------------------------------------------------------

log "Testing RabbitMQ..."

docker compose exec -T rabbitmq \
    rabbitmq-diagnostics -q ping

pass "RabbitMQ smoke test passed."

# ------------------------------------------------------------
# Redis
# ------------------------------------------------------------

log "Testing Redis..."

docker compose exec -T redis \
    redis-cli ping | grep -q PONG

pass "Redis smoke test passed."

# ------------------------------------------------------------
# PostgreSQL
# ------------------------------------------------------------

log "Testing PostgreSQL..."

docker compose exec -T postgres \
    psql \
    -U postgres \
    -d auralith \
    -c "SELECT 1;" >/dev/null

pass "PostgreSQL smoke test passed."

echo
printf '\033[1;32m============================================\033[0m\n'
printf '\033[1;32m       AURALITH SMOKE TESTS PASSED         \033[0m\n'
printf '\033[1;32m============================================\033[0m\n'