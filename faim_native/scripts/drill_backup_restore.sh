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

# Configuration
DRILL_DB_NAME="faim_drill"
DUMP_FILE="faim_backup_drill.sql"
LOG_DIR="Runtime/Logs"
LOG_FILE="$LOG_DIR/drill_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOG_DIR"

echo "============================================" | tee -a "$LOG_FILE"
echo "FAIM-Native Backup/Restore Drill" | tee -a "$LOG_FILE"
echo "============================================" | tee -a "$LOG_FILE"

# 1. Parsing DATABASE_URL to get host/user
# Default: postgresql://postgres:postgres@localhost:5432/faim_native
DB_URL_BASE=$(echo "$DATABASE_URL" | sed 's/\/[^\/]*$//')
DRILL_DB_URL="$DB_URL_BASE/$DRILL_DB_NAME"

echo "Source DB: $DATABASE_URL" | tee -a "$LOG_FILE"
echo "Drill DB:  $DRILL_DB_URL" | tee -a "$LOG_FILE"

# 2. pg_dump (Data & Schema)
echo "" | tee -a "$LOG_FILE"
echo "[1/4] Dumping source database..." | tee -a "$LOG_FILE"
pg_dump "$DATABASE_URL" -O -x -f "$DUMP_FILE" 2>&1 | tee -a "$LOG_FILE"

# 3. Create drill DB
echo "" | tee -a "$LOG_FILE"
echo "[2/4] Recreating drill database ($DRILL_DB_NAME)..." | tee -a "$LOG_FILE"
dropdb --if-exists "$DRILL_DB_NAME" 2>&1 | tee -a "$LOG_FILE"
createdb "$DRILL_DB_NAME" 2>&1 | tee -a "$LOG_FILE"

# 4. Restore
echo "" | tee -a "$LOG_FILE"
echo "[3/4] Restoring dump to drill database..." | tee -a "$LOG_FILE"
psql "$DRILL_DB_URL" -f "$DUMP_FILE" > /dev/null 2>&1

# 5. Verify against drill DB
echo "" | tee -a "$LOG_FILE"
echo "[4/4] Running verification suite against restored database..." | tee -a "$LOG_FILE"
DATABASE_URL="$DRILL_DB_URL" ./scripts/verify.sh --tb=no --quiet 2>&1 | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "============================================" | tee -a "$LOG_FILE"
echo "✓ DRILL COMPLETE" | tee -a "$LOG_FILE"
echo "Log saved to: $LOG_FILE" | tee -a "$LOG_FILE"
echo "============================================" | tee -a "$LOG_FILE"

# Cleanup
rm "$DUMP_FILE"
