#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/Runtime/vps/backups"
RAW_DIR="$PROJECT_ROOT/Runtime/vps/raw"

cd "$PROJECT_ROOT"

ENV_FILE="deploy/env.vpsprod"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE."
  echo "Copy deploy/env.vpsprod.example to deploy/env.vpsprod and fill in the VPS-production secrets."
  exit 1
fi

export FAIM_ENV_FILE="$ENV_FILE"

DB_BACKUP="${1:-}"
RAW_BACKUP="${2:-}"

if [[ -z "$DB_BACKUP" ]]; then
  DB_BACKUP="$(ls -1t "$BACKUP_DIR"/backup_faim_*.sql.gz 2>/dev/null | head -n 1 || true)"
fi

if [[ -z "$RAW_BACKUP" ]]; then
  RAW_BACKUP="$(ls -1t "$BACKUP_DIR"/raw_*.tar.gz 2>/dev/null | head -n 1 || true)"
fi

if [[ -z "$DB_BACKUP" || -z "$RAW_BACKUP" ]]; then
  echo "Missing backup files. Expected a compressed DB backup and raw tarball in $BACKUP_DIR."
  exit 1
fi

echo "Stopping VPS production stack..."
docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.vps.yml --profile accel stop api worker frontend caddy qdrant || true

echo "Restoring database from $DB_BACKUP..."
gunzip -c "$DB_BACKUP" | docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.vps.yml --profile accel exec -T postgres psql -U faim -d faim_native

echo "Restoring raw files from $RAW_BACKUP..."
rm -rf "$RAW_DIR"
mkdir -p "$RAW_DIR"
tar -xzf "$RAW_BACKUP" -C "$PROJECT_ROOT/Runtime/vps"

echo "Restarting VPS production stack..."
docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.vps.yml --profile accel up -d

echo "Restore complete."
