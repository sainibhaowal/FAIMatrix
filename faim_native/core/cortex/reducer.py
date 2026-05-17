"""Cortex state reducer."""

from __future__ import annotations

from typing import Any, Dict, List

from .schemas import CortexBrainState, CortexReasoningNode, CortexTaskType


def _extract_open_questions(confidence: float, contradictions: List[str]) -> List[str]:
    questions: List[str] = []
    if confidence < 0.4:
        questions.append(
            "The current memory confidence is low; more evidence may be needed."
        )
    if contradictions:
        questions.append(
            "Conflicting memory values exist and should be resolved before hardening."
        )
    return questions


def _extract_next_actions(
    task_type: CortexTaskType, confidence: float, contradictions: List[str]
) -> List[str]:
    actions: List[str] = []
    if task_type in {CortexTaskType.ask_follow_up, CortexTaskType.investigate}:
        actions.append("ask_follow_up")
    elif task_type == CortexTaskType.consolidate:
        actions.append("prepare_writeback")
    else:
        actions.append("answer")
    if contradictions:
        actions.append("surface_contradiction")
    if confidence >= 0.75:
        actions.append("consider_consolidation")
    return list(dict.fromkeys(actions))


def _build_narrative(
    *,
    query_text: str,
    answer_mode: str,
    answer_packet: Dict[str, Any],
    contradictions: List[str],
    next_actions: List[str],
) -> str:
    direct = str(answer_packet.get("direct_answer") or "").strip()
    confidence = float(answer_packet.get("confidence") or 0.0)
    if not direct:
        if contradictions:
            return "FAIM Cortex found conflicting memories, but not enough grounded evidence to resolve them safely."
        return "FAIM Cortex did not find a grounded answer in current memory."

    if answer_mode == "timeline":
        lead = "FAIM Cortex reconstructed the memory sequence in time order."
    elif answer_mode == "contradiction":
        lead = "FAIM Cortex isolated the conflicting memory values."
    elif answer_mode == "provenance":
        lead = "FAIM Cortex traced the answer back to its source trail."
    else:
        lead = "FAIM Cortex grounded the answer in retrieved memory."

    tail = ""
    if contradictions:
        tail = " Conflicts remain visible and were not hidden."
    if confidence < 0.4:
        tail += (
            " Confidence is low enough that the answer should be treated as tentative."
        )
    if "ask_follow_up" in next_actions:
        tail += " A follow-up question may be required to close the gap."
    return f"{lead} {direct}{tail}".strip()


def reduce_cortex_state(
    *,
    turn_id: str,
    tenant_id: str,
    graph_id: str,
    session_id: str | None,
    query_text: str,
    answer_mode: str,
    task_type: CortexTaskType,
    query_hash: str,
    graph_version: int,
    graph_hash: str,
    answer_packet: Dict[str, Any],
    results: List[Dict[str, Any]],
    reasoning_tree: List[CortexReasoningNode],
    recent_turns: List[Dict[str, Any]] | None = None,
) -> CortexBrainState:
    confidence = float(answer_packet.get("confidence") or 0.0)
    contradictions = list(answer_packet.get("contradiction_notes") or [])
    recent_turns = list(recent_turns or [])
    active_facts = [
        str(span.get("text") or "").strip()
        for span in answer_packet.get("supporting_spans") or []
        if span.get("text")
    ]
    if not active_facts and answer_packet.get("direct_answer"):
        active_facts.append(str(answer_packet["direct_answer"]).strip())

    hypotheses = []
    if results:
        top = results[0]
        hypotheses.append(
            f"Top evidence node {top.get('node_id')} is the strongest anchor for this turn."
        )
    if recent_turns:
        last_turn = recent_turns[-1]
        hypotheses.append(
            f"Session continuity extends from turn {last_turn.get('turn_id')} about '{str(last_turn.get('query_text') or '')[:80]}'."
        )

    predictions = []
    for node in reasoning_tree:
        if node.branch == "prediction":
            predictions.extend(
                [str(item) for item in node.output.get("predictions", []) if item]
            )

    next_actions = _extract_next_actions(task_type, confidence, contradictions)
    open_questions = _extract_open_questions(confidence, contradictions)
    if not active_facts and task_type == CortexTaskType.ask_follow_up:
        open_questions.append("What specific memory slice should be recalled next?")
    if recent_turns and task_type not in {
        CortexTaskType.ask_follow_up,
        CortexTaskType.consolidate,
    }:
        unresolved = [
            str(turn.get("query_text") or "")
            for turn in recent_turns
            if turn.get("open_question_count", 0) or turn.get("contradiction_count", 0)
        ]
        if unresolved:
            open_questions.append(
                f"Prior session threads still need closure: {unresolved[-1][:120]}"
            )

    writeback_candidates: List[Dict[str, Any]] = []
    if confidence >= 0.75 and active_facts:
        writeback_candidates.append(
            {
                "kind": "summary",
                "status": "proposed",
                "reason": "high_confidence_grounded_answer",
                "text": active_facts[0],
                "confidence": confidence,
            }
        )
    if contradictions:
        writeback_candidates.append(
            {
                "kind": "contradiction_resolution",
                "status": "proposed",
                "reason": "conflicting_memory_values_present",
                "text": contradictions[0],
                "confidence": max(0.0, confidence - 0.15),
            }
        )

    narrative = _build_narrative(
        query_text=query_text,
        answer_mode=answer_mode,
        answer_packet=answer_packet,
        contradictions=contradictions,
        next_actions=next_actions,
    )

    session_turn_count = len(recent_turns) + 1
    session_summary = (
        f"{session_turn_count} turn session anchored on {recent_turns[-1].get('query_text') if recent_turns else 'the current query'}."
        if recent_turns
        else "Single-turn session so far."
    )

    return CortexBrainState(
        turn_id=turn_id,
        tenant_id=tenant_id,
        graph_id=graph_id,
        session_id=session_id,
        query_text=query_text,
        answer_mode=answer_mode,
        task_type=task_type,
        query_hash=query_hash,
        graph_version=graph_version,
        graph_hash=graph_hash,
        goal="Answer the user from grounded FAIM memory with structured reasoning.",
        session_turn_count=session_turn_count,
        session_summary=session_summary,
        active_facts=active_facts,
        evidence_nodes=results,
        contradictions=contradictions,
        open_questions=open_questions,
        hypotheses=hypotheses,
        predictions=predictions,
        next_actions=next_actions,
        confidence=confidence,
        recent_turns=recent_turns,
        reasoning_tree=reasoning_tree,
        writeback_candidates=writeback_candidates,
        answer_packet=answer_packet,
        narrative=narrative,
    )
