"""FAIM-Native self-evolution theory generation.

Deterministic, bounded theory synthesis run inside the self-evolution loop.

A theory is a symbolic generalization derived from observable graph
structure after an evolution cycle:

- Cross-galaxy correlation: a concept appearing in >= 2 galaxies.
- Redundancy cluster: a cluster of highly-similar nodes absorbed by merging.
- Hierarchy composition: distribution of abstraction levels in the graph.
- Cognitive-type composition: which cognitive types dominate the graph.

Rules:
- Theories are gated by λ (evolution pressure): no pressure, no theory.
- Theories are bounded (max per cycle) to keep evolution deterministic.
- A theory is idempotent on a stable ``theory_id`` so repeated cycles never
  duplicate durable rows.
- Generation is best effort: never raises, never blocks the evolution result.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Default thresholds
LAMBDA_THRESHOLD: float = 0.3  # Minimum λ to emit theories
MAX_THEORIES_PER_CYCLE: int = 3
MIN_CROSS_GALAXY_GALAXIES: int = 2
MIN_CONCEPT_LENGTH: int = 3


@dataclass
class Theory:
    """A symbolic generalization derived from the graph."""

    theory_id: str
    theory_type: str  # correlation | redundancy | hierarchy | composition
    description: str
    confidence: float
    evidence_node_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "theory_id": self.theory_id,
            "theory_type": self.theory_type,
            "description": self.description,
            "confidence": self.confidence,
            "evidence_node_ids": self.evidence_node_ids,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class TheoryResult:
    """Result of one theory-generation pass."""

    theories_created: int = 0
    theory_ids: List[str] = field(default_factory=list)
    lambda_hat: float = 0.0
    skipped_candidates: int = 0
    source: str = "theory_native"
    # A theory pass is best-effort, but failures must remain observable to the
    # evolution job/API instead of looking like a legitimate empty result.
    errors: List[str] = field(default_factory=list)


def _theory_id(graph_id: str, theory_type: str, seed: str) -> str:
    """Stable idempotent theory id derived from content, not timestamps."""
    payload = json.dumps(
        {"graph": graph_id, "type": theory_type, "seed": seed},
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _extract_concepts(text: str) -> List[str]:
    """Extract stable concepts from a node's text."""
    if not text:
        return []
    # Capitalized terms (entities) and bare multi-word tokens.
    capitalized = re.findall(r"\b[A-Z][a-zA-Z]+\b", text)
    return list(
        dict.fromkeys(
            c for c in capitalized if len(c) >= MIN_CONCEPT_LENGTH
        )
    )


def _node_text(node: Any) -> str:
    """Best-effort human text for a node."""
    anchor = getattr(node, "anchor_json", None) or {}
    if isinstance(anchor, dict):
        t = anchor.get("text", "") or anchor.get("canonical", "")
        if t:
            return str(t)
    raw = getattr(node, "raw_text", None)
    if raw:
        return str(raw)
    return ""


def _load_node_texts(
    session: Any,
    tenant_id: str,
    graph_id: str,
    node_ids: List[str],
    errors: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Build node_id → text map from the Representation V2 sidecar.

    Real ingestion stores normalized text in ``node_repr_v2``; anchor_json
    on nodes only carries BlockAnchor metadata. Best effort: on any failure
    returns an empty map and theory generation falls back to anchor text.
    """
    if not node_ids or session is None:
        return {}
    try:
        from store.pg.models_faim import NodeRepresentationV2Model

        rows = (
            session.query(NodeRepresentationV2Model)
            .filter(
                NodeRepresentationV2Model.tenant_id == tenant_id,
                NodeRepresentationV2Model.graph_id == graph_id,
                NodeRepresentationV2Model.node_id.in_(node_ids),
            )
            .all()
        )
        return {
            str(r.node_id): (r.normalized_text or "")
            for r in rows
            if r.normalized_text
        }
    except Exception as exc:
        if errors is not None:
            errors.append(f"representation_load:{type(exc).__name__}")
        return {}


# =============================================================================
# Theory generators
# =============================================================================


def _cross_galaxy_correlations(
    graph_id: str,
    nodes: List[Any],
    node_texts: Dict[str, str],
) -> List[Theory]:
    """Concepts appearing in >= 2 galaxies → correlation theories."""
    concept_galaxies: Dict[str, Dict[str, List[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for node in nodes:
        galaxy = getattr(node, "galaxy_id", None) or ""
        if not galaxy:
            continue
        text = node_texts.get(str(node.node_id), "") or _node_text(node)
        for concept in _extract_concepts(text):
            concept_galaxies[concept][galaxy].append(str(node.node_id))

    theories: List[Theory] = []
    for concept, galaxies in concept_galaxies.items():
        if len(galaxies) < MIN_CROSS_GALAXY_GALAXIES:
            continue
        galaxy_ids = sorted(galaxies.keys())
        evidence = sorted(
            str(nid)
            for gids in galaxies.values()
            for nid in gids
        )
        confidence = min(
            0.95,
            0.5 + 0.15 * (len(galaxies) - MIN_CROSS_GALAXY_GALAXIES),
        )
        theories.append(
            Theory(
                theory_id=_theory_id(graph_id, "correlation", concept),
                theory_type="correlation",
                description=(
                    f"'{concept}' recurs across {len(galaxies)} galaxies: "
                    + ", ".join(galaxy_ids)
                ),
                confidence=round(confidence, 4),
                evidence_node_ids=evidence[:16],
                metadata={
                    "concept": concept,
                    "galaxies": galaxy_ids,
                    "galaxy_count": len(galaxies),
                },
            )
        )
    return theories


def _redundancy_cluster_theory(
    graph_id: str,
    nodes: List[Any],
    redundant_pairs: List[tuple],
    node_texts: Dict[str, str],
) -> List[Theory]:
    """Highly-similar node pairs → consolidation theory."""
    if not redundant_pairs:
        return []

    member_ids = sorted({str(a) for a, _, _ in redundant_pairs})
    by_id = {str(n.node_id): n for n in nodes}
    concepts: Counter = Counter()
    for nid in member_ids[:32]:
        node = by_id.get(nid)
        if node is None:
            continue
        text = node_texts.get(nid, "") or _node_text(node)
        for concept in _extract_concepts(text):
            concepts[concept] += 1
    top_concept = concepts.most_common(1)[0][0] if concepts else "shared"

    best_sim = max(sim for _, _, sim in redundant_pairs)
    return [
        Theory(
            theory_id=_theory_id(graph_id, "redundancy", "cluster"),
            theory_type="redundancy",
            description=(
                f"Redundancy cluster of {len(member_ids)} nodes centers on "
                f"'{top_concept}' (peak similarity {best_sim:.2f}); merging "
                "consolidates shared meaning."
            ),
            confidence=round(min(0.9, 0.5 + best_sim * 0.4), 4),
            evidence_node_ids=member_ids[:16],
            metadata={
                "cluster_size": len(member_ids),
                "peak_similarity": round(best_sim, 4),
                "representative_concept": top_concept,
            },
        )
    ]


def _hierarchy_composition_theory(
    graph_id: str,
    nodes: List[Any],
) -> List[Theory]:
    """Abstraction-level distribution → hierarchy theory."""
    levels = Counter(int(getattr(n, "level", 0) or 0) for n in nodes)
    if not levels:
        return []
    max_level = max(levels.keys())
    if max_level < 1:
        return []

    total = sum(levels.values())
    leaf_fraction = levels.get(0, 0) / total if total else 0.0
    macro_count = sum(
        count for level, count in levels.items() if level >= 1
    )
    return [
        Theory(
            theory_id=_theory_id(graph_id, "hierarchy", f"depth-{max_level}"),
            theory_type="hierarchy",
            description=(
                f"Graph reaches abstraction depth {max_level} across "
                f"{macro_count} composite nodes ({leaf_fraction:.0%} leaves); "
                "invented abstractions are being reused by the memory."
            ),
            confidence=round(0.55 + 0.05 * min(max_level, 6), 4),
            evidence_node_ids=sorted(
                str(n.node_id) for n in nodes if int(getattr(n, "level", 0) or 0) >= 1
            )[:16],
            metadata={
                "max_level": max_level,
                "macro_count": macro_count,
                "leaf_fraction": round(leaf_fraction, 4),
                "level_distribution": {
                    str(k): v for k, v in sorted(levels.items())
                },
            },
        )
    ]


def _cognitive_composition_theory(
    graph_id: str,
    nodes: List[Any],
) -> List[Theory]:
    """Dominant cognitive types → composition theory."""
    types = Counter(
        str(getattr(n, "cognitive_type", "unknown") or "unknown") for n in nodes
    )
    if not types:
        return []
    dominant, count = types.most_common(1)[0]
    total = sum(types.values())
    if total == 0:
        return []
    share = count / total
    if share < 0.4:
        return []
    return [
        Theory(
            theory_id=_theory_id(graph_id, "composition", dominant),
            theory_type="composition",
            description=(
                f"'{dominant}' cognition dominates the graph "
                f"({share:.0%} of {total} nodes); ingest mix is "
                "skewed toward this mode."
            ),
            confidence=round(0.5 + share * 0.4, 4),
            evidence_node_ids=sorted(
                str(n.node_id)
                for n in nodes
                if (getattr(n, "cognitive_type", None) or "") == dominant
            )[:16],
            metadata={
                "dominant_type": dominant,
                "share": round(share, 4),
                "total_nodes": total,
                "type_distribution": {
                    str(k): v for k, v in types.most_common(8)
                },
            },
        )
    ]


# =============================================================================
# Main entry point
# =============================================================================


def run_theory_cycle(
    graph_id: str,
    *,
    session: Any,
    node_repo: Any,
    theory_repo: Any,
    graph_version: int = 0,
    lambda_hat: float = 0.0,
    lambda_threshold: float = LAMBDA_THRESHOLD,
    max_theories: int = MAX_THEORIES_PER_CYCLE,
    redundant_pairs: Optional[List[tuple]] = None,
) -> TheoryResult:
    """Run one bounded theory-generation pass on the graph.

    Args:
        graph_id: Target graph identifier.
        session: SQLAlchemy session.
        node_repo: Node repository (used to load the graph snapshot).
        theory_repo: Theory repository used to persist theories.
        graph_version: Version the theories are attributed to.
        lambda_hat: Evolution pressure measured after the cycle.
        lambda_threshold: Minimum λ to emit theories.
        max_theories: Hard cap on theories per cycle.
        redundant_pairs: Optional pre-computed redundant pairs
            ([(a_id, b_id, sim), ...]). If None, the pass tries to derive
            them from the node repo (best effort).

    Returns:
        TheoryResult with the durable theory ids created.
    """
    result = TheoryResult(lambda_hat=lambda_hat)
    if lambda_hat < lambda_threshold:
        result.skipped_candidates += 1
        return result

    try:
        nodes = node_repo.list_nodes(graph_id, limit=1000)
    except Exception as exc:
        result.errors.append(f"node_load:{type(exc).__name__}")
        result.skipped_candidates += 1
        return result
    if not nodes:
        result.skipped_candidates += 1
        return result

    node_texts = _load_node_texts(
        session,
        getattr(node_repo, "tenant_id", ""),
        graph_id,
        [str(n.node_id) for n in nodes],
        errors=result.errors,
    )

    candidates: List[Theory] = []
    candidates.extend(_cross_galaxy_correlations(graph_id, nodes, node_texts))
    candidates.extend(_hierarchy_composition_theory(graph_id, nodes))
    candidates.extend(_cognitive_composition_theory(graph_id, nodes))

    if redundant_pairs is None:
        redundant_pairs = []
        try:
            redundant_pairs = node_repo.find_redundant_pairs(
                graph_id, threshold=0.85, limit=200
            )
        except Exception as exc:
            result.errors.append(f"redundancy_scan:{type(exc).__name__}")
            redundant_pairs = []
    if redundant_pairs:
        candidates.extend(
            _redundancy_cluster_theory(graph_id, nodes, redundant_pairs, node_texts)
        )

    # Deterministic order + bound.
    candidates.sort(key=lambda t: (-t.confidence, t.theory_id))
    chosen = candidates[: max(1, min(int(max_theories), len(candidates)))]

    for theory in chosen:
        try:
            theory_repo.upsert(
                {
                    "theory_id": theory.theory_id,
                    "graph_id": graph_id,
                    "theory_type": theory.theory_type,
                    "description": theory.description,
                    "confidence": theory.confidence,
                    "evidence_node_ids": theory.evidence_node_ids,
                    "metadata": theory.metadata,
                    "graph_version": int(graph_version or 0),
                }
            )
            result.theories_created += 1
            result.theory_ids.append(theory.theory_id)
        except Exception as exc:
            # Persistence is best effort; never block evolution.
            result.skipped_candidates += 1
            result.errors.append(f"theory_persist:{type(exc).__name__}")

    return result


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "Theory",
    "TheoryResult",
    "LAMBDA_THRESHOLD",
    "MAX_THEORIES_PER_CYCLE",
    "run_theory_cycle",
]
