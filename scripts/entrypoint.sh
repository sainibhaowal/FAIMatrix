#!/usr/bin/env bash
# =============================================================================
# FAIM-Native Entrypoint
# =============================================================================
# Ensures schema is up-to-date before starting the application.
#
# Behavior:
#   FAIM_AUTO_MIGRATE=true  → Run migrations automatically
#   FAIM_AUTO_MIGRATE=false → Refuse to start if migrations are pending
# =============================================================================

set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL required}"

# Ensure raw blob store directory exists (volume mount may start empty after down -v)
RAW_PATH="${FAIM_RAW_STORE_PATH:-/var/lib/faim/raw/blobs}"
mkdir -p "${RAW_PATH}" 2>/dev/null || true

AUTO="${FAIM_AUTO_MIGRATE:-false}"

if [[ "${AUTO}" == "true" ]]; then
  echo "[entrypoint] FAIM_AUTO_MIGRATE=true -> applying migrations"
  python -m store.pg.migrate up
else
  echo "[entrypoint] FAIM_AUTO_MIGRATE=false -> requiring latest schema"
  python -m store.pg.migrate up --require-latest
fi

echo "✅ Schema verified. Starting application..."
exec "$@"
