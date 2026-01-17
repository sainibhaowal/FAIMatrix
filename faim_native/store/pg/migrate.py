"""FAIM-Native Migration Engine.

CLI for applying and tracking schema migrations with checksum protection.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import List, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

# Flexible imports
_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from store.pg.session import get_session  # noqa: E402

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_file_checksum(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def ensure_migrations_table(session: Session):
    """Ensure the schema_migrations table exists."""
    # Use cross-dialect compatible SQL
    session.execute(
        text(
            """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            checksum TEXT NOT NULL
        )
    """
        )
    )
    session.commit()


def get_applied_migrations(session: Session) -> List[Tuple[int, str]]:
    """Get list of applied migration versions and checksums."""
    result = session.execute(
        text("SELECT version, checksum FROM schema_migrations ORDER BY version ASC")
    )
    return [(row[0], row[1]) for row in result]


def get_latest_applied_version(session: Session) -> int:
    """Get the latest applied migration version."""
    ensure_migrations_table(session)
    result = session.execute(text("SELECT MAX(version) FROM schema_migrations"))
    row = result.fetchone()
    return row[0] if row and row[0] is not None else 0


def get_latest_local_version() -> int:
    """Get the latest version number from local migration files."""
    files = list(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        return 0
    versions = []
    for f in files:
        try:
            versions.append(int(f.name.split("_")[0]))
        except ValueError:
            continue
    return max(versions) if versions else 0


def run_status(require_latest: bool = False):
    """Show the status of migrations.

    Args:
        require_latest: If True, exit with code 1 if any migrations are pending.
    """
    session = get_session()
    ensure_migrations_table(session)

    applied = get_applied_migrations(session)
    applied_map = {v: c for v, c in applied}

    files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    pending_count = 0

    print(f"{'Version':<10} {'Filename':<35} {'Status':<10} {'Checksum Match':<15}")
    print("-" * 75)

    for f in files:
        # Expected version from filename (e.g., 0001_initial.sql -> 1)
        try:
            version = int(f.name.split("_")[0])
        except ValueError:
            print(f"Warning: Invalid migration filename: {f.name}")
            continue

        status = "PENDING"
        checksum_match = "N/A"

        if version in applied_map:
            status = "APPLIED"
            current_checksum = get_file_checksum(f)
            if applied_map[version] == current_checksum:
                checksum_match = "OK"
            else:
                checksum_match = "MISMATCH!"
        else:
            pending_count += 1

        print(f"{version:<10} {f.name:<35} {status:<10} {checksum_match:<15}")

    session.close()

    if require_latest and pending_count > 0:
        print(f"\nERROR: {pending_count} pending migration(s). Run 'python -m store.pg.migrate up' first.")
        sys.exit(1)


def run_up():
    """Apply pending migrations."""
    session = get_session()
    ensure_migrations_table(session)

    applied = get_applied_migrations(session)
    applied_map = {v: c for v, c in applied}

    files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    to_apply = []

    # 1. Verification Phase: Check all applied migrations against local files
    for f in files:
        try:
            version = int(f.name.split("_")[0])
        except ValueError:
            continue

        current_checksum = get_file_checksum(f)

        if version in applied_map:
            if applied_map[version] != current_checksum:
                print(f"CRITICAL ERROR: Migration {f.name} checksum mismatch!")
                print(f"Stored: {applied_map[version]}")
                print(f"Local:  {current_checksum}")
                print("ABORTING to prevent schema corruption.")
                session.close()
                sys.exit(1)
        else:
            to_apply.append((version, f, current_checksum))

    if not to_apply:
        print("Schema is up to date.")
        session.close()
        return

    # 2. Locking Phase: Use Postgres advisory lock to prevent races
    lock_acquired = False
    is_postgres = session.bind.dialect.name == "postgresql"
    FAIM_LOCK_ID = 0xFA141  # "FAIM" in hex-ish

    if is_postgres:
        print("Acquiring migration lock...", end="", flush=True)
        try:
            # pg_advisory_lock(key) blocks until lock is acquired
            session.execute(text(f"SELECT pg_advisory_lock({FAIM_LOCK_ID})"))
            lock_acquired = True
            print(" OK")

            # Re-check applied migrations after acquiring lock to see if another instance finished
            applied = get_applied_migrations(session)
            applied_map = {v: c for v, c in applied}
            to_apply = [v for v in to_apply if v[0] not in applied_map]

            if not to_apply:
                print(
                    "Schema was updated by another instance. Releasing lock & exiting."
                )
                session.execute(text(f"SELECT pg_advisory_unlock({FAIM_LOCK_ID})"))
                session.close()
                return
        except Exception as e:
            print(f" FAILED to acquire advisory lock: {e}")
            session.close()
            sys.exit(1)

    # 3. Application Phase: Run pending migrations in order
    try:
        for version, f, checksum in to_apply:
            print(f"Applying migration {version}: {f.name}...", end="", flush=True)

            with open(f, "r") as sql_file:
                sql_content = sql_file.read()

            # Dialect Polyfill:
            # Postgres (Production) uses SERIAL for auto-increment.
            # SQLite (Test) uses INTEGER PRIMARY KEY for the same behavior.
            if session.bind.dialect.name == "sqlite":
                sql_content = sql_content.replace(
                    "SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY"
                )
                sql_content = sql_content.replace(
                    "AUTOINCREMENT", ""
                )  # Remove if present

            statements = sql_content.split(";")

            for stmt in statements:
                stmt = stmt.strip()
                if not stmt:
                    continue
                session.execute(text(stmt))

            session.execute(
                text(
                    "INSERT INTO schema_migrations (version, checksum) VALUES (:v, :c)"
                ),
                {"v": version, "c": checksum},
            )
            session.commit()
            print(" DONE")
    except Exception as e:
        session.rollback()
        print(f" FAILED: {e}")
        print("ABORTING.")
        if is_postgres and lock_acquired:
            session.execute(text(f"SELECT pg_advisory_unlock({FAIM_LOCK_ID})"))
        session.close()
        sys.exit(1)
    finally:
        if is_postgres and lock_acquired:
            session.execute(text(f"SELECT pg_advisory_unlock({FAIM_LOCK_ID})"))

    print(f"Successfully applied {len(to_apply)} migrations.")
    session.close()


def main():
    parser = argparse.ArgumentParser(description="FAIM-Native Migration Engine")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    status_parser = subparsers.add_parser("status", help="Show migration status")
    status_parser.add_argument(
        "--require-latest",
        action="store_true",
        help="Exit with code 1 if any migrations are pending (for entrypoint gating)",
    )
    subparsers.add_parser("up", help="Apply pending migrations")

    args = parser.parse_args()

    if args.command == "status":
        run_status(require_latest=args.require_latest)
    elif args.command == "up":
        run_up()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
