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

echo "Starting infrastructure without stopping existing services..."
"${COMPOSE[@]}" up -d --wait postgres redis qdrant

echo "Pulling immutable application images: $FAIM_IMAGE_TAG"
"${COMPOSE[@]}" pull migrate api worker frontend

echo "Applying migrations..."
"${COMPOSE[@]}" run --rm migrate

echo "Updating application services without compose down..."
"${COMPOSE[@]}" up -d --wait --remove-orphans --no-deps api worker frontend

echo "Ensuring the reverse proxy is running..."
"${COMPOSE[@]}" up -d --wait --no-deps caddy

echo "Running public smoke checks..."
"$SCRIPT_DIR/vps_smoke.sh" https://faimatrix.com

echo "Pruning unused Docker resources (volumes are intentionally excluded)..."
docker container prune -f
docker image prune -af
docker builder prune -af
# Docker system prune does not remove volumes unless --volumes is supplied.
docker system prune -af

echo "VPS deployment completed for $FAIM_IMAGE_PREFIX:$FAIM_IMAGE_TAG"
