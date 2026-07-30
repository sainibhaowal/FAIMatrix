"""Acceptance test for deterministic ANN exact agreement."""

from __future__ import annotations

from uuid import uuid4

from faim_native.index.deterministic_ann import (
    VectorPoint,
    build_vptree,
    exact_top_k,
    search_vptree,
)


def test_ann_matches_exact_order():
    points = [
        VectorPoint(node_id=uuid4(), vector=(1.0, 0.0, 0.0, 0.0)),
        VectorPoint(node_id=uuid4(), vector=(0.8, 0.2, 0.0, 0.0)),
        VectorPoint(node_id=uuid4(), vector=(0.0, 1.0, 0.0, 0.0)),
        VectorPoint(node_id=uuid4(), vector=(0.0, 0.0, 1.0, 0.0)),
    ]
    query = (1.0, 0.0, 0.0, 0.0)
    root = build_vptree(points)
    exact = exact_top_k(points, query, 2)
    got = search_vptree(root, query, 2)
    assert got == exact
