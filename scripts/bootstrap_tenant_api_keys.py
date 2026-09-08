#!/usr/bin/env python3
"""Import explicitly supplied tenant API keys into the FAIM auth database.

This command is intentionally manual and dry-run by default.  It accepts only
``FAIM_TENANT_KEY_BOOTSTRAP_JSON`` and never falls back to ``TENANT_KEYS_JSON``.
See ``docs/PRODUCTION_HARDENING.md`` for the one-time operational procedure.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NATIVE_ROOT = PROJECT_ROOT / "faim_native"
if str(NATIVE_ROOT) not in sys.path:
    sys.path.insert(0, str(NATIVE_ROOT))

from runtime.api_key_bootstrap import (  # noqa: E402
    BootstrapValidationError,
    bootstrap_from_environment,
)
from runtime.context import close_session, get_session  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run or import a one-time tenant API-key bootstrap payload into "
            "the FAIM database. Plaintext keys are never printed."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="commit missing keys as Argon2id hashes (default: dry-run)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    # Do not allow the context helper's local SQLite fallback. A real target DB
    # must be selected deliberately before a production credential bootstrap.
    if not str(os.getenv("DATABASE_URL", "")).strip():
        print("Bootstrap refused: DATABASE_URL must be set", file=sys.stderr)
        return 2

    session = None
    try:
        session = get_session()
        result = bootstrap_from_environment(session, apply=bool(args.apply))
        if args.apply:
            session.commit()
            print(
                "Tenant API-key bootstrap complete: "
                f"requested={result.requested} imported={result.imported} "
                f"already_present={result.already_present}"
            )
        else:
            # Read-only planning still opens a transaction on PostgreSQL and
            # may hold an advisory lock. Release it deterministically.
            session.rollback()
            print(
                "Tenant API-key bootstrap dry-run: "
                f"requested={result.requested} would_import={result.would_import} "
                f"already_present={result.already_present}. "
                "Re-run with --apply to commit."
            )
        return 0
    except BootstrapValidationError as exc:
        if session is not None:
            session.rollback()
        # BootstrapValidationError messages are designed not to contain input
        # values. Never print the original exception for arbitrary DB errors.
        print(f"Bootstrap refused: {exc}", file=sys.stderr)
        return 2
    except Exception:
        if session is not None:
            session.rollback()
        print(
            "Bootstrap failed; no tenant API-key changes were committed.",
            file=sys.stderr,
        )
        return 1
    finally:
        close_session(session)


if __name__ == "__main__":
    raise SystemExit(main())
