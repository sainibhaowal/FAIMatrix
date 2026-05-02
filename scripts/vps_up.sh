#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

mkdir -p Runtime/vps/{postgres,redis,qdrant,raw,backups,caddy_data,caddy_config}

docker compose -f docker-compose.yml -f docker-compose.vps.yml --profile accel run --rm --build migrate
docker compose -f docker-compose.yml -f docker-compose.vps.yml --profile accel up -d --build
