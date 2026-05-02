"""Unit tests for Phase 3 deterministic diffusion utilities."""

from __future__ import annotations

from uuid import uuid4

from faim_native.core.query.diffusion import (
    bounded_path_scores,
    concept_neighborhood_scores,
    contradiction_penalties,
    fixed_iteration_diffusion,
)


def test_bounded_path_scores_are_deterministic_and_multi_hop():
    a, b, c = uuid4(), uuid4(), uuid4()
    adjacency = {
        a: [(b, 0.9)],
        b: [(c, 0.8)],
    }
    seed_scores = {a: 1.0}

    first = bounded_path_scores(
        seed_scores=seed_scores,
        adjacency=adjacency,
        max_hops=2,
        decay=0.6,
        max_neighbors=8,
    )
    second = bounded_path_scores(
        seed_scores=seed_scores,
        adjacency=adjacency,
        max_hops=2,
        decay=0.6,
        max_neighbors=8,
    )

    assert first == second
    assert first[a] == 1.0
    assert 0.0 < first[b] <= 1.0
    assert 0.0 < first[c] < first[b]


def test_fixed_iteration_diffusion_is_deterministic_and_bounded():
    a, b, c = uuid4(), uuid4(), uuid4()
    adjacency = {
        a: [(b, 1.0)],
        b: [(c, 0.5)],
        c: [],
    }
    seed_scores = {a: 1.0}

    first = fixed_iteration_diffusion(
        seed_scores=seed_scores,
        adjacency=adjacency,
        alpha=0.2,
        steps=3,
        max_neighbors=8,
    )
    second = fixed_iteration_diffusion(
        seed_scores=seed_scores,
        adjacency=adjacency,
        alpha=0.2,
        steps=3,
        max_neighbors=8,
    )

    assert first == second
    assert all(0.0 <= value <= 1.0 for value in first.values())
    assert b in first


def test_neighborhood_and_contradiction_scores_are_bounded():
    a, b, c = uuid4(), uuid4(), uuid4()
    adjacency = {
        a: [(b, 0.9), (c, 0.6)],
        b: [(a, 0.9)],
        c: [(a, 0.6)],
    }
    support = {a: 1.0, b: 0.8, c: 0.4}
    contradictions = {
        c: [(a, 0.9)],
    }

    neighborhood = concept_neighborhood_scores(
        support_scores=support,
        adjacency=adjacency,
        max_neighbors=8,
    )
    penalties = contradiction_penalties(
        support_scores=support,
        contradictions=contradictions,
    )

    assert 0.0 <= neighborhood[a] <= 1.0
    assert 0.0 <= penalties[c] <= 1.0
    assert penalties[c] > 0.0
