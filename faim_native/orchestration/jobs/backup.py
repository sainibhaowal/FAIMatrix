"""FAIM Database Backup Module.

Uses pg_dump with proper command format:
  pg_dump --dbname=<DB_URL> --file=<backup_file>

Features:
- Retention policy (keep N most recent)
- Optional gzip compression
- Safe subprocess execution (no shell)
- Backup timestamp NEVER enters FAIM hashes (operational only)
"""

from __future__ import annotations

import datetime
import gzip
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

# Database URL from environment
DB_URL = os.getenv("FAIM_DB_URL") or os.getenv("DATABASE_URL")

# Local backup directory
BACKUP_DIR = Path(os.getenv("FAIM_BACKUP_DIR", "/tmp/faim/backups"))  # nosec B108


# =============================================================================
# Backup Functions
# =============================================================================


def build_backup_command(
    db_url: str,
    backup_file: Path,
    *,
    extra_args: Optional[List[str]] = None,
) -> List[str]:
    """Build pg_dump command list (no shell execution).

    Uses --dbname= and --file= format for safety.

    Args:
        db_url: PostgreSQL connection URL.
        backup_file: Output file path.
        extra_args: Additional pg_dump arguments.

    Returns:
        Command list suitable for subprocess.run().
    """
    cmd = [
        "pg_dump",
        f"--dbname={db_url}",
        f"--file={backup_file}",
    ]

    if extra_args:
        cmd.extend(extra_args)

    return cmd


def perform_backup(
    *,
    compress: bool = False,
    db_url: Optional[str] = None,
    backup_dir: Optional[Path] = None,
) -> Dict[str, Optional[str]]:
    """Perform a database backup and save locally.

    Args:
        compress: If True, gzip the backup file.
        db_url: Database URL (defaults to env var).
        backup_dir: Backup directory (defaults to BACKUP_DIR).

    Returns:
        Dict with 'status', 'backup_file', and 'message' keys.

    Note:
        Backup timestamp is operational only and NEVER enters FAIM hashes.
    """
    target_dir = backup_dir or BACKUP_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    url = db_url or DB_URL
    result: Dict[str, Optional[str]] = {
        "status": "error",
        "backup_file": None,
        "message": "",
    }

    if not url:
        result["message"] = "FAIM_DB_URL or DATABASE_URL not configured"
        return result

    # Generate filename with timestamp (operational, not in hashes)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = target_dir / f"backup_faim_{ts}.sql"

    # Build command with safe format
    cmd = build_backup_command(url, backup_file)

    print(f"Dumping database to {backup_file}...")

    try:
        # Use list form (no shell=True for safety)
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Backup saved to {backup_file}")

        # Optionally compress
        if compress and backup_file.exists():
            compressed_file = backup_file.with_suffix(".sql.gz")
            with open(backup_file, "rb") as f_in:
                with gzip.open(compressed_file, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            backup_file.unlink()  # Remove uncompressed
            backup_file = compressed_file
            print(f"Compressed to {compressed_file}")

        result["status"] = "success"
        result["backup_file"] = str(backup_file)
        result["message"] = "Backup completed successfully"

    except subprocess.CalledProcessError as e:
        result["message"] = f"pg_dump failed: {e.stderr or e}"
        print(f"Backup failed: {e}")
    except Exception as e:
        result["message"] = f"Backup error: {e}"
        print(f"Backup error: {e}")

    return result


def list_backups(backup_dir: Optional[Path] = None) -> List[Path]:
    """List available backup files, newest first.

    Args:
        backup_dir: Backup directory (defaults to BACKUP_DIR).

    Returns:
        List of backup file paths, sorted by modification time (newest first).
    """
    target_dir = backup_dir or BACKUP_DIR

    if not target_dir.exists():
        return []

    # Include both .sql and .sql.gz files
    sql_files = list(target_dir.glob("backup_faim_*.sql"))
    gz_files = list(target_dir.glob("backup_faim_*.sql.gz"))

    all_files = sql_files + gz_files

    # Sort by modification time, newest first
    return sorted(all_files, key=lambda p: p.stat().st_mtime, reverse=True)


def cleanup_old_backups(
    keep: int = 7,
    backup_dir: Optional[Path] = None,
) -> List[Path]:
    """Delete old backups, keeping the most recent 'keep' files.

    Args:
        keep: Number of recent backups to keep.
        backup_dir: Backup directory (defaults to BACKUP_DIR).

    Returns:
        List of deleted file paths.
    """
    backups = list_backups(backup_dir)
    deleted: List[Path] = []

    for old in backups[keep:]:
        try:
            old.unlink()
            print(f"Deleted old backup: {old}")
            deleted.append(old)
        except Exception as e:
            print(f"Failed to delete {old}: {e}")

    return deleted


def get_latest_backup(backup_dir: Optional[Path] = None) -> Optional[Path]:
    """Get the most recent backup file.

    Args:
        backup_dir: Backup directory (defaults to BACKUP_DIR).

    Returns:
        Path to the most recent backup, or None if no backups exist.
    """
    backups = list_backups(backup_dir)
    return backups[0] if backups else None


# =============================================================================
# CLI Entry Point
# =============================================================================


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FAIM Database Backup")
    parser.add_argument("--compress", action="store_true", help="Gzip compress backup")
    parser.add_argument("--keep", type=int, default=7, help="Number of backups to keep")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old backups")

    args = parser.parse_args()

    if args.cleanup:
        cleanup_old_backups(keep=args.keep)
    else:
        result = perform_backup(compress=args.compress)
        print(f"Result: {result}")
        if args.keep > 0:
            cleanup_old_backups(keep=args.keep)
