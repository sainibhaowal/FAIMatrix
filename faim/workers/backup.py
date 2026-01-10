"""FAIM Database Backup Module.

Backups are saved locally to /tmp/faim/backups/ (Docker volume).
S3/MinIO upload removed - use Docker volumes or external backup solutions.
"""

import datetime
import os
import subprocess
from pathlib import Path

# Database URL from environment
DB_URL = os.getenv("FAIM_DB_URL") or os.getenv("DATABASE_URL")

# Local backup directory
BACKUP_DIR = Path("/tmp/faim/backups")  # nosec B108


def perform_backup():
    """Perform a database backup and save locally.

    Returns:
        dict with 'status', 'backup_file', and 'message' keys
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"backup_faim_{ts}.sql"
    result = {"status": "error", "backup_file": None, "message": ""}

    if not DB_URL:
        result["message"] = "FAIM_DB_URL or DATABASE_URL not configured"
        return result

    # Dump Database
    print(f"Dumping database to {backup_file}...")
    cmd_list = ["pg_dump", str(DB_URL), "-f", str(backup_file)]

    try:
        subprocess.check_call(cmd_list)
        print(f"Backup saved to {backup_file}")
        result["status"] = "success"
        result["backup_file"] = str(backup_file)
        result["message"] = "Backup completed successfully"
    except subprocess.CalledProcessError as e:
        result["message"] = f"pg_dump failed: {e}"
        print(f"Backup failed: {e}")

    return result


def list_backups():
    """List available backup files."""
    if not BACKUP_DIR.exists():
        return []
    return sorted(BACKUP_DIR.glob("backup_faim_*.sql"), reverse=True)


def cleanup_old_backups(keep: int = 7):
    """Delete old backups, keeping the most recent 'keep' files."""
    backups = list_backups()
    for old in backups[keep:]:
        try:
            old.unlink()
            print(f"Deleted old backup: {old}")
        except Exception as e:
            print(f"Failed to delete {old}: {e}")


if __name__ == "__main__":
    perform_backup()
