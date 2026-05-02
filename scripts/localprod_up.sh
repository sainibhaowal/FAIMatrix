#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

mkdir -p Runtime/localprod/{postgres,redis,qdrant,raw,backups,caddy_data,caddy_config}
"$PROJECT_ROOT/scripts/localprod_ssl.sh"

docker compose -f docker-compose.yml -f docker-compose.localprod.yml --profile accel run --rm --build migrate
docker compose -f docker-compose.yml -f docker-compose.localprod.yml --profile accel up -d --build
