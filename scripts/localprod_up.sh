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

export FAIM_ENV_FILE="$ENV_FILE"
chmod 600 "$ENV_FILE"

mkdir -p Runtime/localprod/{postgres,redis,qdrant,raw,backups,caddy_data,caddy_config}
"$PROJECT_ROOT/scripts/localprod_ssl.sh"

SERVICES=("$@")

if [[ ${#SERVICES[@]} -eq 0 ]]; then
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.localprod.yml --profile accel run --rm --build migrate
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.localprod.yml --profile accel up -d --build
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
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.localprod.yml --profile accel run --rm --build migrate
fi

if [[ ${#BUILD_SERVICES[@]} -gt 0 ]]; then
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.localprod.yml --profile accel build "${BUILD_SERVICES[@]}"
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.localprod.yml --profile accel up -d --no-deps "${BUILD_SERVICES[@]}"
fi
