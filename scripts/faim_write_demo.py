#!/usr/bin/env python3
"""FAIM Write Demo.

Demonstrates: raw → extract → packet → encode → write_atoms pipeline.

Usage:
    python scripts/faim_write_demo.py <file_path>
    python scripts/faim_write_demo.py  # uses sample text
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Setup paths
_script_dir = Path(__file__).parent
_faim_native = _script_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.contracts.types import EventRecord, uuid7  # noqa: E402
from core.engine_native import FAIMNativeEngine  # noqa: E402
from encoding.text_vectorizer import vectorize_blocks  # noqa: E402
from perception.packetize import create_packet  # noqa: E402
from perception.router import route_extraction  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from store.pg.models_faim import create_all_tables  # noqa: E402
from store.pg.repos.edge_repo import EdgeRepo  # noqa: E402
from store.pg.repos.event_repo import EventRepo  # noqa: E402
from store.pg.repos.graph_version_repo import GraphVersionRepo  # noqa: E402
from store.pg.repos.node_repo import NodeRepo  # noqa: E402


class EventRepoWrapper:
    """Wrapper to give EventRepo a session."""

    def __init__(self, session):
        self.session = session
        self._repo = EventRepo()

    def append(self, graph_id: str, kind: str, payload: dict):
        import hashlib
        import json
        from datetime import datetime, timezone

        ts = datetime.now(timezone.utc)
        checksum = hashlib.sha256(
            f"{ts.isoformat()}|{graph_id}|{kind}|{json.dumps(payload)}".encode()
        ).hexdigest()
        event = EventRecord(
            id=uuid7(),
            seq=None,
            ts=ts,
            graph_id=graph_id,
            kind=kind,
            payload=payload,
            checksum=checksum,
            created_at=ts,
        )
        return self._repo.append(self.session, event)

    def list(self, graph_id: str, limit: int = 100):
        return self._repo.list(self.session, graph_id=graph_id, limit=limit)


class GraphVersionRepoWrapper:
    """Wrapper to give GraphVersionRepo a session."""

    def __init__(self, session):
        self.session = session
        self._repo = GraphVersionRepo()

    def get(self, graph_id: str):
        return self._repo.get(self.session, graph_id)

    def bump(self, graph_id: str, reason: str = None):
        return self._repo.bump(self.session, graph_id, reason=reason)


SAMPLE_TEXT = b"""
FAIM-Native Demonstration

This is a sample document to demonstrate the full FAIM-native pipeline:
1. RawTruth storage with SHA256 verification
2. Perception layer with EvidenceBlocks and BlockAnchors
3. Encoding layer with 256-dimensional vectors
4. Core physics with inheritance and antisym merge

The golden ratio (phi = 1.618) plays a key role in fractal mathematics.
The scaling factor s = 1/phi controls inheritance and evolution dynamics.
"""


def main():
    parser = argparse.ArgumentParser(description="FAIM Write Demo")
    parser.add_argument("file", nargs="?", help="File to ingest (optional)")
    parser.add_argument("--graph-id", default="demo_graph", help="Graph ID")
    parser.add_argument("--db", default="sqlite:///:memory:", help="Database URL")
    args = parser.parse_args()

    # Load content
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
        content = file_path.read_bytes()
        filename = file_path.name
    else:
        content = SAMPLE_TEXT
        filename = "sample.txt"

    raw_id = str(uuid7())
    graph_id = args.graph_id

    print("=" * 60)
    print("FAIM-Native Write Demo")
    print("=" * 60)
    print(f"Content size: {len(content)} bytes")
    print(f"Filename: {filename}")
    print(f"Raw ID: {raw_id}")
    print(f"Graph ID: {graph_id}")
    print()

    # 1. Extract
    print("[1/4] Extracting blocks...")
    blocks = route_extraction(content, filename, raw_id)
    print(f"      Extracted {len(blocks)} blocks")

    # 2. Packet
    print("[2/4] Creating packet...")
    packet = create_packet(raw_id, blocks)
    print(f"      Packet hash: {packet.packet_hash[:16]}...")

    # 3. Encode
    print("[3/4] Encoding vectors...")
    vectors = vectorize_blocks(blocks)
    print(f"      Encoded {len(vectors)} vectors (256-dim each)")

    # 4. Write
    print("[4/4] Writing to graph...")

    # Setup database
    engine = create_engine(args.db)
    create_all_tables(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    repos = {
        "node_repo": NodeRepo(session),
        "edge_repo": EdgeRepo(session),
        "event_repo": EventRepoWrapper(session),
        "graph_version_repo": GraphVersionRepoWrapper(session),
    }
    faim_engine = FAIMNativeEngine(**repos)

    result = faim_engine.write_atoms(graph_id, vectors)

    print()
    print("=" * 60)
    print("Results")
    print("=" * 60)
    print(f"Nodes written: {result.nodes_written}")
    print(f"Edges written: {result.edges_written}")
    print(f"Merges: {result.merges}")
    print(f"Events emitted: {result.events_emitted}")
    print(f"Graph version: {result.graph_version}")
    print()

    # Compute graph hash
    graph_hash = faim_engine.compute_graph_hash(graph_id)
    print(f"Graph hash: {graph_hash}")

    # Stats
    stats = faim_engine.get_graph_stats(graph_id)
    print()
    print("Graph Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    session.close()
    print()
    print("✓ Write demo complete")


if __name__ == "__main__":
    main()
