#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

ENV_FILE="deploy/env.vpsprod"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE."
  echo "Copy deploy/env.vpsprod.example to deploy/env.vpsprod and fill in the VPS-production secrets."
  exit 1
fi

export FAIM_ENV_FILE="$ENV_FILE"
chmod 600 "$ENV_FILE"

mkdir -p Runtime/vps/{postgres,redis,qdrant,raw,backups,caddy_data,caddy_config}

SERVICES=("$@")

if [[ ${#SERVICES[@]} -eq 0 ]]; then
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.vps.yml --profile accel run --rm --build migrate
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.vps.yml --profile accel up -d --build
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
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.vps.yml --profile accel run --rm --build migrate
fi

if [[ ${#BUILD_SERVICES[@]} -gt 0 ]]; then
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.vps.yml --profile accel build "${BUILD_SERVICES[@]}"
  docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.vps.yml --profile accel up -d --no-deps "${BUILD_SERVICES[@]}"
fi
