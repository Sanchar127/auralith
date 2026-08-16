#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

log() {
    printf '\n\033[1;34m[CI]\033[0m %s\n' "$1"
}

pass() {
    printf '\033[1;32m[PASS]\033[0m %s\n' "$1"
}

fail() {
    printf '\033[1;31m[FAIL]\033[0m %s\n' "$1"
    exit 1
}

wait_for() {
    local name="$1"
    local command="$2"
    local retries="${3:-30}"
    local delay="${4:-2}"

    log "Waiting for ${name}..."

    for ((i = 1; i <= retries; i++)); do
        if eval "$command" >/dev/null 2>&1; then
            pass "${name} is ready."
            return 0
        fi

        if [[ "$i" -eq "$retries" ]]; then
            fail "${name} did not become ready."
        fi

        sleep "$delay"
    done
}

ENV_FILE="$ROOT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    fail ".env was not found."
fi

set -a
source "$ENV_FILE"
set +a

# ============================================================
# PostgreSQL
# ============================================================

wait_for \
    "PostgreSQL" \
    "docker compose exec -T postgres pg_isready -U \"${POSTGRES_USER}\" -d \"${POSTGRES_DB}\""

log "Testing PostgreSQL functionality..."

docker compose exec -T postgres \
    psql \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -c "SELECT 1;" >/dev/null

pass "PostgreSQL query succeeded."

# ============================================================
# Redis
# ============================================================

wait_for \
    "Redis" \
    "docker compose exec -T redis redis-cli ping | grep -q PONG"

log "Testing Redis read/write functionality..."

docker compose exec -T redis \
    redis-cli SET ci_healthcheck "ok" >/dev/null

redis_value="$(
    docker compose exec -T redis \
        redis-cli GET ci_healthcheck |
        tr -d '\r'
)"

if [[ "$redis_value" != "ok" ]]; then
    fail "Redis read/write test failed."
fi

docker compose exec -T redis \
    redis-cli DEL ci_healthcheck >/dev/null

pass "Redis read/write succeeded."

# ============================================================
# RabbitMQ
# ============================================================

wait_for \
    "RabbitMQ" \
    "docker compose exec -T rabbitmq rabbitmq-diagnostics -q ping"

pass "RabbitMQ diagnostics succeeded."

# ============================================================
# MinIO
# ============================================================

wait_for \
    "MinIO" \
    "curl -fsS http://localhost:${MINIO_API_PORT}/minio/health/live"

pass "MinIO health endpoint succeeded."

# ============================================================
# Qdrant
# ============================================================

wait_for \
    "Qdrant" \
    "curl -fsS http://localhost:${QDRANT_PORT}/healthz"

pass "Qdrant health endpoint succeeded."

# ============================================================
# Ollama
# ============================================================

wait_for \
    "Ollama" \
    "curl -fsS http://localhost:${OLLAMA_PORT}/api/tags"

pass "Ollama API responded."

# ============================================================
# Final infrastructure state
# ============================================================

log "Infrastructure container status..."

docker compose ps

pass "All infrastructure checks passed."