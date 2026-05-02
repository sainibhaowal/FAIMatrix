#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/Runtime/localprod/backups"
RAW_DIR="$PROJECT_ROOT/Runtime/localprod/raw"
TS="$(date +%Y%m%d_%H%M%S)"

cd "$PROJECT_ROOT"

mkdir -p "$BACKUP_DIR" "$RAW_DIR"

docker compose -f docker-compose.yml -f docker-compose.localprod.yml --profile accel exec -T \
  -e FAIM_BACKUP_DIR=/var/lib/faim/backups \
  api python -m orchestration.jobs.backup --compress --keep 14

tar -C "$PROJECT_ROOT/Runtime/localprod" -czf "$BACKUP_DIR/raw_${TS}.tar.gz" raw

echo "Backups created in $BACKUP_DIR"
