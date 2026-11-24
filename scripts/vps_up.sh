#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

ENV_FILE=".env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE."
  echo "Copy .env.example to .env and fill in the production secrets."
  exit 1
fi

chmod 600 "$ENV_FILE"

SERVICES=("$@")

if [[ ${#SERVICES[@]} -eq 0 ]]; then
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml --profile vps run --rm --build migrate
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml --profile vps up -d --build
  exit 0
fi

BUILD_SERVICES=()
RUN_MIGRATE=false
for svc in "${SERVICES[@]}"; do
  if [[ "$svc" == "migrate" ]]; then
    RUN_MIGRATE=true
  else
    BUILD_SERVICES+=("$svc")
  fi
done

if $RUN_MIGRATE; then
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml --profile vps run --rm --build migrate
fi

if [[ ${#BUILD_SERVICES[@]} -gt 0 ]]; then
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml --profile vps build "${BUILD_SERVICES[@]}"
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml --profile vps up -d --no-deps "${BUILD_SERVICES[@]}"
fi
