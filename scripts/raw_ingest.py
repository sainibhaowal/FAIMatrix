#!/usr/bin/env python3
"""Raw ingest script - Store a file as a raw blob and create RawRef in database.

Usage:
    python raw_ingest.py <file_path> [--graph-id GRAPH_ID] [--blob-dir BLOB_DIR]

Example:
    echo "test content" > /tmp/test.txt
    python raw_ingest.py /tmp/test.txt --graph-id myGraph
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from faim.Faim_Native.store.pg.models_faim import create_all_tables
from faim.Faim_Native.store.pg.repos.raw_repo import RawRepo
from faim.Faim_Native.store.pg.session import SessionFactory
from faim.Faim_Native.store.raw.raw_store import RawStore


def main():
    parser = argparse.ArgumentParser(
        description="Ingest a file into the raw blob store and database."
    )
    parser.add_argument("file_path", type=Path, help="Path to file to ingest")
    parser.add_argument("--graph-id", type=str, default=None, help="Optional graph ID")
    parser.add_argument(
        "--blob-dir",
        type=Path,
        default=Path("/tmp/faim_blobs"),
        help="Directory for blob storage",
    )
    parser.add_argument("--db-url", type=str, default=None, help="Database URL")
    args = parser.parse_args()

    # Validate file exists
    if not args.file_path.exists():
        print(f"Error: File not found: {args.file_path}", file=sys.stderr)
        sys.exit(1)

    # Read file content
    content = args.file_path.read_bytes()
    print(f"Read {len(content)} bytes from {args.file_path}")

    # Detect MIME type
    suffix = args.file_path.suffix.lower()
    mime_types = {
        ".txt": "text/plain",
        ".json": "application/json",
        ".md": "text/markdown",
        ".py": "text/x-python",
        ".html": "text/html",
        ".xml": "application/xml",
    }
    mime_type = mime_types.get(suffix, "application/octet-stream")

    # Initialize stores
    raw_store = RawStore(args.blob_dir)
    session_factory = SessionFactory(args.db_url)

    # Create tables if needed
    create_all_tables(session_factory.engine)

    # Store blob
    raw_ref = raw_store.store(content, mime_type=mime_type, graph_id=args.graph_id)
    print(f"Stored blob: {raw_ref.sha256}")
    print(f"  URI: {raw_ref.uri}")

    # Store reference in database
    raw_repo = RawRepo()
    with session_factory.atomic() as session:
        saved_ref = raw_repo.create(session, raw_ref)
        print("Created RawRef in database:")
        print(f"  ID: {saved_ref.id}")
        print(f"  SHA256: {saved_ref.sha256}")
        print(f"  Size: {saved_ref.size_bytes} bytes")
        print(f"  MIME: {saved_ref.mime_type}")
        print(f"  Graph: {saved_ref.graph_id or 'None'}")
        print(f"  Created: {saved_ref.created_at}")

    print("\n✓ Ingest complete!")
    return saved_ref


if __name__ == "__main__":
    main()
