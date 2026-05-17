"""Acceptance tests for Phase 3 graph semantics and diffusion."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from faim_native.core.query.query_engine import recall_with_graph_expansion
from faim_native.orchestration.ingest_flow import FAIMProfile
from faim_native.orchestration.query_flow import run_query
from faim_native.store.pg.models_faim import Base, EdgeModel, NodeModel


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def _node(
    *,
    tenant_id: str,
    graph_id: str,
    vector_hash: str,
    raw_id: str,
    created_at: datetime,
):
    return NodeModel(
        node_id=uuid4(),
        tenant_id=tenant_id,
        graph_id=graph_id,
        kind="atom",
        vector_hash=vector_hash,
        raw_id=raw_id,
        block_id=f"block-{raw_id}",
        anchor_json={"doc_type": "text", "char_start": 0, "char_end": 32},
        v_native=[1.0] + [0.0] * 255,
        opp_signature={},
        residual=0,
        level=0,
        touch_count=1,
        last_access=created_at,
        created_at=created_at,
        updated_at=created_at,
    )


def _edge(*, tenant_id: str, graph_id: str, src, dst, kind: str, weight: float):
    return EdgeModel(
        edge_id=uuid4(),
        tenant_id=tenant_id,
        graph_id=graph_id,
        src_node_id=src,
        dst_node_id=dst,
        kind=kind,
        weight=int(weight * 1e9),
        meta={},
    )


def test_multihop_graph_recall_reaches_two_hop_neighbor():
    session = _session()
    try:
        tenant_id = "t1"
        graph_id = "g1"
        now = datetime.now(timezone.utc)
        seed = _node(
            tenant_id=tenant_id,
            graph_id=graph_id,
            vector_hash="a" * 64,
            raw_id="raw-seed",
            created_at=now,
        )
        bridge = _node(
            tenant_id=tenant_id,
            graph_id=graph_id,
            vector_hash="b" * 64,
            raw_id="raw-bridge",
            created_at=now,
        )
        target = _node(
            tenant_id=tenant_id,
            graph_id=graph_id,
            vector_hash="c" * 64,
            raw_id="raw-target",
            created_at=now,
        )
        session.add_all([seed, bridge, target])
        session.add_all(
            [
                _edge(
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    src=seed.node_id,
                    dst=bridge.node_id,
                    kind="inheritance",
                    weight=0.9,
                ),
                _edge(
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    src=bridge.node_id,
                    dst=target.node_id,
                    kind="synonym",
                    weight=0.8,
                ),
            ]
        )
        session.commit()

        candidates = recall_with_graph_expansion(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            q_vec=tuple(seed.v_native),
            n=10,
            seed_k=5,
            hop_limit=8,
        )
        candidate_ids = {node_id for node_id, _score in candidates}
        assert target.node_id in candidate_ids
    finally:
        session.close()


def test_run_query_exposes_phase3_graph_explain_and_suppresses_older_conflict():
    session = _session()
    try:
        tenant_id = "t2"
        graph_id = "g2"
        now = datetime.now(timezone.utc)
        seed = _node(
            tenant_id=tenant_id,
            graph_id=graph_id,
            vector_hash="d" * 64,
            raw_id="raw-seed",
            created_at=now,
        )
        current = _node(
            tenant_id=tenant_id,
            graph_id=graph_id,
            vector_hash="e" * 64,
            raw_id="raw-current",
            created_at=now,
        )
        historical = _node(
            tenant_id=tenant_id,
            graph_id=graph_id,
            vector_hash="f" * 64,
            raw_id="raw-historical",
            created_at=now - timedelta(days=2),
        )
        session.add_all([seed, current, historical])
        session.add_all(
            [
                _edge(
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    src=seed.node_id,
                    dst=current.node_id,
                    kind="inheritance",
                    weight=0.9,
                ),
                _edge(
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    src=seed.node_id,
                    dst=historical.node_id,
                    kind="inheritance",
                    weight=0.9,
                ),
                _edge(
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    src=current.node_id,
                    dst=historical.node_id,
                    kind="opposition",
                    weight=1.0,
                ),
            ]
        )
        session.commit()

        result = run_query(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            query_text="raw seed",
            k=5,
            profile=FAIMProfile.STRICT,
            return_explain=True,
            index=None,
            cache=None,
        )

        raw_ids = [item.get("evidence", {}).get("raw_id") for item in result.results]
        assert "raw-current" in raw_ids
        assert "raw-historical" not in raw_ids
        assert result.results
        explain = result.results[0]["explain"]
        assert "phase3_graph_paths" in explain
        assert "phase3_graph_score" in explain
    finally:
        session.close()
