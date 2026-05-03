#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

ENV_FILE=".env.localprod"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE."
  echo "Copy .env.localprod.example to .env.localprod and fill in the local-production secrets."
  exit 1
fi

docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.localprod.yml --profile accel down
