#!/usr/bin/env bash
set -euo pipefail

# Pull and activate images built by GitHub Actions. This intentionally avoids
# `docker compose down` so the reverse proxy and data services remain running.
# It never prunes Docker volumes.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/deploy/env.vpsprod"

: "${FAIM_IMAGE_PREFIX:?FAIM_IMAGE_PREFIX is required}"
: "${FAIM_IMAGE_TAG:?FAIM_IMAGE_TAG is required}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

# Never boot a VPS with the checked-in example secrets. A present-but-
# unconfigured active assignment must fail before Compose can mutate any
# service. Comments may legitimately document the CHANGE_ME convention.
if awk '
  /^[[:space:]]*(#|$)/ { next }
  /^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=/ && /CHANGE_ME_/ { found = 1 }
  END { exit(found ? 0 : 1) }
' "$ENV_FILE"; then
  echo "$ENV_FILE still contains CHANGE_ME placeholders; install real VPS secrets first" >&2
  exit 1
fi

# Read dotenv values without sourcing the file.  Sourcing an operator-owned
# env file would execute shell syntax and is unnecessary for validation.
env_value() {
  local key="$1"
  awk -v wanted="$key" 'index($0, wanted "=") == 1 { print substr($0, length(wanted) + 2); exit }' "$ENV_FILE"
}

remove_bootstrap_env_line() {
  local temporary_env_file
  temporary_env_file="$(mktemp "${ENV_FILE}.bootstrap.XXXXXX")"
  if ! awk 'index($0, "FAIM_TENANT_KEY_BOOTSTRAP_JSON=") != 1 { print }' \
    "$ENV_FILE" > "$temporary_env_file"; then
    rm -f -- "$temporary_env_file"
    return 1
  fi
  if ! chmod 600 "$temporary_env_file"; then
    rm -f -- "$temporary_env_file"
    return 1
  fi
  if ! mv "$temporary_env_file" "$ENV_FILE"; then
    rm -f -- "$temporary_env_file"
    return 1
  fi
}

required_values=(
  FAIM_MODE FAIM_ENV POSTGRES_PASSWORD REDIS_PASSWORD QDRANT_API_KEY
  DATABASE_URL REDIS_URL QDRANT_URL NEXTAUTH_URL NEXTAUTH_SECRET
  FAIM_MASTER_KEY TENANT_KEYS_JSON FAIM_PUBLIC_ORIGIN FAIM_CORS_ALLOW_ORIGINS
)
for key in "${required_values[@]}"; do
  if [[ -z "$(env_value "$key")" ]]; then
    echo "$ENV_FILE is missing a required value: $key" >&2
    exit 1
  fi
done

if [[ "$(env_value FAIM_MODE | tr '[:upper:]' '[:lower:]')" != "production" ||
      "$(env_value FAIM_ENV | tr '[:upper:]' '[:lower:]')" != "production" ]]; then
  echo "$ENV_FILE must set FAIM_MODE=production and FAIM_ENV=production" >&2
  exit 1
fi

if [[ "$(env_value FAIM_ALLOW_DEV_AUTH_BYPASS | tr '[:upper:]' '[:lower:]')" != "false" ]]; then
  echo "$ENV_FILE must set FAIM_ALLOW_DEV_AUTH_BYPASS=false" >&2
  exit 1
fi

if [[ "$(env_value FAIM_AUTH_ENV_FALLBACK_ENABLED | tr '[:upper:]' '[:lower:]')" != "false" ]]; then
  echo "$ENV_FILE must set FAIM_AUTH_ENV_FALLBACK_ENABLED=false" >&2
  exit 1
fi

# Production authentication is DB-only. Keep the legacy variable present as an
# explicit empty JSON object so Compose has deterministic input, but refuse a
# persistent plaintext tenant-key map. The one-time bootstrap below reads a
# separate temporary variable and removes it after a successful DB import.
if [[ "$(env_value TENANT_KEYS_JSON)" != "{}" ]]; then
  echo "$ENV_FILE must set TENANT_KEYS_JSON={} for DB-only production auth" >&2
  exit 1
fi

master_key="$(env_value FAIM_MASTER_KEY)"
if [[ ! "$master_key" =~ ^[0-9a-fA-F]{64}$ ]]; then
  echo "$ENV_FILE FAIM_MASTER_KEY must contain exactly 64 hexadecimal characters" >&2
  exit 1
fi

cd "$PROJECT_ROOT"
chmod 600 "$ENV_FILE"

COMPOSE=(
  docker compose
  --env-file "$ENV_FILE"
  -f docker-compose.yml
  -f docker-compose.vps.yml
  -f docker-compose.registry.yml
  --profile accel
)

if [[ "${1:-}" == "--preflight-only" ]]; then
  echo "Validating production Compose configuration only..."
  "${COMPOSE[@]}" config --quiet
  echo "Production VPS preflight passed for image tag $FAIM_IMAGE_TAG"
  exit 0
fi

echo "Starting infrastructure without stopping existing services..."
"${COMPOSE[@]}" up -d --wait postgres redis qdrant

echo "Pulling immutable application images: $FAIM_IMAGE_TAG"
"${COMPOSE[@]}" pull migrate api worker frontend

echo "Applying migrations..."
"${COMPOSE[@]}" run --rm migrate

# A bootstrap payload is intentionally accepted only from the explicit,
# short-lived env-file line. The backend image hashes it with Argon2id and the
# line is removed only after the transaction succeeds. Never echo this value.
if [[ -n "$(env_value FAIM_TENANT_KEY_BOOTSTRAP_JSON)" ]]; then
  echo "Bootstrapping tenant API keys into the authentication database..."
  "${COMPOSE[@]}" run --rm --no-deps migrate \
    /app/scripts/bootstrap_tenant_api_keys.py --apply

  remove_bootstrap_env_line
  echo "Tenant API-key bootstrap completed; temporary bootstrap input removed."
fi

echo "Updating application services without compose down..."
"${COMPOSE[@]}" up -d --wait --remove-orphans --no-deps api worker frontend

echo "Ensuring the reverse proxy is running..."
"${COMPOSE[@]}" up -d --wait --no-deps caddy

echo "Running public smoke checks..."
"$SCRIPT_DIR/vps_smoke.sh" https://faimatrix.com

# Do not run global Docker prune commands here.  A deployment must not remove
# unrelated containers, images, or build caches owned by other services on the
# VPS.  Image/volume retention is an operator-controlled maintenance task.
echo "Leaving unrelated Docker resources untouched."

echo "VPS deployment completed for $FAIM_IMAGE_PREFIX:$FAIM_IMAGE_TAG"
