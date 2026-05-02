#!/usr/bin/env python3
"""FAIM Diagnostics Demo.

Demonstrates: load graph → compute D/H/λ diagnostics → print results.

Usage:
    python scripts/faim_diagnostics_demo.py
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
from core.metrics.fractal_physics import (  # noqa: E402
    GOLDEN_S,
    PHI,
    compute_diagnostics,
)
from encoding.text_vectorizer import vectorize_blocks  # noqa: E402
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


class GraphVersionRepoWrapper:
    """Wrapper to give GraphVersionRepo a session."""

    def __init__(self, session):
        self.session = session
        self._repo = GraphVersionRepo()

    def get(self, graph_id: str):
        return self._repo.get(self.session, graph_id)

    def bump(self, graph_id: str, reason: str = None):
        return self._repo.bump(self.session, graph_id, reason=reason)


SAMPLE_TEXTS = [
    b"The golden ratio phi appears throughout nature and mathematics.",
    b"Fractals exhibit self-similarity at different scales.",
    b"Memory systems can evolve through inheritance and opposition.",
    b"Deterministic algorithms ensure reproducible behavior.",
    b"Entropy measures disorder in a probability distribution.",
]


def main():
    parser = argparse.ArgumentParser(description="FAIM Diagnostics Demo")
    parser.add_argument("--graph-id", default="diagnostics_demo", help="Graph ID")
    args = parser.parse_args()

    graph_id = args.graph_id

    print("=" * 60)
    print("FAIM-Native Diagnostics Demo")
    print("=" * 60)
    print(f"PHI (golden ratio): {PHI:.6f}")
    print(f"GOLDEN_S (1/PHI):   {GOLDEN_S:.6f}")
    print(f"Graph ID: {graph_id}")
    print()

    # Setup database
    engine = create_engine("sqlite:///:memory:")
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

    # Write sample data
    print("[1/2] Writing sample data...")
    for i, text in enumerate(SAMPLE_TEXTS):
        raw_id = f"raw_{i:03d}"
        blocks = route_extraction(text, f"doc_{i}.txt", raw_id)
        vectors = vectorize_blocks(blocks)
        faim_engine.write_atoms(graph_id, vectors)

    print(f"      Wrote {len(SAMPLE_TEXTS)} documents")
    print()

    # Get nodes and edges
    nodes = repos["node_repo"].list_nodes(graph_id, limit=100)
    edges = repos["edge_repo"].list_all_edges(graph_id, limit=100)
    version = repos["graph_version_repo"].get(graph_id) or 0

    # Compute diagnostics
    print("[2/2] Computing diagnostics...")

    vectors = [n.v_native for n in nodes if n.v_native]
    residuals = [n.residual / 1e9 if n.residual else 0.0 for n in nodes]

    diagnostics = compute_diagnostics(
        graph_id=graph_id,
        vectors=vectors,
        residuals=residuals,
        edge_count=len(edges),
        graph_version=version,
    )

    print()
    print("=" * 60)
    print("Fractal Physics Diagnostics")
    print("=" * 60)
    print(f"Graph ID:      {diagnostics.graph_id}")
    print(f"Region:        {diagnostics.region_id}")
    print(f"Node count:    {diagnostics.node_count}")
    print(f"Edge count:    {diagnostics.edge_count}")
    print()
    print("FAIM-Native Metrics:")
    print(f"  s (scaling):   {diagnostics.s:.6f}")
    print(f"  D (dimension): {diagnostics.D_hat:.6f}")
    print(f"  H (entropy):   {diagnostics.H_hat:.6f}")
    print(f"  λ (pressure):  {diagnostics.lambda_hat:.6f}")
    print()
    print("Derived Metrics:")
    print(f"  R (redundancy): {diagnostics.redundancy_R:.6f}")
    print(f"  N (novelty):    {diagnostics.novelty_N:.6f}")
    print(f"  E (energy):     {diagnostics.energy_E:.6f}")
    print()
    print(f"Graph version:    {diagnostics.computed_at_version}")
    print(f"Diagnostics hash: {diagnostics.diagnostics_hash[:32]}...")

    session.close()
    print()
    print("✓ Diagnostics demo complete")


if __name__ == "__main__":
    main()
