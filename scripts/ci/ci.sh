#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# ============================================================
# Helpers
# ============================================================

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

# ============================================================
# Environment
# ============================================================

ENV_FILE="$ROOT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    fail ".env was not found."
fi

log "Loading environment from .env..."

set -a
source "$ENV_FILE"
set +a

export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-auralith-ci}"

pass "Environment loaded."

# ============================================================
# Required environment
# ============================================================

required_env=(
    POSTGRES_USER
    POSTGRES_PASSWORD
    POSTGRES_DB

    RABBITMQ_DEFAULT_USER
    RABBITMQ_DEFAULT_PASS

    MINIO_ROOT_USER
    MINIO_ROOT_PASSWORD

    MINIO_API_PORT
    QDRANT_PORT
    OLLAMA_PORT
    REDIS_PORT
    API_PORT
)

log "Validating required environment variables..."

for variable in "${required_env[@]}"; do
    if [[ -z "${!variable:-}" ]]; then
        fail "Required environment variable is missing: ${variable}"
    fi
done

pass "Required environment variables are available."

# ============================================================
# Cleanup
# ============================================================

cleanup() {
    local exit_code=$?

    log "Final container state..."

    docker compose \
        --env-file "$ENV_FILE" \
        ps || true

    log "Cleaning CI environment..."

    docker compose \
        --env-file "$ENV_FILE" \
        down \
        --volumes \
        --remove-orphans \
        >/dev/null 2>&1 || true

    if [[ "$exit_code" -eq 0 ]]; then
        pass "CI environment cleaned."
    else
        printf '\033[1;31m[CI] CI failed with exit code %s.\033[0m\n' "$exit_code"
    fi

    exit "$exit_code"
}

trap cleanup EXIT

# ============================================================
# 1. Required tools
# ============================================================

log "Checking required tools..."

for command in docker curl uv; do
    if ! command -v "$command" >/dev/null 2>&1; then
        fail "Required command not found: $command"
    fi
done

if ! docker compose version >/dev/null 2>&1; then
    fail "Docker Compose is unavailable."
fi

pass "Required tools are available."

# ============================================================
# 2. Repository validation
# ============================================================

log "Validating repository structure..."

required_files=(
    ".env.example"
    "docker-compose.yml"
    "docker-compose.prod.yml"

    "backend/pyproject.toml"
    "backend/uv.lock"
    "backend/alembic.ini"

    "docker/api.Dockerfile"
    "docker/deepf.Dockerfile"
    "docker/matchering.Dockerfile"
    "docker/subscription.Dockerfile"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        fail "Missing required file: $file"
    fi
done

required_directories=(
    "backend/app"
    "backend/test"
    "backend/test/unit"
    "backend/test/integration"
    "backend/test/evaluation"

    "contracts"
    "deepfilternet"
    "subscription"
    "services"
)

for directory in "${required_directories[@]}"; do
    if [[ ! -d "$directory" ]]; then
        fail "Missing required directory: $directory"
    fi
done

pass "Repository structure is valid."

# ============================================================
# 3. Python dependencies
# ============================================================

log "Synchronizing Python dependencies..."

(
    cd backend
    uv sync --frozen --all-groups
)

pass "Python dependencies synchronized."

# ============================================================
# 4. Unit tests
# ============================================================

log "Running unit tests..."

(
    cd backend

    APP_ENV=test \
    LOG_LEVEL=WARNING \
    uv run pytest \
        test/unit \
        -ra \
        --strict-config \
        --strict-markers \
        --tb=short
)

pass "Unit tests passed."

# ============================================================
# 5. Docker Compose validation
# ============================================================

log "Validating Docker Compose configuration..."

docker compose \
    --env-file "$ENV_FILE" \
    config --quiet

pass "Docker Compose configuration is valid."

# ============================================================
# 6. Production Compose validation
# ============================================================

log "Validating production Docker Compose configuration..."

docker compose \
    -f docker-compose.prod.yml \
    --env-file "$ENV_FILE" \
    config --quiet

pass "Production Compose configuration is valid."

# ============================================================
# 7. Build Docker images
# ============================================================

log "Building Docker images..."

docker compose \
    --env-file "$ENV_FILE" \
    build

pass "Docker images built successfully."

# ============================================================
# 8. Start infrastructure
# ============================================================

log "Starting infrastructure services..."

docker compose \
    --env-file "$ENV_FILE" \
    up -d \
    postgres \
    redis \
    rabbitmq \
    minio \
    qdrant \
    ollama

pass "Infrastructure services started."

# ============================================================
# 9. Infrastructure checks
# ============================================================

log "Running infrastructure checks..."

"$ROOT_DIR/scripts/ci/check-infrastructure.sh"

pass "Infrastructure checks passed."

# ============================================================
# 10. MinIO initialization
# ============================================================

log "Initializing MinIO..."

docker compose \
    --env-file "$ENV_FILE" \
    run --rm minio-init

pass "MinIO initialization passed."

# ============================================================
# 11. Start application services
# ============================================================

log "Starting application services..."

docker compose \
    --env-file "$ENV_FILE" \
    up -d \
    api \
    celery \
    subscription \
    deepfilternet \
    matchering

pass "Application services started."

# ============================================================
# 12. Application service checks
# ============================================================

log "Running application service checks..."

"$ROOT_DIR/scripts/ci/check-services.sh"

pass "Application service checks passed."

# ============================================================
# 13. Evaluation tests
# ============================================================

log "Running evaluation tests..."

docker compose \
    --env-file "$ENV_FILE" \
    exec -T api \
    pytest \
    test/evaluation \
    -ra \
    --strict-config \
    --strict-markers \
    --tb=short

pass "Evaluation tests passed."

# ============================================================
# 14. Smoke tests
# ============================================================

log "Running smoke tests..."

"$ROOT_DIR/scripts/ci/smoke-test.sh"

pass "Smoke tests passed."

# ============================================================
# 15. Integration tests
# ============================================================

log "Running integration tests..."

docker compose \
    --env-file "$ENV_FILE" \
    exec -T api \
    pytest \
    test/integration \
    -ra \
    --strict-config \
    --strict-markers \
    --tb=short

pass "Integration tests passed."

# ============================================================
# 16. Database migration verification
# ============================================================

log "Checking Alembic migrations..."

docker compose \
    --env-file "$ENV_FILE" \
    exec -T api \
    alembic current

pass "Alembic migration check passed."

# ============================================================
# 17. Final service state
# ============================================================

log "Final Docker service state..."

docker compose \
    --env-file "$ENV_FILE" \
    ps

# ============================================================
# 18. Detect failed containers
# ============================================================

failed_containers="$(
    docker compose \
        --env-file "$ENV_FILE" \
        ps \
        --status exited \
        --status dead \
        --format '{{.Name}}'
)"

if [[ -n "$failed_containers" ]]; then
    echo "$failed_containers"
    fail "One or more containers exited unexpectedly."
fi

pass "No failed containers detected."

# ============================================================
# 19. Success
# ============================================================

printf '\n'
printf '\033[1;32m============================================================\033[0m\n'
printf '\033[1;32m                  AURALITH CI PASSED                       \033[0m\n'
printf '\033[1;32m============================================================\033[0m\n'
printf '\n'