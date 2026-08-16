#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$ROOT_DIR"

ENV_FILE="${AURALITH_ENV_FILE:-$ROOT_DIR/.env.ci}"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "[FAIL] Environment file not found: $ENV_FILE"
    exit 1
fi

echo "[CI] Stopping Auralith CI environment..."

AURALITH_ENV_FILE="$ENV_FILE" \
docker compose \
    --env-file "$ENV_FILE" \
    down \
    --volumes \
    --remove-orphans

echo "[CI] Cleanup completed."