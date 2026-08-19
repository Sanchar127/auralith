
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

# ------------------------------------------------------------
# HTTP readiness check
# ------------------------------------------------------------

wait_for_http() {
    local name="$1"
    local url="$2"
    local retries="${3:-120}"

    log "Waiting for $name..."

    for ((i = 1; i <= retries; i++)); do

        if curl \
            --fail \
            --silent \
            --show-error \
            --connect-timeout 3 \
            --max-time 5 \
            "$url" >/dev/null 2>&1; then

            pass "$name is responding."
            return 0
        fi

        if (( i % 10 == 0 )); then
            log "$name not ready yet (${i}/${retries})..."
        fi

        sleep 2
    done

    printf '\033[1;31m[FAIL]\033[0m %s failed to become ready: %s\n' \
        "$name" "$url"

    return 1
}

# ------------------------------------------------------------
# API - container-side health check
# ------------------------------------------------------------

check_api_inside_container() {
    local retries="${1:-120}"

    log "Waiting for Auralith API inside the container..."

    for ((i = 1; i <= retries; i++)); do

        if docker compose exec -T api \
            python -c "
import urllib.request

url = 'http://127.0.0.1:8000/health'

with urllib.request.urlopen(url, timeout=5) as response:
    body = response.read().decode()
    print(body)

    if response.status != 200:
        raise SystemExit(1)
" >/dev/null 2>&1; then

            pass "Auralith API is healthy inside the container."
            return 0
        fi

        if (( i % 10 == 0 )); then
            log "Auralith API not ready inside container (${i}/${retries})..."
        fi

        sleep 2
    done

    printf '\033[1;31m[FAIL]\033[0m Auralith API failed inside the container.\n'

    echo
    log "Auralith API logs:"
    docker compose logs --no-color --tail=300 api || true

    return 1
}

# ------------------------------------------------------------
# API - host-side health check
# ------------------------------------------------------------

check_api_from_host() {
    wait_for_http \
        "Auralith API from CI host" \
        "http://127.0.0.1:8000/health" \
        120
}

# ------------------------------------------------------------
# API
# ------------------------------------------------------------

log "Running Auralith API checks..."

# First verify that FastAPI/Uvicorn is actually serving
# inside the API container.
check_api_inside_container || fail "Auralith API is not healthy inside the container."

# Then verify that Docker's published port is reachable
# from the CI host.
check_api_from_host || {
    log "Host-side API check failed."

    log "Docker port mapping:"
    docker port auralith-api || true

    log "Auralith API container state:"
    docker inspect auralith-api \
        --format='Status={{.State.Status}} Running={{.State.Running}} ExitCode={{.State.ExitCode}}' \
        || true

    log "Auralith API logs:"
    docker compose logs --no-color --tail=200 api || true

    fail "Auralith API is healthy inside the container but unreachable from the CI host."
}

# ------------------------------------------------------------
# Subscription
# ------------------------------------------------------------

# wait_for_http \
#     "Subscription service" \
#     "http://127.0.0.1:8002/health" \
#     60

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
pass "All application service checks passed."

