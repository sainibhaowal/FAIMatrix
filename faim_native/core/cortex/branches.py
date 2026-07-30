"""Parallel Cortex reasoning branches.

Phase 1 keeps these branches deterministic and structured.
"""

from __future__ import annotations

import asyncio
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

from .schemas import CortexReasoningNode

STOPWORDS = {
    "the",
    "and",
    "for",
    "that",
    "this",
    "with",
    "from",
    "into",
    "what",
    "when",
    "where",
    "how",
    "why",
    "does",
    "did",
    "are",
    "was",
    "were",
    "will",
    "have",
    "has",
    "had",
    "your",
    "you",
    "about",
    "then",
    "than",
}


@dataclass(frozen=True)
class BranchOutput:
    """One branch output."""

    node: CortexReasoningNode


def _node_ids(results: Sequence[Dict[str, Any]]) -> List[str]:
    return [str(item.get("node_id", "")) for item in results if item.get("node_id")]


def _supporting_texts(answer_packet: Dict[str, Any]) -> List[str]:
    spans = answer_packet.get("supporting_spans") or []
    return [str(span.get("text", "")).strip() for span in spans if span.get("text")]


def _source_labels(results: Sequence[Dict[str, Any]]) -> List[str]:
    labels: List[str] = []
    for item in results:
        evidence = item.get("evidence") or {}
        raw_id = evidence.get("raw_id")
        anchor = evidence.get("anchor") or {}
        filename = anchor.get("filename") or raw_id or item.get("node_id")
        page = anchor.get("page") or anchor.get("page_number")
        label = f"{filename}"
        if page is not None:
            label = f"{label} p.{page}"
        labels.append(label)
    return labels


async def recall_branch(state: Dict[str, Any]) -> BranchOutput:
    answer_packet = state["answer_packet"]
    texts = _supporting_texts(answer_packet)
    evidence_ids = _node_ids(state["results"])
    summary = (
        texts[0]
        if texts
        else "No supporting span was strong enough to anchor a direct recall."
    )
    node = CortexReasoningNode(
        branch="recall",
        title="Recall branch",
        summary=summary,
        evidence_node_ids=evidence_ids[:5],
        confidence=float(answer_packet.get("confidence") or 0.0),
        output={
            "supporting_spans": answer_packet.get("supporting_spans") or [],
            "direct_answer": answer_packet.get("direct_answer") or "",
        },
    )
    return BranchOutput(node=node)


async def timeline_branch(state: Dict[str, Any]) -> BranchOutput:
    answer_packet = state["answer_packet"]
    spans = answer_packet.get("supporting_spans") or []
    current = [span for span in spans if span.get("temporal_status") == "CURRENT"]
    historical = [span for span in spans if span.get("temporal_status") != "CURRENT"]
    summary = "Timeline branch found no clear ordering signal."
    if current and historical:
        summary = "Current evidence follows older evidence in the retrieved memory."
    elif spans:
        summary = "Timeline branch found a single dominant time slice."
    node = CortexReasoningNode(
        branch="timeline",
        title="Timeline branch",
        summary=summary,
        evidence_node_ids=_node_ids(state["results"])[:5],
        confidence=float(answer_packet.get("confidence") or 0.0),
        output={
            "current_spans": current,
            "historical_spans": historical,
        },
    )
    return BranchOutput(node=node)


async def contradiction_branch(state: Dict[str, Any]) -> BranchOutput:
    answer_packet = state["answer_packet"]
    notes = list(answer_packet.get("contradiction_notes") or [])
    summary = (
        notes[0]
        if notes
        else "No contradiction signal was detected in the current result set."
    )
    node = CortexReasoningNode(
        branch="contradiction",
        title="Contradiction branch",
        summary=summary,
        evidence_node_ids=_node_ids(state["results"])[:5],
        confidence=max(0.0, float(answer_packet.get("confidence") or 0.0) - 0.15),
        output={"contradiction_notes": notes},
    )
    return BranchOutput(node=node)


async def concept_branch(state: Dict[str, Any]) -> BranchOutput:
    texts = _supporting_texts(state["answer_packet"])
    words: Counter[str] = Counter()
    for text in texts[:8]:
        for raw in re.findall(r"[A-Za-z][A-Za-z0-9_-]+", text.lower()):
            if raw in STOPWORDS or len(raw) <= 2:
                continue
            words[raw] += 1
    concepts = [word for word, _ in words.most_common(4)]
    summary = (
        f"Emerging concept: {', '.join(concepts[:2])}"
        if concepts
        else "No stable concept cluster was strong enough to name."
    )
    node = CortexReasoningNode(
        branch="concept",
        title="Concept branch",
        summary=summary,
        evidence_node_ids=_node_ids(state["results"])[:5],
        confidence=0.5 if concepts else 0.2,
        output={"concepts": concepts},
    )
    return BranchOutput(node=node)


async def prediction_branch(state: Dict[str, Any]) -> BranchOutput:
    answer_packet = state["answer_packet"]
    confidence = float(answer_packet.get("confidence") or 0.0)
    if confidence >= 0.75 and not answer_packet.get("contradiction_notes"):
        prediction = (
            "The current memory likely remains stable unless new evidence arrives."
        )
    elif answer_packet.get("contradiction_notes"):
        prediction = (
            "A clarification or memory writeback may be needed before this can harden."
        )
    else:
        prediction = "The next best step is to request one more grounded memory slice."
    node = CortexReasoningNode(
        branch="prediction",
        title="Prediction branch",
        summary=prediction,
        evidence_node_ids=_node_ids(state["results"])[:5],
        confidence=max(0.1, confidence - 0.1),
        output={"predictions": [prediction]},
    )
    return BranchOutput(node=node)


async def provenance_branch(state: Dict[str, Any]) -> BranchOutput:
    answer_packet = state["answer_packet"]
    results = state["results"]
    sources = []
    for item in results[:8]:
        evidence = item.get("evidence") or {}
        anchor = evidence.get("anchor") or {}
        sources.append(
            {
                "node_id": item.get("node_id"),
                "raw_id": evidence.get("raw_id"),
                "block_id": evidence.get("block_id"),
                "anchor": anchor,
                "score": item.get("score", 0.0),
            }
        )
    labels = _source_labels(results[:5])
    summary = (
        f"Primary sources: {', '.join(labels[:3])}"
        if labels
        else "No provenance trail was available."
    )
    node = CortexReasoningNode(
        branch="provenance",
        title="Provenance branch",
        summary=summary,
        evidence_node_ids=_node_ids(results)[:5],
        confidence=float(answer_packet.get("confidence") or 0.0),
        output={"sources": sources},
    )
    return BranchOutput(node=node)


async def continuity_branch(state: Dict[str, Any]) -> BranchOutput:
    recent_turns = list(state.get("recent_turns") or [])
    if not recent_turns:
        summary = "No prior turns exist in this session yet."
        continuity = []
        unresolved = []
    else:
        continuity = [
            {
                "turn_id": turn.turn_id,
                "query_text": turn.query_text,
                "answer_mode": turn.answer_mode,
                "task_type": turn.task_type.value,
                "confidence": turn.confidence,
                "narrative": turn.narrative,
                "open_question_count": turn.open_question_count,
                "contradiction_count": turn.contradiction_count,
                "created_at": turn.created_at.isoformat(),
            }
            for turn in recent_turns
        ]
        latest = recent_turns[-1]
        summary = f"Session continuity follows prior turn '{latest.query_text[:80]}'."
        unresolved = [
            turn.query_text
            for turn in recent_turns
            if turn.open_question_count > 0 or turn.contradiction_count > 0
        ]
    node = CortexReasoningNode(
        branch="continuity",
        title="Continuity branch",
        summary=summary,
        evidence_node_ids=_node_ids(state["results"])[:5],
        confidence=0.6 if recent_turns else 0.2,
        output={
            "recent_turns": continuity,
            "unresolved_threads": unresolved[:5],
        },
    )
    return BranchOutput(node=node)


def _serialize_reasoning_path(path) -> Dict[str, Any]:
    path_dict = path.to_dict()
    node_ids = [str(path.start_node)] + [str(hop.next_node_id) for hop in path.hops]
    edge_ids = [str(hop.edge_id) for hop in path.hops]
    path_dict["node_ids"] = node_ids
    path_dict["edge_ids"] = edge_ids
    return path_dict


async def traversal_branch(state: Dict[str, Any]) -> BranchOutput:
    if not state.get("planned_enable_multi_hop"):
        node = CortexReasoningNode(
            branch="traversal",
            title="Traversal branch",
            summary="Multi-hop traversal was not required for this turn.",
            evidence_node_ids=_node_ids(state["results"])[:5],
            confidence=0.0,
            output={
                "enabled": False,
                "reason": "planner_disabled_multi_hop",
                "paths": [],
                "exact_match": False,
            },
        )
        return BranchOutput(node=node)

    session = state.get("session")
    if session is None:
        node = CortexReasoningNode(
            branch="traversal",
            title="Traversal branch",
            summary="Traversal session was unavailable, so exact path execution was skipped.",
            evidence_node_ids=_node_ids(state["results"])[:5],
            confidence=0.0,
            output={
                "enabled": False,
                "reason": "missing_session",
                "paths": [],
                "exact_match": False,
            },
        )
        return BranchOutput(node=node)

    try:
        from core.reasoning.traversal import MultiHopTraverser
    except Exception:
        node = CortexReasoningNode(
            branch="traversal",
            title="Traversal branch",
            summary="Traversal engine import failed, so exact path execution was skipped.",
            evidence_node_ids=_node_ids(state["results"])[:5],
            confidence=0.0,
            output={
                "enabled": False,
                "reason": "traverser_import_failed",
                "paths": [],
                "exact_match": False,
            },
        )
        return BranchOutput(node=node)

    start_node_ids = _node_ids(state["results"])[:4]
    constraints = state.get("planned_constraints")
    edge_types = None
    min_confidence = max(0.05, float(state.get("planned_min_source_reliability") or 0.1) * 0.4)
    if constraints is not None:
        allowed = getattr(constraints, "allowed_edge_types", None)
        if allowed:
            edge_types = set(allowed)
        min_confidence = max(0.05, float(getattr(constraints, "min_confidence", min_confidence) or min_confidence))

    traverser = MultiHopTraverser(
        session=session,
        tenant_id=str(state["tenant_id"]),
        graph_id=str(state["graph_id"]),
    )
    query_goal = str(state.get("query_text") or "").strip()
    max_hops = int(state.get("planned_max_hops") or 1)
    paths = traverser.traverse(
        start_node_ids=start_node_ids,
        goal=query_goal or None,
        max_hops=max_hops,
        min_confidence=min_confidence,
        edge_types=edge_types,
        max_frontier_width=max(24, min(160, max_hops * 8)),
        max_total_expansions=max(512, min(20000, max_hops * 640)),
        return_partial_paths=True,
    )

    serialized_paths = [_serialize_reasoning_path(path) for path in paths[:3]]
    exact_match = any(not bool(path.metadata.get("partial")) for path in paths[:3])
    if serialized_paths:
        best = serialized_paths[0]
        summary = (
            f"Executed a real bounded traversal up to {max_hops} hops and returned "
            f"{'an exact' if exact_match else 'the strongest partial'} path of "
            f"{int(best.get('path_length') or 0)} hops."
        )
        evidence_ids = list(best.get("node_ids") or [])[:8]
        confidence = float(best.get("confidence") or 0.0)
    else:
        summary = (
            f"Executed bounded traversal up to {max_hops} hops, but no stable path "
            "survived the confidence and cycle guards."
        )
        evidence_ids = start_node_ids
        confidence = 0.0

    node = CortexReasoningNode(
        branch="traversal",
        title="Traversal branch",
        summary=summary,
        evidence_node_ids=evidence_ids,
        confidence=confidence,
        output={
            "enabled": True,
            "goal": query_goal,
            "traversal_goal": str(state.get("planned_traversal_goal") or ""),
            "max_hops": max_hops,
            "paths": serialized_paths,
            "exact_match": exact_match,
        },
    )
    return BranchOutput(node=node)


async def run_parallel_branches(state: Dict[str, Any]) -> List[CortexReasoningNode]:
    outputs = await asyncio.gather(
        recall_branch(state),
        traversal_branch(state),
        timeline_branch(state),
        contradiction_branch(state),
        concept_branch(state),
        prediction_branch(state),
        provenance_branch(state),
        continuity_branch(state),
    )
    return [item.node for item in outputs]
