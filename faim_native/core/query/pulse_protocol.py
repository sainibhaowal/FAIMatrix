"""Shared cognitive pulse event protocol for query and graph reasoning.

The protocol is intentionally deterministic: event IDs and trace IDs are derived
from graph/query/node/stage/source values so tests and UI state remain stable.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


PULSE_PROTOCOL_VERSION = "pulse-v2"


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _stable_hash(parts: Iterable[Any]) -> str:
    raw = "||".join(str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def make_pulse_event(
    *,
    graph_id: str,
    node_id: str,
    stage: str,
    source: str,
    strength: float,
    query_hash: Optional[str] = None,
    hop: Optional[int] = None,
    contribution: float = 0.0,
    evidence: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Create one normalized pulse event."""
    event_id = _stable_hash(
        [
            PULSE_PROTOCOL_VERSION,
            graph_id,
            query_hash or "",
            node_id,
            stage,
            source,
            hop if hop is not None else "",
        ]
    )
    return {
        "event_id": event_id,
        "protocol": PULSE_PROTOCOL_VERSION,
        "graph_id": graph_id,
        "query_hash": query_hash,
        "node_id": node_id,
        "hop": hop,
        "stage": stage,
        "source": source,
        "strength": round(_clamp(float(strength)), 6),
        "contribution": round(float(contribution), 6),
        "evidence": dict(evidence or {}),
    }


def summarize_events(events: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    """Count events by source and stage for compact UI legends."""
    summary: Dict[str, int] = {}
    for event in events:
        source = str(event.get("source") or "unknown")
        stage = str(event.get("stage") or "unknown")
        summary[f"source:{source}"] = summary.get(f"source:{source}", 0) + 1
        summary[f"stage:{stage}"] = summary.get(f"stage:{stage}", 0) + 1
    return dict(sorted(summary.items(), key=lambda item: item[0]))


def build_node_reason_ledger(
    *,
    graph_id: str,
    query_hash: Optional[str],
    node_id: str,
    score: float,
    score_components: Mapping[str, Any],
    explain_payload: Mapping[str, Any],
) -> Dict[str, Any]:
    """Build a reusable per-node reason ledger from query explain payload."""
    events: List[Dict[str, Any]] = []
    components = {
        str(key): float(value or 0.0)
        for key, value in dict(score_components or {}).items()
        if isinstance(value, (int, float))
    }

    semantic_signature = dict(explain_payload.get("semantic_signature") or {})
    phase_b = dict(explain_payload.get("phaseB_query_expansion") or {})
    domain = dict(explain_payload.get("domain_relevance") or {})
    graph_score = dict(explain_payload.get("phase3_graph_score") or {})
    reranker = dict(explain_payload.get("phase4_reranker") or {})
    late = dict(explain_payload.get("phaseC_late_interaction") or {})
    fusion = dict(explain_payload.get("fusion_summary") or {})
    query_fusion = dict(explain_payload.get("query_fusion_summary") or {})

    base_strength = _clamp(abs(float(score or 0.0)))
    events.append(
        make_pulse_event(
            graph_id=graph_id,
            query_hash=query_hash,
            node_id=node_id,
            stage="candidate_score",
            source="faim_core_score",
            strength=base_strength,
            contribution=float(score or 0.0),
            evidence={
                "score_components": components,
                "final_score": float(score or 0.0),
            },
        )
    )

    source_counts = dict(phase_b.get("source_counts") or {})
    expansion_count = int(phase_b.get("expansion_count") or len(phase_b.get("expansions") or []))
    if source_counts or expansion_count:
        for source, count in sorted(source_counts.items(), key=lambda item: str(item[0])):
            events.append(
                make_pulse_event(
                    graph_id=graph_id,
                    query_hash=query_hash,
                    node_id=node_id,
                    stage="query_expansion",
                    source=str(source),
                    strength=_clamp(float(count) / max(expansion_count, 1)),
                    contribution=float(count),
                    evidence={
                        "expansion_count": expansion_count,
                        "source_count": count,
                        "sample_expansions": list(phase_b.get("expansions") or [])[:12],
                    },
                )
            )

    registry = dict(phase_b.get("semantic_registry") or {})
    if registry:
        events.append(
            make_pulse_event(
                graph_id=graph_id,
                query_hash=query_hash,
                node_id=node_id,
                stage="semantic_registry",
                source="semantic_registry",
                strength=_clamp(float(registry.get("expansion_count") or 0.0) / 20.0),
                contribution=float(registry.get("expansion_count") or 0.0),
                evidence=registry,
            )
        )

    domain_scores = dict(domain.get("node_scores") or {})
    if domain_scores or domain.get("query_links"):
        domain_strength = _clamp(sum(float(v or 0.0) for v in domain_scores.values()))
        events.append(
            make_pulse_event(
                graph_id=graph_id,
                query_hash=query_hash,
                node_id=node_id,
                stage="domain_memory",
                source="domain_memory_bundle",
                strength=domain_strength,
                contribution=domain_strength,
                evidence={
                    "node_scores": domain_scores,
                    "query_links": list(domain.get("query_links") or [])[:12],
                    "candidate_count": int(domain.get("candidate_count") or 0),
                },
            )
        )

    graph_paths = list(explain_payload.get("phase3_graph_paths") or [])
    for idx, path in enumerate(graph_paths[:12]):
        hop = int(dict(path).get("hop") or idx + 1)
        weight = float(dict(path).get("weight") or 0.0)
        events.append(
            make_pulse_event(
                graph_id=graph_id,
                query_hash=query_hash,
                node_id=node_id,
                stage="graph_traversal",
                source=f"edge:{dict(path).get('kind') or 'unknown'}",
                hop=hop,
                strength=weight,
                contribution=weight,
                evidence=dict(path),
            )
        )
    if graph_score:
        for key in ("path", "diffusion", "neighborhood", "contradiction"):
            value = float(graph_score.get(key) or 0.0)
            if value == 0.0:
                continue
            events.append(
                make_pulse_event(
                    graph_id=graph_id,
                    query_hash=query_hash,
                    node_id=node_id,
                    stage="graph_score",
                    source=f"graph_{key}",
                    strength=abs(value),
                    contribution=value,
                    evidence=graph_score,
                )
            )

    reranker_components = dict(reranker.get("components") or {})
    if reranker_components:
        for key, value in sorted(reranker_components.items(), key=lambda item: str(item[0])):
            if not isinstance(value, (int, float)) or float(value) == 0.0:
                continue
            events.append(
                make_pulse_event(
                    graph_id=graph_id,
                    query_hash=query_hash,
                    node_id=node_id,
                    stage="reranker",
                    source=f"reranker:{key}",
                    strength=abs(float(value)),
                    contribution=float(value),
                    evidence={"components": reranker_components},
                )
            )

    late_components = dict(late.get("components") or {})
    if late_components:
        for key, value in sorted(late_components.items(), key=lambda item: str(item[0])):
            if not isinstance(value, (int, float)) or float(value) == 0.0:
                continue
            events.append(
                make_pulse_event(
                    graph_id=graph_id,
                    query_hash=query_hash,
                    node_id=node_id,
                    stage="late_interaction",
                    source=f"late_interaction:{key}",
                    strength=abs(float(value)),
                    contribution=float(value),
                    evidence={
                        "matched_units": dict(late.get("matched_units") or {}),
                        "components": late_components,
                    },
                )
            )

    signature_counts = {
        "alias_families": len(semantic_signature.get("alias_families") or []),
        "transliterated_tokens": len(semantic_signature.get("transliterated_tokens") or []),
        "stem_families": len(semantic_signature.get("stem_families") or []),
        "relation_cues": len(semantic_signature.get("relation_cues") or []),
        "value_cues": len(semantic_signature.get("value_cues") or []),
        "temporal_cues": len(semantic_signature.get("temporal_cues") or []),
        "semantic_phrase_buckets": int(semantic_signature.get("semantic_phrase_bucket_count") or 0),
        "concept_buckets": int(semantic_signature.get("concept_bucket_count") or 0),
        "morphology_buckets": int(semantic_signature.get("morphology_bucket_count") or 0),
    }
    for source, count in signature_counts.items():
        if count <= 0:
            continue
        events.append(
            make_pulse_event(
                graph_id=graph_id,
                query_hash=query_hash,
                node_id=node_id,
                stage="semantic_signature",
                source=source,
                strength=_clamp(float(count) / 16.0),
                contribution=float(count),
                evidence={"count": count},
            )
        )

    active_layers = list(fusion.get("active_layers") or [])
    strongest_layers = list(fusion.get("strongest_layers") or [])
    confidence = _clamp(
        max([float(event.get("strength") or 0.0) for event in events] + [base_strength])
    )
    return {
        "protocol": PULSE_PROTOCOL_VERSION,
        "trace_id": _stable_hash([PULSE_PROTOCOL_VERSION, graph_id, query_hash or "", node_id]),
        "node_id": node_id,
        "confidence": round(confidence, 6),
        "event_count": len(events),
        "active_layers": active_layers,
        "strongest_layers": strongest_layers,
        "source_summary": summarize_events(events),
        "why_glowing": {
            "expansion_sources": source_counts,
            "graph_hops": graph_paths[:12],
            "reranker_components": reranker_components,
            "late_interaction_components": late_components,
            "domain_memory": {
                "node_scores": domain_scores,
                "query_links": list(domain.get("query_links") or [])[:12],
            },
            "semantic_signature": signature_counts,
            "candidate_pool": dict(query_fusion.get("candidate_pool") or {}),
        },
        "events": events,
    }


def build_pulse_trace_from_path(
    *,
    graph_id: str,
    path_nodes: Sequence[str],
    steps: Sequence[Mapping[str, Any]],
    layer_summary: Mapping[str, int],
    source: str,
) -> Dict[str, Any]:
    """Wrap path steps in the shared pulse protocol envelope."""
    trace_id = _stable_hash([PULSE_PROTOCOL_VERSION, graph_id, *path_nodes, source])
    events: List[Dict[str, Any]] = []
    for step in steps:
        node_id = str(step.get("node_id") or "")
        if not node_id:
            continue
        events.append(
            make_pulse_event(
                graph_id=graph_id,
                node_id=node_id,
                stage="graph_path",
                source="path_step",
                hop=int(step.get("index") or 0),
                strength=float(step.get("pulse_strength") or 0.0),
                contribution=float(step.get("pulse_strength") or 0.0),
                evidence={
                    "evidence_sources": list(step.get("evidence_sources") or []),
                    "semantic_signature": dict(step.get("semantic_signature") or {}),
                    "via_edge": step.get("via_edge"),
                },
            )
        )
    combined_summary = dict(layer_summary)
    for key, value in summarize_events(events).items():
        combined_summary[key] = combined_summary.get(key, 0) + value
    return {
        "protocol": PULSE_PROTOCOL_VERSION,
        "compatible_protocols": ["pulse-v1"],
        "trace_id": trace_id,
        "path_length": max(len(path_nodes) - 1, 0),
        "source": source,
        "layer_summary": dict(sorted(combined_summary.items(), key=lambda item: item[0])),
        "events": events,
        "steps": list(steps),
    }


__all__ = [
    "PULSE_PROTOCOL_VERSION",
    "build_node_reason_ledger",
    "build_pulse_trace_from_path",
    "make_pulse_event",
    "summarize_events",
]
