"""Acceptance: evolve remains stable when opposition edge already exists."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.contracts.types import uuid7
from orchestration.evolve_flow import run_evolve
from store.pg.models_faim import NodeModel, create_all_tables
from store.pg.repos.edge_repo import EdgeRepo
from store.pg.repos.event_repo import EventRepo
from store.pg.repos.graph_version_repo import GraphVersionRepo
from store.pg.repos.node_repo import NodeRepo


def test_evolve_repeated_runs_do_not_fail_on_existing_opposition_edge():
    engine = create_engine("sqlite:///:memory:")
    create_all_tables(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    tenant_id = "tenant_at_evolve_edge_idem"
    graph_id = "graph_at_evolve_edge_idem"
    now = datetime.now(timezone.utc)

    try:
        session.add(
            NodeModel(
                node_id=uuid7(),
                tenant_id=tenant_id,
                graph_id=graph_id,
                kind="atom",
                vector_hash="a" * 64,
                raw_id="raw_a",
                block_id="block_a",
                anchor_json={"doc_type": "text"},
                v_native=[0.125] * 256,
                opp_signature=None,
                residual=0,
                level=0,
                touch_count=1,
                last_access=now,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            NodeModel(
                node_id=uuid7(),
                tenant_id=tenant_id,
                graph_id=graph_id,
                kind="atom",
                vector_hash="b" * 64,
                raw_id="raw_b",
                block_id="block_b",
                anchor_json={"doc_type": "text"},
                v_native=[0.125] * 256,
                opp_signature=None,
                residual=0,
                level=0,
                touch_count=1,
                last_access=now,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

        node_repo = NodeRepo(session, tenant_id=tenant_id)
        edge_repo = EdgeRepo(session, tenant_id=tenant_id)
        event_repo = EventRepo(session, tenant_id=tenant_id)
        gv_repo = GraphVersionRepo(session, tenant_id=tenant_id)

        first = run_evolve(
            graph_id=graph_id,
            tenant_id=tenant_id,
            session=session,
            profile="strict",
            persist_mode="relaxed",
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            gv_repo=gv_repo,
        )
        assert first.status == "completed"

        second = run_evolve(
            graph_id=graph_id,
            tenant_id=tenant_id,
            session=session,
            profile="strict",
            persist_mode="relaxed",
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            gv_repo=gv_repo,
        )
        assert second.status == "completed"

        opposition_edges = edge_repo.list_opposition_edges(graph_id=graph_id, limit=20)
        assert len(opposition_edges) == 1
        assert opposition_edges[0].kind == "opposition"
    finally:
        session.close()
