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

mkdir -p Runtime/vps/{postgres,redis,qdrant,raw,backups,caddy_data,caddy_config}

docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.vps.yml --profile accel run --rm --build migrate
docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.vps.yml --profile accel up -d --build
