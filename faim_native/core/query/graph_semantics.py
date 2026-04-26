"""Deterministic graph semantics and multi-hop traversal utilities."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import (
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)
from uuid import UUID

try:
    from faim.Faim_Native.core.query.diffusion import (
        bounded_path_scores,
        concept_neighborhood_scores,
        contradiction_penalties,
        fixed_iteration_diffusion,
    )
except (ImportError, RuntimeError):
    from core.query.diffusion import (
        bounded_path_scores,
        concept_neighborhood_scores,
        contradiction_penalties,
        fixed_iteration_diffusion,
    )


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _edge_weight(edge) -> float:
    return _clamp((edge.weight or 0) / 1e9 if edge.weight is not None else 0.0)


def build_graph_semantic_scores(
    *,
    edge_repo,
    node_repo,
    graph_id: str,
    seed_scores: Mapping[UUID, float],
    base_candidate_ids: Sequence[UUID],
    allowed_kinds: Set[str],
    max_hops: int = 2,
    max_neighbors: int = 8,
    decay: float = 0.6,
    alpha: float = 0.2,
    steps: int = 3,
) -> Tuple[
    List[UUID], Dict[UUID, Dict[str, float]], Dict[UUID, List[Dict[str, object]]]
]:
    """Return additive graph-semantic scores and multi-hop candidate expansion."""
    if not seed_scores:
        return list(base_candidate_ids), {}, {}

    visited: Set[UUID] = set(base_candidate_ids) | set(seed_scores)
    frontier: Set[UUID] = set(seed_scores)
    supportive_adj: Dict[UUID, List[Tuple[UUID, float]]] = defaultdict(list)
    contradictions: Dict[UUID, List[Tuple[UUID, float]]] = defaultdict(list)
    path_sources: Dict[UUID, List[Dict[str, object]]] = defaultdict(list)
    node_times: Dict[UUID, Optional[datetime]] = {}
    suppressed_nodes: Set[UUID] = set()

    supportive_kinds = set(allowed_kinds)
    supportive_kinds.discard("opposition")
    fetch_kinds = supportive_kinds | {"opposition"}

    for _hop in range(1, max_hops + 1):
        if not frontier:
            break

        edges = edge_repo.list_graph_neighbors(
            graph_id=graph_id,
            node_ids=sorted(frontier, key=str),
            kinds=sorted(fetch_kinds),
            limit=max(len(frontier) * max_neighbors * 6, 64),
        )
        if not edges:
            break

        candidate_node_ids: Set[UUID] = set()
        for edge in edges:
            candidate_node_ids.add(edge.src_node_id)
            candidate_node_ids.add(edge.dst_node_id)
        for node in node_repo.list_by_ids(
            graph_id=graph_id, node_ids=sorted(candidate_node_ids, key=str)
        ):
            node_times[node.node_id] = _utc(node.created_at)

        next_frontier: Set[UUID] = set()
        for edge in edges:
            weight = _edge_weight(edge)
            if weight <= 0.0:
                continue

            src = edge.src_node_id
            dst = edge.dst_node_id
            if edge.kind == "opposition":
                contradictions[src].append((dst, weight))
                contradictions[dst].append((src, weight))
                src_time = node_times.get(src)
                dst_time = node_times.get(dst)
                if src in visited and dst in visited:
                    if src_time and dst_time:
                        if src_time >= dst_time:
                            suppressed_nodes.add(dst)
                        else:
                            suppressed_nodes.add(src)
                continue

            for current, neighbor in ((src, dst), (dst, src)):
                if current not in frontier:
                    continue
                if neighbor in suppressed_nodes:
                    continue

                # Temporal contradiction suppression: if neighbor opposes an already-visited
                # newer node, keep the newer side as the traversable one.
                opposing = contradictions.get(neighbor, ())
                suppress_neighbor = False
                for other_id, opp_weight in opposing:
                    if other_id not in visited or opp_weight <= 0.0:
                        continue
                    other_time = node_times.get(other_id)
                    neighbor_time = node_times.get(neighbor)
                    if other_time and neighbor_time and other_time >= neighbor_time:
                        suppress_neighbor = True
                        break
                if suppress_neighbor:
                    suppressed_nodes.add(neighbor)
                    continue

                supportive_adj[current].append((neighbor, weight))
                path_sources[neighbor].append(
                    {
                        "from_node_id": str(current),
                        "kind": edge.kind,
                        "weight": round(weight, 6),
                        "hop": _hop,
                    }
                )
                if neighbor not in visited:
                    next_frontier.add(neighbor)
                    visited.add(neighbor)

        frontier = set(sorted(next_frontier, key=str))

    # Normalize deterministic adjacency ordering + fanout caps.
    normalized_adj: Dict[UUID, List[Tuple[UUID, float]]] = {}
    for node_id in sorted(supportive_adj, key=str):
        neighbors = sorted(
            supportive_adj[node_id],
            key=lambda item: (-float(item[1]), str(item[0])),
        )[:max_neighbors]
        normalized_adj[node_id] = neighbors

    path_scores = bounded_path_scores(
        seed_scores=seed_scores,
        adjacency=normalized_adj,
        max_hops=max_hops,
        decay=decay,
        max_neighbors=max_neighbors,
    )
    diffusion_scores = fixed_iteration_diffusion(
        seed_scores=seed_scores,
        adjacency=normalized_adj,
        alpha=alpha,
        steps=steps,
        max_neighbors=max_neighbors,
    )
    neighborhood_scores = concept_neighborhood_scores(
        support_scores=path_scores,
        adjacency=normalized_adj,
        max_neighbors=max_neighbors,
    )
    filtered_contradictions = {
        node_id: [
            (other_id, weight)
            for other_id, weight in neighbors
            if other_id not in suppressed_nodes
        ]
        for node_id, neighbors in contradictions.items()
    }

    contradiction_scores = contradiction_penalties(
        support_scores=path_scores,
        contradictions=filtered_contradictions,
    )

    expanded_ids = sorted(visited - suppressed_nodes, key=str)
    graph_scores: Dict[UUID, Dict[str, float]] = {}
    for node_id in expanded_ids:
        path_score = path_scores.get(node_id, 0.0)
        diffusion_score = diffusion_scores.get(node_id, 0.0)
        neighborhood_score = neighborhood_scores.get(node_id, 0.0)
        contradiction_score = contradiction_scores.get(node_id, 0.0)
        total = _clamp(
            0.45 * path_score
            + 0.35 * diffusion_score
            + 0.20 * neighborhood_score
            - 0.35 * contradiction_score
        )
        graph_scores[node_id] = {
            "total": round(total, 6),
            "path": round(path_score, 6),
            "diffusion": round(diffusion_score, 6),
            "neighborhood": round(neighborhood_score, 6),
            "contradiction": round(contradiction_score, 6),
        }

    explain_paths = {
        node_id: sorted(
            path_sources.get(node_id, ()),
            key=lambda item: (int(item["hop"]), item["kind"], item["from_node_id"]),  # type: ignore[call-overload]
        )[:8]
        for node_id in expanded_ids
    }
    return expanded_ids, graph_scores, explain_paths


__all__ = ["build_graph_semantic_scores"]
