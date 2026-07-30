"""Unit tests for Advanced Temporal Contradiction Resolution (Transitive & Soft)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.query.query_engine import rerank_faim
from store.pg.models_faim import EdgeModel, NodeModel, create_all_tables


def test_transitive_contradiction_resolution():
    engine = create_engine("sqlite:///:memory:")
    create_all_tables(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    tenant_id = "tenant_test"
    graph_id = "graph_test"

    # Create 3 nodes:
    # A (old: 2024)
    # B (new: 2026)
    # C (new descendant of B: 2026-02)
    id_a = uuid4()
    id_b = uuid4()
    id_c = uuid4()

    node_a = NodeModel(
        node_id=id_a,
        tenant_id=tenant_id,
        graph_id=graph_id,
        kind="atom",
        vector_hash="hash_a",
        v_native=[0.1, 0.2],
        residual=0,
        level=0,
        touch_count=0,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )

    node_b = NodeModel(
        node_id=id_b,
        tenant_id=tenant_id,
        graph_id=graph_id,
        kind="atom",
        vector_hash="hash_b",
        v_native=[0.1, 0.3],
        residual=0,
        level=0,
        touch_count=0,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    node_c = NodeModel(
        node_id=id_c,
        tenant_id=tenant_id,
        graph_id=graph_id,
        kind="atom",
        vector_hash="hash_c",
        v_native=[0.1, 0.4],
        residual=0,
        level=1,
        touch_count=0,
        created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    # 1. Opposition edge between A and B
    edge_opp = EdgeModel(
        edge_id=uuid4(),
        tenant_id=tenant_id,
        graph_id=graph_id,
        src_node_id=id_a,
        dst_node_id=id_b,
        kind="opposition",
        weight=int(1.0 * 1e9),
    )

    # 2. Inheritance edge: C inherits from B (so B is parent/src, C is child/dst)
    edge_inh = EdgeModel(
        edge_id=uuid4(),
        tenant_id=tenant_id,
        graph_id=graph_id,
        src_node_id=id_b,
        dst_node_id=id_c,
        kind="inheritance",
        weight=int(1.0 * 1e9),
    )

    session.add_all([node_a, node_b, node_c, edge_opp, edge_inh])
    session.commit()

    # Pre-rank list in scored format (similarity etc doesn't matter for contradiction testing)
    scored = [
        {"node_id": id_a, "score": 0.8, "score_components": {}, "level": 0, "touch_count": 0, "vector_hash": "hash_a"},
        {"node_id": id_c, "score": 0.95, "score_components": {}, "level": 1, "touch_count": 0, "vector_hash": "hash_c"},
    ]

    # --- Mode 1: include_historical=True (Soft Suppression) ---
    results_soft = rerank_faim(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        q_vec=(0.1, 0.2),
        candidate_ids=[id_a, id_c],
        k=10,
        include_historical=True,
    )
    # Patch the scores so they match our input scored (since we did not specify graph/lexical/domain scores)
    for r in results_soft:
        if r["node_id"] == id_a:
            node_a_res = r
        elif r["node_id"] == id_c:
            node_c_res = r

    # Assertions for Soft mode:
    # 1. Node A (historical) is kept in the output
    assert len(results_soft) == 2
    assert node_a_res["temporal_status"] == "HISTORICAL"
    assert node_c_res["temporal_status"] == "CURRENT"
    assert node_a_res["superseded_by"] == id_c
    assert id_a in node_c_res["supersedes"]

    # --- Mode 2: include_historical=False (Hard Suppression) ---
    # We must reset the scored list because rerank_faim modifies list references/contents
    results_hard = rerank_faim(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        q_vec=(0.1, 0.2),
        candidate_ids=[id_a, id_c],
        k=10,
        include_historical=False,
    )

    # Assertions for Hard mode:
    # 1. Node A is completely suppressed (removed)
    assert len(results_hard) == 1
    assert results_hard[0]["node_id"] == id_c
    assert results_hard[0]["temporal_status"] == "CURRENT"

    session.close()
