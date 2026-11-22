"""Multi-Hop Typed Relational Concept Graph (Zero-ML, < 1 ms Spreading).

Performs bounded, hub-dampened, decaying multi-hop spreading activation across:
1. Typed ConceptNet relational assertions (Causes, HasPrerequisite, PartOf,
   UsedFor, IsA, CapableOf, AtLocation, Synonym, FormOf, RelatedTo) when
   ``data/conceptnet_relations.json.gz`` is present.
2. Fallback/augmentation from embedded ``conceptnet_synonyms.json.gz`` and
   tenant-learned ``domain_map`` (including PPMI ``cooccurrence_bridge`` edges)
   and ``canonical_map``.

Every hop applies ``decay ** hop`` (default ``0.6 ** hop``), relation-type
weights, hub-degree dampening (``1 / log2(2 + degree)``), cycle prevention, and
a strict beam bound so multi-hop traversal completes in < 1 ms.
"""

from __future__ import annotations

import gzip
import heapq
import json
import math
import os
import threading
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from lexical import synonym_expander
from lexical.synonym_expander import WeightedExpansion, _normalize_term

_REL_DATA_PATH = Path(__file__).parent / "data" / "conceptnet_relations.json.gz"

RELATION_WEIGHTS: Dict[str, float] = {
    "Synonym": 0.95,
    "FormOf": 0.90,
    "Causes": 0.85,
    "HasPrerequisite": 0.85,
    "PartOf": 0.80,
    "UsedFor": 0.80,
    "IsA": 0.75,
    "CapableOf": 0.75,
    "AtLocation": 0.70,
    "RelatedTo": 0.65,
    "DomainBridge": 0.88,
    "Canonical": 0.92,
}

# Type alias: term -> list of (target_term, relation_name, base_weight)
TypedEdge = Tuple[str, str, float]

_rel_graph: Optional[Dict[str, List[TypedEdge]]] = None
_rel_lock = threading.Lock()
_REL_AVAILABLE: Optional[bool] = None


def _load_typed_relations() -> bool:
    """Lazy-load typed ConceptNet relations if compiled data file exists."""
    global _rel_graph, _REL_AVAILABLE
    if _REL_AVAILABLE is not None:
        return _REL_AVAILABLE
    with _rel_lock:
        if _REL_AVAILABLE is not None:
            return _REL_AVAILABLE
        try:
            with gzip.open(_REL_DATA_PATH, "rt", encoding="utf-8") as f:
                raw = json.load(f)
            parsed: Dict[str, List[TypedEdge]] = {}
            for head, edges in raw.items():
                norm_head = _normalize_term(head)
                if not norm_head or not isinstance(edges, list):
                    continue
                cleaned: List[TypedEdge] = []
                for edge in edges:
                    if isinstance(edge, (list, tuple)) and len(edge) >= 3:
                        target = _normalize_term(str(edge[0]))
                        rel = str(edge[1])
                        weight = float(edge[2])
                        if target and target != norm_head:
                            cleaned.append((target, rel, weight))
                if cleaned:
                    parsed[norm_head] = cleaned
            _rel_graph = parsed
            _REL_AVAILABLE = bool(parsed)
        except (FileNotFoundError, gzip.BadGzipFile, json.JSONDecodeError, OSError):
            _rel_graph = {}
            _REL_AVAILABLE = False
    return _REL_AVAILABLE


def _default_max_hops() -> int:
    try:
        return max(1, min(5, int(os.getenv("FAIM_RELATIONAL_MAX_HOPS", "3"))))
    except ValueError:
        return 3


def _default_decay() -> float:
    try:
        val = float(os.getenv("FAIM_RELATIONAL_HOP_DECAY", "0.6"))
        return min(0.95, max(0.1, val))
    except ValueError:
        return 0.6


def _neighbors_for_term(
    term: str,
    *,
    extra_graph: Optional[Mapping[str, Sequence[TypedEdge]]] = None,
    domain_map: Optional[Mapping[str, Sequence[str]]] = None,
    canonical_map: Optional[Mapping[str, Sequence[str]]] = None,
    use_conceptnet: bool = True,
    max_per_node: int = 12,
) -> List[TypedEdge]:
    """Collect typed outgoing edges for `term` from all available graph layers."""
    edges: List[TypedEdge] = []
    seen_targets = set()

    def _add(target: str, rel: str, weight: float) -> None:
        norm_t = _normalize_term(target)
        if not norm_t or norm_t == term or norm_t in seen_targets:
            return
        seen_targets.add(norm_t)
        edges.append((norm_t, rel, weight))

    if extra_graph:
        for target, rel, weight in extra_graph.get(term, ()):
            _add(target, rel, float(weight))

    if canonical_map:
        for target in canonical_map.get(term, ()):
            _add(target, "Canonical", RELATION_WEIGHTS["Canonical"])

    if domain_map:
        for target in domain_map.get(term, ()):
            _add(target, "DomainBridge", RELATION_WEIGHTS["DomainBridge"])

    if use_conceptnet:
        if _load_typed_relations() and _rel_graph:
            for target, rel, weight in _rel_graph.get(term, ())[:max_per_node]:
                _add(target, rel, weight)
        elif synonym_expander.is_available() and synonym_expander._synonyms:
            for target in synonym_expander._synonyms.get(term, [])[:max_per_node]:
                _add(target, "RelatedTo", RELATION_WEIGHTS["RelatedTo"])

    return edges[:max_per_node]


def spread_relational_concepts(
    seed_terms: Iterable[str],
    *,
    max_hops: Optional[int] = None,
    decay: Optional[float] = None,
    min_score: float = 0.12,
    max_expansions: int = 18,
    beam_width: int = 32,
    extra_graph: Optional[Mapping[str, Sequence[TypedEdge]]] = None,
    domain_map: Optional[Mapping[str, Sequence[str]]] = None,
    canonical_map: Optional[Mapping[str, Sequence[str]]] = None,
    use_conceptnet: bool = True,
) -> Tuple[WeightedExpansion, ...]:
    """Run bounded, hub-dampened multi-hop spreading over typed concept edges.

    Score at hop `h` along edge `(u -> v, rel, w_rel)`:
        score(v) = score(u) * decay * w_rel * hub_damp(deg(u))
    where `hub_damp(d) = 1.0 / max(1.0, log2(2.0 + d) / 2.0)`.
    """
    eff_hops = _default_max_hops() if max_hops is None else max(1, int(max_hops))
    eff_decay = _default_decay() if decay is None else min(0.95, max(0.1, float(decay)))

    seeds: List[str] = []
    seed_set = set()
    for raw in seed_terms:
        norm = _normalize_term(raw)
        if norm and norm not in seed_set:
            seed_set.add(norm)
            seeds.append(norm)
    if not seeds:
        return ()

    # Max-heap via negative score: (-score, hop, term, origin_seed, rel_chain)
    frontier: List[Tuple[float, int, str, str, Tuple[str, ...]]] = [
        (-1.0, 0, seed, seed, ()) for seed in seeds
    ]
    heapq.heapify(frontier)

    best_seen: Dict[str, Tuple[float, int, str, Tuple[str, ...]]] = {}
    expanded_per_hop: Dict[int, int] = {}

    while frontier:
        neg_score, hop, node, origin, rel_chain = heapq.heappop(frontier)
        cur_score = -neg_score
        if hop >= eff_hops:
            continue
        hop_count = expanded_per_hop.get(hop, 0)
        if hop_count >= beam_width:
            continue
        expanded_per_hop[hop] = hop_count + 1

        neighbors = _neighbors_for_term(
            node,
            extra_graph=extra_graph,
            domain_map=domain_map,
            canonical_map=canonical_map,
            use_conceptnet=use_conceptnet,
        )
        if not neighbors:
            continue

        # Hub-degree dampening prevents generic high-degree words from flooding
        hub_damp = 1.0 / max(1.0, math.log2(2.0 + len(neighbors)) / 2.0)
        next_hop = hop + 1
        for target, rel, rel_weight in neighbors:
            if target in seed_set:
                continue
            next_score = cur_score * eff_decay * float(rel_weight) * hub_damp
            if next_score < min_score:
                continue
            prev = best_seen.get(target)
            if prev is not None and prev[0] >= next_score:
                continue
            next_chain = rel_chain + (rel,)
            best_seen[target] = (next_score, next_hop, origin, next_chain)
            if next_hop < eff_hops:
                heapq.heappush(
                    frontier,
                    (-next_score, next_hop, target, origin, next_chain),
                )

    if not best_seen:
        return ()

    ranked = sorted(
        best_seen.items(),
        key=lambda item: (-item[1][0], item[1][1], item[0]),
    )[: max(1, int(max_expansions))]

    return tuple(
        WeightedExpansion(
            term=term,
            weight=round(min(0.95, float(score)), 4),
            sources=(f"relational_graph_hop{hop}", f"rel_{'_'.join(chain[:2]).lower()}"),
            origins=(origin,),
        )
        for term, (score, hop, origin, chain) in ranked
    )


__all__ = [
    "RELATION_WEIGHTS",
    "TypedEdge",
    "spread_relational_concepts",
]
