#!/usr/bin/env python3
"""Raw verify script - Load a blob and verify its SHA256 matches.

Usage:
    python raw_verify.py <raw_id or sha256> [--blob-dir BLOB_DIR]

Example:
    python raw_verify.py abc123...  # Using SHA256
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from uuid import UUID

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from faim.Faim_Native.core.contracts.types import compute_sha256
from faim.Faim_Native.store.pg.models_faim import create_all_tables
from faim.Faim_Native.store.pg.repos.raw_repo import RawRepo
from faim.Faim_Native.store.pg.session import SessionFactory
from faim.Faim_Native.store.raw.raw_store import BlobNotFoundError, RawStore


def main():
    parser = argparse.ArgumentParser(
        description="Verify a raw blob's SHA256 hash matches."
    )
    parser.add_argument("identifier", type=str, help="Raw ID (UUID) or SHA256 hash")
    parser.add_argument(
        "--blob-dir",
        type=Path,
        default=Path("/tmp/faim_blobs"),
        help="Directory for blob storage",
    )
    parser.add_argument("--db-url", type=str, default=None, help="Database URL")
    args = parser.parse_args()

    # Initialize stores
    raw_store = RawStore(args.blob_dir)
    session_factory = SessionFactory(args.db_url)
    create_all_tables(session_factory.engine)

    raw_repo = RawRepo()

    # Determine if identifier is UUID or SHA256
    sha256 = None
    raw_ref = None

    try:
        # Try parsing as UUID
        uuid_id = UUID(args.identifier)
        with session_factory.session() as session:
            raw_ref = raw_repo.get_by_id(session, uuid_id)
            if raw_ref:
                sha256 = raw_ref.sha256
                print(f"Found RawRef by ID: {raw_ref.id}")
    except ValueError:
        pass

    if sha256 is None:
        # Assume it's a SHA256
        if len(args.identifier) == 64:
            sha256 = args.identifier
            with session_factory.session() as session:
                raw_ref = raw_repo.get_by_sha(session, sha256)
                if raw_ref:
                    print(f"Found RawRef by SHA256: {raw_ref.id}")
        else:
            print(f"Error: Invalid identifier: {args.identifier}", file=sys.stderr)
            print("  Expected UUID or 64-character SHA256 hex", file=sys.stderr)
            sys.exit(1)

    print(f"\nVerifying SHA256: {sha256}")

    # Load blob from filesystem
    try:
        content = raw_store.load_by_sha(sha256, verify=False)
        print(f"  Loaded {len(content)} bytes from blob store")
    except BlobNotFoundError:
        print("  FAIL: Blob not found in store", file=sys.stderr)
        sys.exit(1)

    # Compute actual hash
    actual_sha256 = compute_sha256(content)
    print(f"  Computed SHA256: {actual_sha256}")

    # Compare
    if actual_sha256 == sha256:
        print("\n✓ OK: SHA256 verified!")
        if raw_ref:
            print(f"  Size matches: {len(content)} == {raw_ref.size_bytes}")
        sys.exit(0)
    else:
        print("\n✗ FAIL: SHA256 mismatch!", file=sys.stderr)
        print(f"  Expected: {sha256}", file=sys.stderr)
        print(f"  Actual:   {actual_sha256}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
