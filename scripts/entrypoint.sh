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

AUTO="${FAIM_AUTO_MIGRATE:-false}"

if [[ "${AUTO}" == "true" ]]; then
  echo "🗄️ FAIM_AUTO_MIGRATE=true — Running migrations..."
  python -m store.pg.migrate up
else
  echo "🔒 FAIM_AUTO_MIGRATE=false — Verifying schema is current..."
  python -m store.pg.migrate status --require-latest
fi

echo "✅ Schema verified. Starting application..."
exec "$@"
