from __future__ import annotations

from uuid import uuid4

from faim_native.index.deterministic_ann import (
    VectorPoint,
    build_vptree,
    exact_top_k,
    search_vptree,
)


def test_vptree_matches_exact_top_k():
    points = [
        VectorPoint(node_id=uuid4(), vector=(1.0, 0.0, 0.0)),
        VectorPoint(node_id=uuid4(), vector=(0.9, 0.1, 0.0)),
        VectorPoint(node_id=uuid4(), vector=(0.0, 1.0, 0.0)),
        VectorPoint(node_id=uuid4(), vector=(0.0, 0.0, 1.0)),
    ]
    query = (1.0, 0.0, 0.0)
    root = build_vptree(points)
    exact = exact_top_k(points, query, 3)
    approx = search_vptree(root, query, 3)
    assert [node_id for node_id, _score in approx] == [
        node_id for node_id, _score in exact
    ]
