#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$ROOT_DIR"

ENV_FILE="${AURALITH_ENV_FILE:-$ROOT_DIR/.env.ci}"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "[FAIL] Environment file not found: $ENV_FILE"
    exit 1
fi

echo "[CI] Validating development Compose configuration..."

AURALITH_ENV_FILE="$ENV_FILE" \
docker compose \
    --env-file "$ENV_FILE" \
    config --quiet

echo "[PASS] docker-compose.yml is valid."

echo "[CI] Validating production Compose configuration..."

docker compose \
    --env-file "$ENV_FILE" \
    -f docker-compose.prod.yml \
    config --quiet

echo "[PASS] docker-compose.prod.yml is valid."