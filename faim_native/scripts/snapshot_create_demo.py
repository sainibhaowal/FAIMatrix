#!/usr/bin/env python3
"""Snapshot create demo - Create a snapshot with computed graph hash receipt.

Demonstrates snapshot creation with placeholder graph hash.

Usage:
    python snapshot_create_demo.py [--graph-id GRAPH_ID]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from faim.Faim_Native.core.contracts.types import SnapshotRecord, compute_graph_hash
from faim.Faim_Native.store.pg.models_faim import create_all_tables
from faim.Faim_Native.store.pg.repos.graph_version_repo import GraphVersionRepo
from faim.Faim_Native.store.pg.repos.snapshot_repo import SnapshotRepo
from faim.Faim_Native.store.pg.session import SessionFactory


def main():
    parser = argparse.ArgumentParser(
        description="Demo: Create a snapshot with graph hash receipt."
    )
    parser.add_argument(
        "--graph-id",
        type=str,
        default="demo_graph",
        help="Graph ID for the snapshot",
    )
    parser.add_argument("--db-url", type=str, default=None, help="Database URL")
    args = parser.parse_args()

    # Initialize database
    session_factory = SessionFactory(args.db_url)
    create_all_tables(session_factory.engine)

    print(f"Snapshot Create Demo for graph: {args.graph_id}")
    print("=" * 50)

    with session_factory.atomic() as session:
        snapshot_repo = SnapshotRepo()
        version_repo = GraphVersionRepo()

        # Get or bump graph version
        current_version = version_repo.get_version(session, args.graph_id)
        if current_version == 0:
            current_version = version_repo.bump(
                session, args.graph_id, "initial snapshot"
            )
            print(f"\n1. Created initial graph version: {current_version}")
        else:
            print(f"\n1. Current graph version: {current_version}")

        # Simulate node hashes (placeholder for real graph hash computation)
        # In a real system, you'd compute these from actual node data
        simulated_node_hashes = [
            "abc123def456...",
            "789xyz012345...",
            "fedcba987654...",
        ]
        graph_hash = compute_graph_hash(simulated_node_hashes)
        print("\n2. Computed graph hash receipt:")
        print(f"   Hash: {graph_hash[:32]}...")

        # Create snapshot
        snapshot = SnapshotRecord.create(
            graph_id=args.graph_id,
            graph_version=current_version,
            graph_hash=graph_hash,
            node_count=len(simulated_node_hashes),
            metadata={"source": "demo", "nodes_hashed": len(simulated_node_hashes)},
        )

        print("\n3. Created snapshot record:")
        print(f"   ID: {snapshot.id}")
        print(f"   Graph version: {snapshot.graph_version}")
        print(f"   Node count: {snapshot.node_count}")

        # Save to database
        saved = snapshot_repo.create(session, snapshot)
        print("\n4. Saved to database:")
        print(f"   ID: {saved.id}")
        print(f"   Created at: {saved.created_at}")

        # List all snapshots
        all_snapshots = snapshot_repo.list_by_graph(session, args.graph_id, limit=5)
        print(f"\n5. All snapshots for graph ({len(all_snapshots)} total):")
        for s in all_snapshots:
            print(f"   [{s.graph_version}] {s.id} - {s.node_count} nodes")

        # Get latest
        latest = snapshot_repo.get_latest(session, args.graph_id)
        if latest:
            print("\n6. Latest snapshot:")
            print(f"   ID: {latest.id}")
            print(f"   Version: {latest.graph_version}")
            print(f"   Hash: {latest.graph_hash[:32]}...")

    print("\n✓ Snapshot create demo complete!")


if __name__ == "__main__":
    main()
