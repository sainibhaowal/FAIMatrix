"""Phase R5 unit checks: additive response/event clarity fields."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest


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


@dataclass
class _ScorecardGraphVersion:
    version: int


class _ScorecardGraphVersionRepo:
    def __init__(self, version: int) -> None:
        self._version = version

    def get_or_create(self, _session: Any, _graph_id: str) -> _ScorecardGraphVersion:
        return _ScorecardGraphVersion(version=self._version)


class _ScorecardCountRepo:
    def __init__(self, value: int) -> None:
        self._value = value

    def count(self, _graph_id: str) -> int:
        return self._value


class _ScorecardEventRepo:
    def __init__(self, events: list[Any]) -> None:
        self._events = events

    def get_by_seq(
        self,
        _session: Any,
        *,
        graph_id: str,
        after_seq: int = 0,
        limit: int = 500,
    ) -> list[Any]:
        del graph_id, after_seq, limit
        return self._events


def _scorecard_ctx_with_payload(payload: dict[str, Any]):
    event = SimpleNamespace(
        kind="DIAGNOSTICS_SNAPSHOT",
        payload=payload,
        ts=datetime(2026, 2, 20, 21, 20, 12, tzinfo=timezone.utc),
    )
    return SimpleNamespace(
        session=object(),
        event_repo=_ScorecardEventRepo([event]),
        gv_repo=_ScorecardGraphVersionRepo(version=7),
        node_repo=_ScorecardCountRepo(98),
        edge_repo=_ScorecardCountRepo(856),
    )


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
    monkeypatch.setattr(
        evolution_native, "can_prune", lambda node, max_sim, policy: False
    )
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


@pytest.mark.parametrize(
    ("payload", "expected_hash"),
    [
        (
            {
                "D_hat": 0.802645,
                "H_hat": 0.167669,
                "lambda_hat": 0.076833,
                "redundancy_R": 0.85567,
                "novelty_N": 0.0,
                "energy_E": 1.186225,
                "diagnostics_hash": "diag_hash_only",
            },
            "diag_hash_only",
        ),
        (
            {
                "graph_hash": "graph_hash_value",
                "D_hat": 0.802645,
                "H_hat": 0.167669,
                "lambda_hat": 0.076833,
                "redundancy_R": 0.85567,
                "novelty_N": 0.0,
                "energy_E": 1.186225,
            },
            "graph_hash_value",
        ),
    ],
)
def test_r5_metrics_scorecard_accepts_flat_payload(
    payload: dict[str, Any], expected_hash: str
):
    from api.routers.metrics import get_scorecard

    ctx = _scorecard_ctx_with_payload(payload)
    scorecard = asyncio.run(get_scorecard(graph_id="U:test", ctx=ctx))

    assert scorecard.graph_hash == expected_hash
    assert scorecard.graph_version == 7
    assert scorecard.node_count == 98
    assert scorecard.edge_count == 856
    assert scorecard.dimension_D == pytest.approx(0.802645)
    assert scorecard.entropy_H == pytest.approx(0.167669)
    assert scorecard.pressure_lambda == pytest.approx(0.076833)
    assert scorecard.redundancy == pytest.approx(0.85567)
    assert scorecard.novelty == pytest.approx(0.0)
    assert scorecard.energy == pytest.approx(1.186225)
    assert scorecard.computed_at == "2026-02-20T21:20:12+00:00"


def test_r5_metrics_scorecard_prefers_nested_payload():
    from api.routers.metrics import get_scorecard

    ctx = _scorecard_ctx_with_payload(
        {
            "D_hat": 0.111,
            "H_hat": 0.222,
            "lambda_hat": 0.333,
            "metrics": {
                "D": 0.999,
                "H": 0.888,
                "lambda": 0.777,
                "redundancy": 0.666,
                "novelty": 0.555,
                "energy": 0.444,
            },
            "graph_hash": "hash",
        }
    )
    scorecard = asyncio.run(get_scorecard(graph_id="U:test", ctx=ctx))

    assert scorecard.dimension_D == pytest.approx(0.999)
    assert scorecard.entropy_H == pytest.approx(0.888)
    assert scorecard.pressure_lambda == pytest.approx(0.777)
    assert scorecard.redundancy == pytest.approx(0.666)
    assert scorecard.novelty == pytest.approx(0.555)
    assert scorecard.energy == pytest.approx(0.444)
