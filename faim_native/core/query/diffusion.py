"""Deterministic graph diffusion and path scoring utilities."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Mapping, Tuple, TypeVar


NodeId = TypeVar("NodeId")


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _normalize_scores(scores: Mapping[NodeId, float]) -> Dict[NodeId, float]:
    if not scores:
        return {}
    max_value = max(float(v) for v in scores.values()) or 1.0
    return {
        node_id: _clamp(float(value) / max_value)
        for node_id, value in sorted(scores.items(), key=lambda item: str(item[0]))
    }


def bounded_path_scores(
    *,
    seed_scores: Mapping[NodeId, float],
    adjacency: Mapping[NodeId, Iterable[Tuple[NodeId, float]]],
    max_hops: int = 2,
    decay: float = 0.6,
    max_neighbors: int = 8,
) -> Dict[NodeId, float]:
    """Compute deterministic bounded path support from seed nodes."""
    if not seed_scores or max_hops < 1:
        return {}

    frontier: Dict[NodeId, float] = {
        node_id: _clamp(float(score))
        for node_id, score in sorted(seed_scores.items(), key=lambda item: str(item[0]))
        if float(score) > 0.0
    }
    totals: Dict[NodeId, float] = dict(frontier)

    for _hop in range(1, max_hops + 1):
        next_frontier: Dict[NodeId, float] = defaultdict(float)
        for node_id in sorted(frontier, key=str):
            base_score = frontier[node_id]
            neighbors = sorted(
                adjacency.get(node_id, ()),
                key=lambda item: (-float(item[1]), str(item[0])),
            )[:max_neighbors]
            for neighbor_id, weight in neighbors:
                contribution = base_score * _clamp(weight) * decay
                if contribution <= 0.0:
                    continue
                next_frontier[neighbor_id] = max(
                    float(next_frontier.get(neighbor_id, 0.0)),
                    contribution,
                )
                totals[neighbor_id] = max(float(totals.get(neighbor_id, 0.0)), contribution)
        frontier = dict(next_frontier)
        if not frontier:
            break

    return _normalize_scores(totals)


def fixed_iteration_diffusion(
    *,
    seed_scores: Mapping[NodeId, float],
    adjacency: Mapping[NodeId, Iterable[Tuple[NodeId, float]]],
    alpha: float = 0.2,
    steps: int = 3,
    max_neighbors: int = 8,
) -> Dict[NodeId, float]:
    """Run deterministic fixed-step diffusion on a weighted graph."""
    if not seed_scores:
        return {}

    base = _normalize_scores(seed_scores)
    current: Dict[NodeId, float] = dict(base)

    for _step in range(max(0, steps)):
        incoming: Dict[NodeId, float] = defaultdict(float)
        for src_node in sorted(current, key=str):
            src_value = current[src_node]
            neighbors = sorted(
                adjacency.get(src_node, ()),
                key=lambda item: (-float(item[1]), str(item[0])),
            )[:max_neighbors]
            total_weight = sum(_clamp(weight) for _neighbor, weight in neighbors) or 1.0
            for neighbor_id, weight in neighbors:
                incoming[neighbor_id] += src_value * (_clamp(weight) / total_weight)

        updated: Dict[NodeId, float] = {}
        all_nodes = sorted(set(base) | set(current) | set(incoming), key=str)
        for node_id in all_nodes:
            restart = base.get(node_id, 0.0)
            propagated = incoming.get(node_id, 0.0)
            updated[node_id] = _clamp((1.0 - alpha) * restart + alpha * propagated)
        current = updated

    return _normalize_scores(current)


def concept_neighborhood_scores(
    *,
    support_scores: Mapping[NodeId, float],
    adjacency: Mapping[NodeId, Iterable[Tuple[NodeId, float]]],
    max_neighbors: int = 8,
) -> Dict[NodeId, float]:
    """Compute neighborhood coherence from nearby supported nodes."""
    if not support_scores:
        return {}

    totals: Dict[NodeId, float] = defaultdict(float)
    for node_id in sorted(adjacency, key=str):
        neighbors = sorted(
            adjacency.get(node_id, ()),
            key=lambda item: (-float(item[1]), str(item[0])),
        )[:max_neighbors]
        if not neighbors:
            continue
        value = 0.0
        for neighbor_id, weight in neighbors:
            value += support_scores.get(neighbor_id, 0.0) * _clamp(weight)
        if value > 0.0:
            totals[node_id] = value / max(len(neighbors), 1)
    return _normalize_scores(totals)


def contradiction_penalties(
    *,
    support_scores: Mapping[NodeId, float],
    contradictions: Mapping[NodeId, Iterable[Tuple[NodeId, float]]],
) -> Dict[NodeId, float]:
    """Compute contradiction penalties from opposition relationships."""
    penalties: Dict[NodeId, float] = defaultdict(float)
    for node_id in sorted(contradictions, key=str):
        max_penalty = 0.0
        for other_id, weight in sorted(contradictions[node_id], key=lambda item: (-float(item[1]), str(item[0]))):
            max_penalty = max(max_penalty, support_scores.get(other_id, 0.0) * _clamp(weight))
        if max_penalty > 0.0:
            penalties[node_id] = _clamp(max_penalty)
    return penalties


__all__ = [
    "bounded_path_scores",
    "fixed_iteration_diffusion",
    "concept_neighborhood_scores",
    "contradiction_penalties",
]
