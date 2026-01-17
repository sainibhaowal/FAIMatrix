#!/usr/bin/env bash
# =============================================================================
# FAIM-Native CI with Postgres (Production-Grade Release Gate)
# =============================================================================
# This script validates the full production stack:
#   1. Start Postgres container
#   2. Run migrations
#   3. Run verification tests
#   4. Run backup drill (Postgres only)
#
# Usage: ./scripts/ci_postgres.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FAIM_NATIVE_DIR="$PROJECT_ROOT/faim_native"

echo "============================================"
echo "FAIM-Native CI Pipeline (Postgres)"
echo "============================================"
echo ""

# ---------------------------------------------------------------------------
# 1. Start Postgres Container
# ---------------------------------------------------------------------------
echo "🐘 Starting Postgres container..."

POSTGRES_CONTAINER="faim-ci-postgres"
POSTGRES_PASSWORD="ci_test_password"

# Cleanup any previous container
docker rm -f "$POSTGRES_CONTAINER" 2>/dev/null || true

docker run -d \
    --name "$POSTGRES_CONTAINER" \
    -e POSTGRES_USER=faim \
    -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
    -e POSTGRES_DB=faim_native \
    -p 5433:5432 \
    postgres:15

# Wait for Postgres to be ready
echo "Waiting for Postgres to be ready..."
for i in {1..30}; do
    if docker exec "$POSTGRES_CONTAINER" pg_isready -U faim -d faim_native >/dev/null 2>&1; then
        echo "✅ Postgres is ready"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "❌ Postgres failed to start"
        docker logs "$POSTGRES_CONTAINER"
        docker rm -f "$POSTGRES_CONTAINER"
        exit 1
    fi
    sleep 1
done

# Export DATABASE_URL for tests
export DATABASE_URL="postgresql://faim:${POSTGRES_PASSWORD}@localhost:5433/faim_native"

# ---------------------------------------------------------------------------
# 2. Run Migrations
# ---------------------------------------------------------------------------
echo ""
echo "🗄️ Running migrations..."
cd "$FAIM_NATIVE_DIR"
python3 -m store.pg.migrate up

# ---------------------------------------------------------------------------
# 3. Run Verification Tests
# ---------------------------------------------------------------------------
echo ""
echo "🧪 Running verification tests..."
if [ -f "$FAIM_NATIVE_DIR/scripts/verify.sh" ]; then
    bash "$FAIM_NATIVE_DIR/scripts/verify.sh"
else
    pytest --tb=short -q
fi

# ---------------------------------------------------------------------------
# 4. Run Backup Drill (Postgres Only)
# We override pg_dump to use the one inside the container to avoid version mismatch
echo ""
echo "💾 Running backup drill..."
if [ -f "$FAIM_NATIVE_DIR/scripts/drill_backup_restore.sh" ]; then
    export USE_DOCKER_DUMP="true"
    export DOCKER_CONTAINER="$POSTGRES_CONTAINER"
    export PGPASSWORD="ci_test_password"
    bash "$FAIM_NATIVE_DIR/scripts/drill_backup_restore.sh"
    unset USE_DOCKER_DUMP DOCKER_CONTAINER PGPASSWORD
else
    echo "⚠️ Backup drill script not found, skipping..."
fi

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
echo ""
echo "🧹 Cleaning up..."
docker rm -f "$POSTGRES_CONTAINER"

echo ""
echo "============================================"
echo "✅ FAIM-Native CI Pipeline PASSED"
echo "============================================"
