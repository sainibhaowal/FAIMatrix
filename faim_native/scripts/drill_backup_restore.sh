#!/bin/bash
# drill_backup_restore.sh - Prove recoverability of FAIM-Native data.
#
# Usage:
#   cd /home/sephi-asi/FAIM/faim/Faim_Native
#   ./scripts/drill_backup_restore.sh
#
# Requirements:
#   - pg_dump / psql installed
#   - DATABASE_URL environment variable set
#   - Postgres permissions to create databases

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
DRILL_DB_NAME="faim_drill"
DUMP_FILE="faim_backup_drill.sql"
LOG_DIR="Runtime/Logs"
LOG_FILE="$LOG_DIR/drill_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOG_DIR"

echo "============================================" | tee -a "$LOG_FILE"
echo "FAIM-Native Backup/Restore Drill" | tee -a "$LOG_FILE"
echo "============================================" | tee -a "$LOG_FILE"

# 1. Parsing DATABASE_URL to get parameters
# We use psql to perform DB creation/deletion to ensure we use the same connection logic.
PARENT_URL=$(echo "$DATABASE_URL" | sed 's/\/[^\/]*$//')

echo "Source DB: $DATABASE_URL" | tee -a "$LOG_FILE"
echo "Drill DB Name:  $DRILL_DB_NAME" | tee -a "$LOG_FILE"

# 2. pg_dump (Data & Schema)
echo "" | tee -a "$LOG_FILE"
echo "[1/4] Dumping source database..." | tee -a "$LOG_FILE"

if [ "$USE_DOCKER_DUMP" = "true" ]; then
    echo "Using Docker exec for pg_dump (Container: $DOCKER_CONTAINER, User: faim)" | tee -a "$LOG_FILE"
    set +e
    docker exec -e PGPASSWORD="$PGPASSWORD" -u root "$DOCKER_CONTAINER" pg_dump -U faim -d faim_native -O -x > "$DUMP_FILE" 2> /tmp/pg_dump_err.log
    DUMP_EXIT_CODE=$?
    set -e
    
    if [ $DUMP_EXIT_CODE -ne 0 ]; then
        echo "❌ docker exec pg_dump failed. Error:" | tee -a "$LOG_FILE"
        cat /tmp/pg_dump_err.log | tee -a "$LOG_FILE"
        exit 1
    fi
else
    pg_dump "$DATABASE_URL" -O -x -f "$DUMP_FILE" 2>> "$LOG_FILE"
fi

echo "Dump complete. File size: $(du -h "$DUMP_FILE" | cut -f1)" | tee -a "$LOG_FILE"

if [ $? -ne 0 ] || [ ! -s "$DUMP_FILE" ]; then
    echo "⚠️ pg_dump reported an error or produced an empty file (possibly version mismatch)." | tee -a "$LOG_FILE"
    if [ ! -s "$DUMP_FILE" ]; then
        echo "❌ Critical: Dump file is empty. Aborting." | tee -a "$LOG_FILE"
        exit 1
    fi
fi

# 3. Create drill DB
# Using psql to run administrative commands against the server
echo "" | tee -a "$LOG_FILE"
echo "[2/4] Recreating drill database ($DRILL_DB_NAME)..." | tee -a "$LOG_FILE"
# We connect to 'postgres' DB on the same server to run DROP/CREATE
psql "$PARENT_URL/postgres" -c "DROP DATABASE IF EXISTS $DRILL_DB_NAME WITH (FORCE);" 2>&1 | tee -a "$LOG_FILE"
psql "$PARENT_URL/postgres" -c "CREATE DATABASE $DRILL_DB_NAME;" 2>&1 | tee -a "$LOG_FILE"

# 4. Restore
echo "" | tee -a "$LOG_FILE"
echo "[3/4] Restoring dump to drill database..." | tee -a "$LOG_FILE"
DRILL_DB_URL="$PARENT_URL/$DRILL_DB_NAME"
psql "$DRILL_DB_URL" -f "$DUMP_FILE" > /dev/null 2>&1

# 5. Verify against drill DB
echo "" | tee -a "$LOG_FILE"
echo "[4/4] Running verification suite against restored database..." | tee -a "$LOG_FILE"
# We run verify.sh from its own directory to avoid path issues
DATABASE_URL="$DRILL_DB_URL" bash "$SCRIPT_DIR/verify.sh" --tb=no --quiet 2>&1 | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "============================================" | tee -a "$LOG_FILE"
echo "✓ DRILL COMPLETE" | tee -a "$LOG_FILE"
echo "Log saved to: $LOG_FILE" | tee -a "$LOG_FILE"
echo "============================================" | tee -a "$LOG_FILE"

# Cleanup
rm "$DUMP_FILE"
