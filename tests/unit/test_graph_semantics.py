"""Unit tests for Phase 3 graph semantics scoring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from faim_native.core.query.graph_semantics import build_graph_semantic_scores


@dataclass
class _FakeEdge:
    src_node_id: object
    dst_node_id: object
    kind: str
    weight: int


@dataclass
class _FakeNode:
    node_id: object
    created_at: datetime


class _FakeEdgeRepo:
    def __init__(self, edges):
        self._edges = list(edges)

    def list_graph_neighbors(self, graph_id, node_ids, kinds=None, limit=1000):
        allowed = set(kinds or [])
        result = []
        node_ids = set(node_ids)
        for edge in self._edges:
            if kinds is not None and edge.kind not in allowed:
                continue
            if edge.src_node_id in node_ids or edge.dst_node_id in node_ids:
                result.append(edge)
        return sorted(
            result,
            key=lambda edge: (
                str(edge.src_node_id),
                str(edge.dst_node_id),
                edge.kind,
                -edge.weight,
            ),
        )[:limit]


class _FakeNodeRepo:
    def __init__(self, nodes):
        self._nodes = {node.node_id: node for node in nodes}

    def list_by_ids(self, graph_id, node_ids):
        return [self._nodes[node_id] for node_id in node_ids if node_id in self._nodes]


def test_graph_semantics_expands_multihop_and_returns_explain_paths():
    a, b, c = uuid4(), uuid4(), uuid4()
    now = datetime.now(timezone.utc)
    edge_repo = _FakeEdgeRepo(
        [
            _FakeEdge(a, b, "inheritance", int(0.9 * 1e9)),
            _FakeEdge(b, c, "synonym", int(0.8 * 1e9)),
        ]
    )
    node_repo = _FakeNodeRepo(
        [
            _FakeNode(a, now),
            _FakeNode(b, now),
            _FakeNode(c, now),
        ]
    )

    candidate_ids, graph_scores, graph_paths = build_graph_semantic_scores(
        edge_repo=edge_repo,
        node_repo=node_repo,
        graph_id="g",
        seed_scores={a: 1.0},
        base_candidate_ids=[a],
        allowed_kinds={"inheritance", "synonym", "opposition"},
        max_hops=2,
        max_neighbors=8,
        decay=0.6,
        alpha=0.2,
        steps=3,
    )

    assert c in candidate_ids
    assert graph_scores[b]["total"] > 0.0
    assert graph_scores[c]["path"] > 0.0
    assert graph_paths[b]


def test_graph_semantics_suppresses_older_contradicted_neighbor():
    seed, newer, older = uuid4(), uuid4(), uuid4()
    now = datetime.now(timezone.utc)
    edge_repo = _FakeEdgeRepo(
        [
            _FakeEdge(seed, newer, "inheritance", int(0.9 * 1e9)),
            _FakeEdge(seed, older, "inheritance", int(0.9 * 1e9)),
            _FakeEdge(newer, older, "opposition", int(1.0 * 1e9)),
        ]
    )
    node_repo = _FakeNodeRepo(
        [
            _FakeNode(seed, now),
            _FakeNode(newer, now),
            _FakeNode(older, now - timedelta(days=1)),
        ]
    )

    candidate_ids, graph_scores, _graph_paths = build_graph_semantic_scores(
        edge_repo=edge_repo,
        node_repo=node_repo,
        graph_id="g",
        seed_scores={seed: 1.0},
        base_candidate_ids=[seed],
        allowed_kinds={"inheritance", "opposition"},
        max_hops=2,
        max_neighbors=8,
        decay=0.6,
        alpha=0.2,
        steps=3,
    )

    assert newer in candidate_ids
    assert older not in candidate_ids
    assert graph_scores[newer]["contradiction"] == 0.0
