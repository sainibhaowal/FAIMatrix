from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from faim_native.core.reasoning.traversal import MultiHopTraverser
from faim_native.store.pg.models_faim import Base, EdgeModel, NodeModel


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def _node(*, tenant_id: str, graph_id: str, raw_id: str):
    now = datetime.now(timezone.utc)
    return NodeModel(
        node_id=uuid4(),
        tenant_id=tenant_id,
        graph_id=graph_id,
        kind="atom",
        vector_hash=uuid4().hex,
        raw_id=raw_id,
        block_id=f"block-{raw_id}",
        anchor_json={"filename": raw_id},
        v_native=[1.0] + [0.0] * 255,
        opp_signature={},
        residual=0,
        level=0,
        touch_count=1,
        last_access=now,
        created_at=now,
        updated_at=now,
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
        created_at=datetime.now(timezone.utc),
    )


def test_traverser_supports_more_than_three_hops_with_exact_goal_match():
    session = _session()
    try:
        tenant_id = "tenant-hop"
        graph_id = "graph-hop"
        labels = ["start", "hop-1", "hop-2", "hop-3", "hop-4", "target-service"]
        nodes = [_node(tenant_id=tenant_id, graph_id=graph_id, raw_id=label) for label in labels]
        session.add_all(nodes)
        session.add_all(
            [
                _edge(
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    src=nodes[idx].node_id,
                    dst=nodes[idx + 1].node_id,
                    kind="leads_to",
                    weight=0.95,
                )
                for idx in range(len(nodes) - 1)
            ]
        )
        session.commit()

        traverser = MultiHopTraverser(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
        )
        paths = traverser.traverse(
            start_node_ids=[str(nodes[0].node_id)],
            goal="target-service",
            max_hops=8,
            edge_types={"leads_to"},
        )

        assert paths
        assert any(path.hop_count >= 5 for path in paths)
        assert any(path.end_node == str(nodes[-1].node_id) for path in paths)
    finally:
        session.close()


def test_traverser_returns_partial_path_when_goal_not_exactly_matched():
    session = _session()
    try:
        tenant_id = "tenant-partial"
        graph_id = "graph-partial"
        labels = ["seed", "bridge", "candidate"]
        nodes = [_node(tenant_id=tenant_id, graph_id=graph_id, raw_id=label) for label in labels]
        session.add_all(nodes)
        session.add_all(
            [
                _edge(
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    src=nodes[0].node_id,
                    dst=nodes[1].node_id,
                    kind="related_to",
                    weight=0.9,
                ),
                _edge(
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    src=nodes[1].node_id,
                    dst=nodes[2].node_id,
                    kind="related_to",
                    weight=0.8,
                ),
            ]
        )
        session.commit()

        traverser = MultiHopTraverser(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
        )
        paths = traverser.traverse(
            start_node_ids=[str(nodes[0].node_id)],
            goal="missing-goal",
            max_hops=6,
            edge_types={"related_to"},
            return_partial_paths=True,
        )

        assert paths
        assert paths[0].metadata.get("partial") is True
        assert paths[0].metadata.get("node_ids")
        assert paths[0].metadata.get("edge_ids")
    finally:
        session.close()
