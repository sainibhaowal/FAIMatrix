#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/Runtime/vps/backups"
RAW_DIR="$PROJECT_ROOT/Runtime/vps/raw"
TS="$(date +%Y%m%d_%H%M%S)"

cd "$PROJECT_ROOT"

ENV_FILE="deploy/env.vpsprod"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE."
  echo "Copy deploy/env.vpsprod.example to deploy/env.vpsprod and fill in the VPS-production secrets."
  exit 1
fi

export FAIM_ENV_FILE="$ENV_FILE"

mkdir -p "$BACKUP_DIR" "$RAW_DIR"

docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.vps.yml --profile accel exec -T \
  -e FAIM_BACKUP_DIR=/var/lib/faim/backups \
  api python -m orchestration.jobs.backup --compress --keep 14

tar -C "$PROJECT_ROOT/Runtime/vps" -czf "$BACKUP_DIR/raw_${TS}.tar.gz" raw

echo "Backups created in $BACKUP_DIR"
