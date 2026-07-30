"""FAIM-Native Migration Engine.

CLI for applying and tracking schema migrations with checksum protection.
"""

from __future__ import annotations

import argparse
import hashlib
import re
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


def split_sql_statements(sql_content: str) -> List[str]:
    """Split SQL script into statements without breaking on quoted semicolons or dollar quotes.

    Handles:
    - single quoted strings with escaped quotes ('')
    - double quoted identifiers
    - line comments (-- ...)
    - block comments (/* ... */)
    - dollar quoted strings ($tag$ ... $tag$)
    """
    statements: List[str] = []
    buf: List[str] = []

    in_single = False
    in_double = False
    in_line_comment = False
    in_block_comment = False
    in_dollar = False
    dollar_tag = ""

    i = 0
    n = len(sql_content)
    while i < n:
        ch = sql_content[i]
        nxt = sql_content[i + 1] if i + 1 < n else ""

        if in_line_comment:
            buf.append(ch)
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            buf.append(ch)
            if ch == "*" and nxt == "/":
                buf.append(nxt)
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if in_dollar:
            buf.append(ch)
            if ch == "$" and sql_content[i:].startswith(dollar_tag):
                buf.append(dollar_tag[1:])
                i += len(dollar_tag)
                in_dollar = False
                dollar_tag = ""
            else:
                i += 1
            continue

        if not in_single and not in_double:
            if ch == "-" and nxt == "-":
                buf.append(ch)
                buf.append(nxt)
                in_line_comment = True
                i += 2
                continue
            if ch == "/" and nxt == "*":
                buf.append(ch)
                buf.append(nxt)
                in_block_comment = True
                i += 2
                continue
            if ch == "$":
                match = re.match(r"^\$[A-Za-z0-9_]*\$", sql_content[i:])
                if match:
                    dollar_tag = match.group(0)
                    in_dollar = True
                    buf.append(dollar_tag)
                    i += len(dollar_tag)
                    continue

        if ch == "'" and not in_double:
            buf.append(ch)
            if in_single and nxt == "'":
                buf.append(nxt)
                i += 2
                continue
            in_single = not in_single
            i += 1
            continue

        if ch == '"' and not in_single:
            in_double = not in_double
            buf.append(ch)
            i += 1
            continue

        if ch == ";" and not in_single and not in_double:
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)

    return statements


def get_file_checksum(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def _sqlite_rewrite_sql_content(sql_content: str) -> str:
    """Rewrite Postgres-oriented migration SQL into SQLite-compatible SQL."""
    rewritten = sql_content
    rewritten = re.sub(
        r"(?i)\bSERIAL\s+PRIMARY\s+KEY\b", "INTEGER PRIMARY KEY", rewritten
    )
    rewritten = rewritten.replace("AUTOINCREMENT", "")
    rewritten = re.sub(r"(?i)\bTIMESTAMPTZ\b", "TIMESTAMP", rewritten)
    rewritten = re.sub(r"(?i)\bJSONB\b", "JSON", rewritten)
    rewritten = re.sub(r"(?i)::jsonb", "", rewritten)
    rewritten = re.sub(r"::[A-Za-z_][A-Za-z0-9_]*", "", rewritten)
    rewritten = re.sub(r"(?i)\bNOW\(\)", "CURRENT_TIMESTAMP", rewritten)
    rewritten = re.sub(r"(?i)\s+DEFAULT\s+gen_random_uuid\(\)", "", rewritten)
    rewritten = re.sub(r"(?i)\bUSING\s+GIN\s*\(", "(", rewritten)
    rewritten = re.sub(r"(?i)\s+jsonb_path_ops\b", "", rewritten)
    # Ignore pgvector specific statements
    rewritten = re.sub(r"(?i)CREATE EXTENSION.*?;", "", rewritten)
    rewritten = re.sub(r"(?i)vector\(\d+\)", "JSON", rewritten)
    rewritten = re.sub(r"(?i)CREATE INDEX.*?USING hnsw.*?;", "", rewritten)
    rewritten = re.sub(r"(?i)CREATE OR REPLACE FUNCTION.*?\$\$ LANGUAGE plpgsql;", "", rewritten, flags=re.DOTALL)
    rewritten = re.sub(r"(?i)DROP TRIGGER.*?;\s*CREATE TRIGGER.*?EXECUTE FUNCTION.*?;", "", rewritten, flags=re.DOTALL)
    return rewritten


def _sqlite_expand_alter_add_column(statement: str) -> List[str]:
    """Expand Postgres multi-add ALTER TABLE into SQLite one-column statements."""
    match = re.match(
        r"(?is)^ALTER\s+TABLE\s+([A-Za-z0-9_\".]+)\s+(.*)$", statement.strip()
    )
    if not match:
        return [statement]

    table_name = match.group(1)
    body = match.group(2).strip()
    if "ADD COLUMN" not in body.upper():
        return [statement]

    chunks = re.split(r"(?is),\s*ADD\s+COLUMN\s+", body)
    expanded: List[str] = []
    for idx, chunk in enumerate(chunks):
        part = chunk.strip()
        if not part:
            continue
        if idx == 0:
            part = re.sub(r"(?is)^ADD\s+COLUMN\s+", "", part).strip()
        part = re.sub(r"(?is)^IF\s+NOT\s+EXISTS\s+", "", part).strip()
        if not part:
            continue
        expanded.append(f"ALTER TABLE {table_name} ADD COLUMN {part}")
    return expanded or [statement]


def _sqlite_compatible_statements(statement: str) -> List[str]:
    """Return zero or more SQLite-compatible statements for a migration statement."""
    stmt = statement.strip()
    if not stmt:
        return []

    non_comment_lines = [
        line for line in stmt.splitlines() if not line.strip().startswith("--")
    ]
    content = "\n".join(non_comment_lines).strip()
    if not content:
        return []

    if re.match(r"(?is)^COMMENT\s+ON\s+", content):
        return []
    if "alter column" in content.lower():
        return []
    return _sqlite_expand_alter_add_column(content)


def _sqlite_should_ignore_error(exc: Exception, statement: str) -> bool:
    """Best-effort filter for benign SQLite migration idempotency errors."""
    msg = str(exc).lower()
    stmt = statement.lower()
    if "duplicate column name" in msg and "alter table" in stmt:
        return True
    if "already exists" in msg and ("create index" in stmt or "create table" in stmt):
        return True
    return False


def ensure_migrations_table(session: Session):
    """Ensure the schema_migrations table exists."""
    # Use cross-dialect compatible SQL
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            checksum TEXT NOT NULL
        )
    """))
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
        print(
            f"\nERROR: {pending_count} pending migration(s). Run 'python -m store.pg.migrate up' first."
        )
        sys.exit(1)


def run_up(require_latest: bool = False):
    """Apply pending migrations.

    Args:
        require_latest: If True, do not apply migrations; only exit with code 1 if any are pending.
    """
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

    # If require_latest is set, we fail here instead of applying
    if require_latest:
        print(
            f"\nERROR: {len(to_apply)} pending migration(s). Refusing to start because --require-latest is set."
        )
        session.close()
        sys.exit(1)

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

            is_sqlite = session.bind.dialect.name == "sqlite"
            if is_sqlite:
                sql_content = _sqlite_rewrite_sql_content(sql_content)

            statements = split_sql_statements(sql_content)

            for raw_stmt in statements:
                stmt_candidates = (
                    _sqlite_compatible_statements(raw_stmt) if is_sqlite else [raw_stmt]
                )
                for stmt in stmt_candidates:
                    stmt = stmt.strip()
                    if not stmt:
                        continue

                    # Verify statement has actual content (not just comments)
                    lines = [
                        line
                        for line in stmt.split("\n")
                        if not line.strip().startswith("--")
                    ]
                    if not "".join(lines).strip():
                        continue

                    try:
                        # Use savepoint so ignorable SQLite statement errors
                        # (e.g., duplicate column/index) do not abort migration tx.
                        with session.begin_nested():
                            session.execute(text(stmt))
                    except Exception as exc:
                        if is_sqlite and _sqlite_should_ignore_error(exc, stmt):
                            continue
                        raise

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
    up_parser = subparsers.add_parser("up", help="Apply pending migrations")
    up_parser.add_argument(
        "--require-latest",
        action="store_true",
        help="Exit with code 1 if any migrations are pending (for entrypoint gating)",
    )

    args = parser.parse_args()

    if args.command == "status":
        run_status(require_latest=args.require_latest)
    elif args.command == "up":
        run_up(require_latest=args.require_latest)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
