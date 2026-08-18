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

wait_for_http() {
    local name="$1"
    local url="$2"
    local retries="${3:-60}"

    log "Waiting for $name..."

    for ((i = 1; i <= retries; i++)); do
        if curl -fsS "$url" >/dev/null 2>&1; then
            pass "$name is responding."
            return 0
        fi

        if [[ "$i" -eq "$retries" ]]; then
            fail "$name failed to become ready: $url"
        fi

        sleep 2
    done
}

# ------------------------------------------------------------
# API
# ------------------------------------------------------------

wait_for_http \
    "Auralith API" \
    "http://localhost:8000/health"

# ------------------------------------------------------------
# Subscription
# ------------------------------------------------------------

# wait_for_http \
#     "Subscription service" \
#     "http://localhost:8002/health"


# ------------------------------------------------------------
# DeepFilterNet
# ------------------------------------------------------------

log "Checking DeepFilterNet container..."

deepfilter_status="$(
    docker inspect \
        --format='{{.State.Status}}' \
        auralith-deepfilternet
)"

if [[ "$deepfilter_status" != "running" ]]; then
    fail "DeepFilterNet container is not running. Status: $deepfilter_status"
fi

pass "DeepFilterNet container is running."

# ------------------------------------------------------------
# Celery
# ------------------------------------------------------------

log "Checking Celery worker..."

if ! docker compose exec -T celery \
    celery \
    -A app.workers.celery_app.celery \
    inspect ping; then

    fail "Celery worker did not respond to inspect ping."
fi

pass "Celery worker is responding."

# ------------------------------------------------------------
# Final status
# ------------------------------------------------------------

log "Application service status..."

docker compose ps

echo
pass "Application service checks passed."