"""Phase R5 unit checks: additive response/event clarity fields."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4


@dataclass
class _MergeResult:
    winner_id: str
    loser_id: str
    meta: dict


class _DummyNodeRepo:
    def __init__(self, nodes):
        self._nodes = nodes
        self.session = object()
        self.tenant_id = "tenant_r5"

    def list_nodes(self, graph_id, limit=1000):  # noqa: ARG002
        return list(self._nodes)

    def delete_node(self, graph_id, node_id):  # noqa: ARG002
        return None


class _DummyEdgeRepo:
    def list_all_edges(self, graph_id, limit=10000):  # noqa: ARG002
        return []

    def add_opposition_edge(self, graph_id, a_id, b_id, weight, meta):  # noqa: ARG002
        return None

    def delete_edges_for_node(self, graph_id, node_id):  # noqa: ARG002
        return None


class _DummyEventRepo:
    def __init__(self):
        self.events = []

    def emit(self, session, graph_id, kind, payload):  # noqa: ARG002
        self.events.append({"kind": kind, "payload": payload})


class _DummyGraphVersionRepo:
    def get(self, session, graph_id):  # noqa: ARG002
        return SimpleNamespace(version=1)

    def bump(self, session, graph_id, reason):  # noqa: ARG002
        return 2


def test_r5_evolution_skipped_payload_includes_mode_context():
    from core.dynamics.evolution_native import evolve_once

    graph_id = f"r5-skip-{uuid4().hex[:8]}"
    node = SimpleNamespace(
        node_id=str(uuid4()),
        v_native=[1.0, 0.0, 0.0],
        vector_hash="vh_skip",
        residual=0,
        touch_count=1,
    )
    node_repo = _DummyNodeRepo(nodes=[node])
    edge_repo = _DummyEdgeRepo()
    event_repo = _DummyEventRepo()
    gv_repo = _DummyGraphVersionRepo()

    evolve_once(
        graph_id=graph_id,
        node_repo=node_repo,
        edge_repo=edge_repo,
        event_repo=event_repo,
        graph_version_repo=gv_repo,
        event_context={
            "requested_profile": "relaxed",
            "requested_persist_mode": "relaxed",
            "effective_profile": "relaxed",
            "effective_persist_mode": "relaxed",
            "durability_path": "core_sync_secondary_async",
        },
    )

    skipped = [e for e in event_repo.events if e["kind"] == "EVOLUTION_SKIPPED"]
    assert skipped, "expected EVOLUTION_SKIPPED event"
    payload = skipped[-1]["payload"]
    assert payload["requested_profile"] == "relaxed"
    assert payload["requested_persist_mode"] == "relaxed"
    assert payload["effective_profile"] == "relaxed"
    assert payload["effective_persist_mode"] == "relaxed"
    assert payload["durability_path"] == "core_sync_secondary_async"


def test_r5_evolution_complete_payload_includes_mode_context(monkeypatch):
    import core.dynamics.evolution_native as evolution_native

    graph_id = f"r5-complete-{uuid4().hex[:8]}"
    node_a = SimpleNamespace(
        node_id=str(uuid4()),
        v_native=[1.0, 0.0, 0.0],
        vector_hash="vh_a",
        residual=0,
        touch_count=1,
    )
    node_b = SimpleNamespace(
        node_id=str(uuid4()),
        v_native=[1.0, 0.0, 0.0],
        vector_hash="vh_b",
        residual=0,
        touch_count=1,
    )
    node_repo = _DummyNodeRepo(nodes=[node_a, node_b])
    edge_repo = _DummyEdgeRepo()
    event_repo = _DummyEventRepo()
    gv_repo = _DummyGraphVersionRepo()

    monkeypatch.setattr(evolution_native, "should_merge", lambda score, threshold: True)
    monkeypatch.setattr(evolution_native, "can_prune", lambda node, max_sim, policy: False)
    monkeypatch.setattr(
        evolution_native,
        "merge_vectors",
        lambda a_id, b_id, a_hash, b_hash, score: _MergeResult(  # noqa: ARG005
            winner_id=a_id,
            loser_id=b_id,
            meta={"source": "r5_test"},
        ),
    )

    evolution_native.evolve_once(
        graph_id=graph_id,
        node_repo=node_repo,
        edge_repo=edge_repo,
        event_repo=event_repo,
        graph_version_repo=gv_repo,
        event_context={
            "requested_profile": "strict",
            "requested_persist_mode": "strict",
            "effective_profile": "strict",
            "effective_persist_mode": "strict",
            "durability_path": "sync_strict",
        },
    )

    completed = [e for e in event_repo.events if e["kind"] == "EVOLUTION_COMPLETE"]
    assert completed, "expected EVOLUTION_COMPLETE event"
    payload = completed[-1]["payload"]
    assert payload["requested_profile"] == "strict"
    assert payload["requested_persist_mode"] == "strict"
    assert payload["effective_profile"] == "strict"
    assert payload["effective_persist_mode"] == "strict"
    assert payload["durability_path"] == "sync_strict"
