from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch
from uuid import uuid4

from lexical.semantic_registry import resolve_semantic_registry_expansions
from orchestration import query_reinforcement as qrl
from orchestration.query_flow import _domain_weighted_expansions
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from store.pg.models_faim import Base, NodeRepresentationV2Model
from store.pg.repos.domain_knowledge_repo import DomainKnowledgeRepo


def _make_memory_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_record_query_evidence_async_respects_flags_and_is_nonblocking(monkeypatch):
    monkeypatch.setenv("FAIM_BENCHMARK_MODE", "true")
    assert (
        qrl.record_query_evidence_async(
            tenant_id="t1",
            graph_id="g1",
            query_text="sample query",
            top_node_ids=[str(uuid4())],
        )
        is False
    )

    monkeypatch.setenv("FAIM_BENCHMARK_MODE", "false")
    monkeypatch.setenv("FAIM_QUERY_REINFORCEMENT_ENABLED", "true")
    t0 = time.perf_counter()
    with patch.object(qrl, "_push_event_to_redis", return_value=True):
        ok = qrl.record_query_evidence_async(
            tenant_id="t1",
            graph_id="g1",
            query_text="sample query",
            top_node_ids=[str(uuid4())],
        )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert ok is True
    assert elapsed_ms < 50.0


def test_redis_push_and_pop_roundtrip_with_mock_redis():
    stored = []

    class _FakePipe:
        def __init__(self):
            self._ops = []

        def rpush(self, key, val):
            stored.append(val)
            self._ops.append(1)

        def ltrim(self, key, start, end):
            self._ops.append(1)

        def expire(self, key, ttl):
            self._ops.append(1)

        def lrange(self, key, start, end):
            self._ops.append(("lrange", list(stored)))

        def execute(self):
            return [op[1] if isinstance(op, tuple) else op for op in self._ops]

    fake_client = MagicMock()
    fake_client.pipeline.side_effect = lambda **_kw: _FakePipe()

    with patch("cache.redis_client._get_client", return_value=fake_client):
        assert qrl._push_event_to_redis(
            {
                "tenant_id": "t1",
                "graph_id": "g1",
                "query_text": "hello world",
                "top_node_ids": ["n1"],
                "reward": 1.0,
            }
        )
        popped = qrl._pop_events_from_redis("t1", "g1")

    assert len(popped) == 1
    assert popped[0]["query_text"] == "hello world"


def test_promote_query_evidence_bridges_end_to_end_and_query_expansion():
    session = _make_memory_session()
    tenant_id = "t-qrl"
    graph_id = "g-qrl"
    nid = uuid4()
    session.add(
        NodeRepresentationV2Model(
            node_id=nid,
            tenant_id=tenant_id,
            graph_id=graph_id,
            repr_hash="h-qrl-1",
            normalized_text="ignition coil battery failure troubleshooting",
        )
    )
    session.commit()

    events = [
        {"query_text": "sluggish crank", "top_node_ids": [str(nid)], "reward": 1.0},
        {"query_text": "sluggish crank", "top_node_ids": [str(nid)], "reward": 1.5},
    ]
    res = qrl.promote_query_evidence_bridges(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        events=events,
        min_reinforcement_count=2,
        max_bridges_per_term=6,
    )
    session.commit()

    assert res.status == "completed"
    assert res.events_consumed == 2
    assert res.bridges_persisted > 0
    assert res.graph_version == 1

    domain_repo = DomainKnowledgeRepo(session=session, tenant_id=tenant_id)
    domain_rows = domain_repo.list_lexicon_entries(graph_id)
    domain_map = domain_repo.get_domain_map(graph_id)

    weighted = _domain_weighted_expansions("sluggish crank", domain_rows)
    terms = {item.term for item in weighted}
    assert "ignition" in terms or "battery" in terms

    reg_expansions, _info = resolve_semantic_registry_expansions(
        query_text="sluggish crank",
        domain_map=domain_map,
    )
    reg_terms = {item.term for item in reg_expansions}
    assert "ignition" in reg_terms or "battery" in reg_terms


def test_promote_respects_min_reinforcement_count_and_edge_cases():
    session = _make_memory_session()
    nid = uuid4()
    session.add(
        NodeRepresentationV2Model(
            node_id=nid,
            tenant_id="t1",
            graph_id="g1",
            repr_hash="h1",
            normalized_text="voltage regulator diode failure",
        )
    )
    session.commit()

    # Single event is below min_reinforcement_count=2
    res_low = qrl.promote_query_evidence_bridges(
        session=session,
        tenant_id="t1",
        graph_id="g1",
        events=[{"query_text": "dim headlight", "top_node_ids": [str(nid)]}],
        min_reinforcement_count=2,
    )
    assert res_low.status == "skipped"
    assert res_low.reason == "below_min_reinforcement_count"

    assert (
        qrl.promote_query_evidence_bridges(
            session=None, tenant_id="t1", graph_id="g1"
        ).reason
        == "no_session"
    )
    assert (
        qrl.promote_query_evidence_bridges(
            session=session, tenant_id="t1", graph_id="g1", events=[]
        ).reason
        == "no_feedback_events"
    )
