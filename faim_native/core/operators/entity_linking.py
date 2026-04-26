"""Deterministic entity linking and domain traversal for Phase 8."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Sequence, Set, Tuple
from uuid import UUID


@dataclass(frozen=True)
class LinkedTerm:
    surface_form: str
    canonical_form: str
    kind: str
    node_id: UUID
    score: float


def resolve_query_links(
    query_text: str, lexicon_rows: Sequence[object]
) -> List[LinkedTerm]:
    normalized = " ".join(query_text.lower().split())
    terms = set(normalized.split())
    linked: List[LinkedTerm] = []
    for row in lexicon_rows:
        surface = str(getattr(row, "surface_form", "") or "").strip().lower()
        if not surface:
            continue
        matched = surface in normalized if " " in surface else surface in terms
        if not matched:
            continue
        meta = dict(getattr(row, "meta", {}) or {})
        node_id = meta.get("node_id")
        if not node_id:
            continue
        try:
            linked.append(
                LinkedTerm(
                    surface_form=surface,
                    canonical_form=str(row.canonical_form),
                    kind=str(row.kind),
                    node_id=UUID(str(node_id)),
                    score=float(getattr(row, "score", 0.0) or 0.0),
                )
            )
        except Exception:
            continue
    linked.sort(
        key=lambda item: (-item.score, item.kind, item.surface_form, str(item.node_id))
    )
    return linked


def build_domain_candidate_scores(
    *,
    edge_repo,
    graph_id: str,
    linked_terms: Sequence[LinkedTerm],
    max_neighbors: int = 24,
) -> Tuple[List[UUID], Dict[UUID, Dict[str, float]]]:
    if not linked_terms:
        return [], {}

    seed_ids = [item.node_id for item in linked_terms]
    edges = edge_repo.list_graph_neighbors(
        graph_id=graph_id,
        node_ids=seed_ids,
        kinds=[
            "entity_alias",
            "entity_relation",
            "fact_value",
            "fact_time",
            "domain_term",
            "kb_source",
        ],
        limit=max_neighbors,
    )
    scores: Dict[UUID, Dict[str, float]] = defaultdict(
        lambda: {"entity_link": 0.0, "fact_support": 0.0, "domain_term": 0.0}
    )
    for term in linked_terms:
        bucket = scores[term.node_id]
        if term.kind == "entity_alias":
            bucket["entity_link"] = max(
                bucket["entity_link"], min(1.0, 0.7 + 0.3 * term.score)
            )
        elif term.kind == "relation_alias":
            bucket["fact_support"] = max(
                bucket["fact_support"], min(1.0, 0.5 + 0.3 * term.score)
            )
        else:
            bucket["domain_term"] = max(bucket["domain_term"], min(1.0, term.score))

    candidate_ids: Set[UUID] = set(seed_ids)
    for edge in edges:
        neighbor_id = (
            edge.dst_node_id if edge.src_node_id in seed_ids else edge.src_node_id
        )
        candidate_ids.add(neighbor_id)
        weight = max(0.0, min(1.0, float(edge.weight or 0) / 1e9))
        bucket = scores[neighbor_id]
        if edge.kind == "entity_relation":
            bucket["fact_support"] = max(bucket["fact_support"], 0.65 * weight)
        elif edge.kind in {"fact_value", "fact_time"}:
            bucket["fact_support"] = max(bucket["fact_support"], 0.55 * weight)
        elif edge.kind == "domain_term":
            bucket["domain_term"] = max(bucket["domain_term"], 0.5 * weight)
        elif edge.kind == "kb_source":
            bucket["fact_support"] = max(bucket["fact_support"], 0.45 * weight)

    return sorted(candidate_ids, key=lambda item: str(item)), dict(scores)


__all__ = ["LinkedTerm", "build_domain_candidate_scores", "resolve_query_links"]
