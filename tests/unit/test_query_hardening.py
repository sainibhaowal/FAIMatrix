"""Regression coverage for the production query hardening contract."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from api.routers.query import PROFILE_MAP, QueryRequest
from core.query.query_engine import rerank_faim
from encoding.vector_schema import VECTOR_DIMENSION
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from store.pg.models_faim import NodeModel, create_all_tables


def _session():
    engine = create_engine("sqlite:///:memory:")
    create_all_tables(engine)
    return sessionmaker(bind=engine)()


def _node(*, tenant_id: str, graph_id: str, valid_from=None, valid_to=None):
    return NodeModel(
        node_id=uuid4(),
        tenant_id=tenant_id,
        graph_id=graph_id,
        kind="atom",
        vector_hash=uuid4().hex,
        v_native=[0.1] * VECTOR_DIMENSION,
        opp_signature={},
        valid_from=valid_from,
        valid_to=valid_to,
    )


def test_query_contract_maps_balanced_profile_explicitly():
    QueryRequest(graph_id="g", query_text="q")
    from orchestration.ingest_flow import FAIMProfile

    assert "BALANCED" in QueryRequest.model_fields["profile"].description
    assert PROFILE_MAP["BALANCED"] is FAIMProfile.BALANCED


def test_balanced_profile_has_explicit_adaptive_policy():
    from orchestration.profile_persist_policy import resolve_profile_persist_policy

    policy = resolve_profile_persist_policy(
        operation="ingest",
        requested_profile="balanced",
        requested_persist_mode="strict",
        compatibility_mode=False,
    )

    assert policy.coerced is False
    assert policy.effective_profile == "balanced"
    assert policy.index_enabled is True


def test_as_of_filters_evidence_by_explicit_validity_interval():
    session = _session()
    try:
        tenant_id, graph_id = "tenant", "graph"
        expired = _node(
            tenant_id=tenant_id,
            graph_id=graph_id,
            valid_to=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        active = _node(
            tenant_id=tenant_id,
            graph_id=graph_id,
            valid_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        session.add_all([expired, active])
        session.commit()

        ranked = rerank_faim(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            q_vec=tuple([0.1] * VECTOR_DIMENSION),
            candidate_ids=[expired.node_id, active.node_id],
            as_of=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

        assert [item["node_id"] for item in ranked] == [active.node_id]
        assert ranked[0]["temporal_status"] == "CURRENT"
    finally:
        session.close()


def test_invalid_validity_interval_is_rejected_by_ingest_flow():
    from orchestration.ingest_flow import run_ingest

    with pytest.raises(ValueError, match="valid_to must be later"):
        run_ingest(
            graph_id="g",
            raw_id="r",
            filename="x.txt",
            file_bytes=b"x",
            valid_from=datetime(2026, 2, 1, tzinfo=timezone.utc),
            valid_to=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )


def test_graph_metrics_are_cached_by_graph_version(monkeypatch):
    from orchestration.query_flow import get_graph_metrics
    from store.pg.models_faim import GraphDiagnosticsCacheModel

    session = _session()
    try:
        first = get_graph_metrics(session, "tenant", "graph")
        assert first["diagnostics_cached"] == 1.0
        assert session.query(GraphDiagnosticsCacheModel).count() == 1

        import core.dynamics.evolution_native as evolution_native

        original = evolution_native.compute_graph_diagnostics
        calls = {"count": 0}

        def counted(*args, **kwargs):
            calls["count"] += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(evolution_native, "compute_graph_diagnostics", counted)
        second = get_graph_metrics(session, "tenant", "graph")
        assert second["diagnostics_hash"] == first["diagnostics_hash"]
        assert calls["count"] == 0
    finally:
        session.close()


def test_special_node_hash_is_bounded_for_postgres_catalog_contract():
    from store.pg.repos.node_repo import NodeRepo

    session = _session()
    try:
        repo = NodeRepo(session=session, tenant_id="tenant")
        node_id = repo.upsert_special_node(
            graph_id="graph",
            kind="fact",
            vector_hash="fact:" + ("x" * 64),
            v_native=[0.1] * VECTOR_DIMENSION,
            opp_signature={},
        )
        row = repo.get_node("graph", node_id)
        assert row is not None
        assert len(row.vector_hash) == 64
        same_id = repo.upsert_special_node(
            graph_id="graph",
            kind="fact",
            vector_hash="fact:" + ("x" * 64),
            v_native=[0.2] * VECTOR_DIMENSION,
            opp_signature={},
        )
        assert same_id == node_id
    finally:
        session.close()
