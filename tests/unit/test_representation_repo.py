"""Repository tests for Representation V2 sidecar persistence and stats."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from faim_native.encoding.representation_v2 import build_representation_v2
from faim_native.store.pg.models_faim import Base, NodeModel
from faim_native.store.pg.repos.representation_repo import RepresentationRepo


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def _insert_node(session, node_id, graph_id="graph-1"):
    session.add(
        NodeModel(
            node_id=node_id,
            tenant_id="test_tenant",
            graph_id=graph_id,
            kind="atom",
            vector_hash=f"vh-{node_id}",
            raw_id=None,
            block_id=None,
            anchor_json=None,
            v_native=[0.0] * 256,
            opp_signature={},
            residual=0,
            level=0,
            touch_count=0,
        )
    )
    session.flush()


class TestRepresentationRepo:
    def test_upsert_creates_stats_and_is_idempotent(self):
        session = _make_session()
        try:
            node_id = uuid4()
            _insert_node(session, node_id)
            repo = RepresentationRepo(session=session, tenant_id="test_tenant")
            repr_v2 = build_representation_v2("release 2026 revenue 15 percent")

            status_1 = repo.upsert_node_representation("graph-1", node_id, repr_v2)
            status_2 = repo.upsert_node_representation("graph-1", node_id, repr_v2)

            assert status_1 == "inserted"
            assert status_2 == "unchanged"

            stats = repo.get_graph_stats("graph-1")
            assert stats["word"]["doc_count"] == 1
            assert stats["phrase"]["doc_count"] == 1
        finally:
            session.close()

    def test_top_k_lexical_returns_matching_node(self):
        session = _make_session()
        try:
            repo = RepresentationRepo(session=session, tenant_id="test_tenant")
            graph_id = "graph-1"
            match_id = uuid4()
            other_id = uuid4()
            _insert_node(session, match_id, graph_id)
            _insert_node(session, other_id, graph_id)

            repo.upsert_node_representation(
                graph_id,
                match_id,
                build_representation_v2("release 2026 revenue 15 percent"),
            )
            repo.upsert_node_representation(
                graph_id,
                other_id,
                build_representation_v2("warehouse inventory adjusted yesterday"),
            )

            ranked = repo.top_k_lexical(
                graph_id,
                build_representation_v2("revenue 2026 15 percent"),
                k=2,
            )

            assert ranked[0][0] == match_id
            assert ranked[0][1] >= ranked[1][1]
        finally:
            session.close()
