#!/usr/bin/env python3
"""Event append demo - Append a dummy event and read it back.

Demonstrates the append-only event journal with checksum verification.

Usage:
    python event_append_demo.py [--graph-id GRAPH_ID]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from faim.Faim_Native.core.contracts.types import EventRecord
from faim.Faim_Native.store.journal.event_journal import EventJournal
from faim.Faim_Native.store.pg.models_faim import create_all_tables
from faim.Faim_Native.store.pg.session import SessionFactory


def main():
    parser = argparse.ArgumentParser(
        description="Demo: Append a dummy event and read it back."
    )
    parser.add_argument(
        "--graph-id",
        type=str,
        default="demo_graph",
        help="Graph ID for the event",
    )
    parser.add_argument("--db-url", type=str, default=None, help="Database URL")
    args = parser.parse_args()

    # Initialize database
    session_factory = SessionFactory(args.db_url)
    create_all_tables(session_factory.engine)

    print(f"Event Append Demo for graph: {args.graph_id}")
    print("=" * 50)

    with session_factory.atomic() as session:
        journal = EventJournal(session)

        # Create a sample event
        event = EventRecord.create(
            graph_id=args.graph_id,
            kind="node_created",
            payload={
                "node_id": "demo_node_001",
                "label": "Demo Node",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        print("\n1. Created event:")
        print(f"   ID: {event.id}")
        print(f"   Kind: {event.kind}")
        print(f"   Checksum: {event.checksum[:16]}...")
        print(f"   Checksum valid: {event.verify_checksum()}")

        # Append to journal
        saved = journal.append(event)
        print("\n2. Appended to journal:")
        print(f"   Seq: {saved.seq}")
        print(f"   ID: {saved.id}")

        # Get event count
        count = journal.count(args.graph_id)
        print(f"\n3. Total events in graph: {count}")

        # Read back events
        events = journal.read(args.graph_id, after_seq=0, limit=10)
        print(f"\n4. Read back {len(events)} events:")
        for e in events:
            print(f"   [{e.seq}] {e.kind}: {e.payload.get('node_id', 'N/A')}")
            print(f"        Checksum valid: {e.verify_checksum()}")

        # Get latest event
        latest = journal.get_latest(args.graph_id)
        if latest:
            print("\n5. Latest event:")
            print(f"   Seq: {latest.seq}")
            print(f"   Kind: {latest.kind}")
            print(f"   Timestamp: {latest.ts}")

    print("\n✓ Event append demo complete!")


if __name__ == "__main__":
    main()
