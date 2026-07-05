"""FAIM Cortex turn runtime."""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from api.routers.query import QueryAnswer
from core.cortex.branches import run_parallel_branches
from core.cortex.history import load_cortex_session_summary, load_recent_cortex_turns
from core.cortex.persistence import persist_cortex_turn
from core.cortex.planner import PlannedTurn, classify_turn
from core.cortex.reducer import reduce_cortex_state
from core.cortex.schemas import CortexBrainState, CortexTaskType, CortexTurnResponse
from core.query.answer_synthesis import synthesize_answer
from orchestration.ingest_flow import FAIMProfile
from orchestration.query_flow import run_query


def _normalize_mode(answer_mode: str) -> str:
    value = (answer_mode or "direct").strip().lower()
    if value in {"timeline", "contradiction", "provenance"}:
        return value
    return "direct"


def _classify(query_text: str, answer_mode: str, confidence: float) -> PlannedTurn:
    return classify_turn(
        query_text=query_text, answer_mode=answer_mode, confidence=confidence
    )


def _adaptive_query_graph_options(planned) -> Dict[str, Any]:
    """Map a planned turn into bounded retrieval options.

    Retrieval stays more conservative than the full reasoning branch, but it
    now scales with the real planned hop budget instead of being hardcoded.
    """
    max_hops = int(max(1, getattr(planned, "max_hops", 1) or 1))
    constraints = getattr(planned, "constraints", None)
    branching = int(
        max(4, min(24, getattr(constraints, "max_branching_factor", 8) or 8))
    )
    return {
        "graph_max_hops": max_hops,
        "graph_max_neighbors": branching,
        "graph_diffusion_steps": max(3, min(max_hops, 12)),
        "graph_decay": 0.62 if max_hops >= 8 else 0.6,
        "graph_alpha": 0.18 if max_hops >= 8 else 0.2,
    }


def _answer_packet_from_result(query_text: str, result) -> Dict[str, Any]:
    answer_dict = result.answer or {}
    if not answer_dict:
        answer_dict = synthesize_answer(
            query_text=query_text,
            ranked_results=result.results,
            query_hash=result.query_hash,
            graph_id=result.graph_id,
        )
    return answer_dict


def _render_narrative(state: CortexBrainState) -> str:
    direct = str(state.answer_packet.get("direct_answer") or "").strip()
    if not direct:
        return state.narrative

    if state.task_type == CortexTaskType.timeline:
        prefix = "Timeline synthesis:"
    elif state.task_type == CortexTaskType.contradiction:
        prefix = "Contradiction synthesis:"
    elif state.task_type == CortexTaskType.provenance:
        prefix = "Provenance synthesis:"
    elif state.task_type == CortexTaskType.predict:
        prefix = "Prediction synthesis:"
    else:
        prefix = "FAIM Cortex synthesis:"
    return f"{prefix} {state.narrative}"


async def run_cortex_turn(
    *,
    session,
    tenant_id: str,
    graph_id: str,
    query_text: str,
    k: int = 15,
    profile: FAIMProfile = FAIMProfile.RELAXED,
    answer_mode: str = "direct",
    session_id: Optional[str] = None,
    return_explain: bool = True,
    think_enabled: bool = True,
) -> CortexTurnResponse:
    """Execute one Cortex turn.

    Phase 1 implementation:
    - reuse deterministic FAIM query retrieval
    - classify the turn
    - run structured reasoning branches in parallel
    - reduce to a structured brain state
    - return a narration-ready answer packet
    """

    # Cortex thinking is a backend capability now, not a user-visible toggle.
    # Old clients may still send think_enabled=false; keep accepting the field
    # but route every turn through the enhanced planner and bounded traversal.
    effective_think_enabled = True

    import time

    start = time.perf_counter()
    answer_mode = _normalize_mode(answer_mode)
    turn_id = uuid4().hex
    initial_planned = None

    if effective_think_enabled:
        try:
            from core.cortex.planner_enhanced import plan_turn_enhanced

            initial_planned = plan_turn_enhanced(
                query_text=query_text,
                answer_mode=answer_mode,
                confidence=0.0,
                enable_multi_hop=True,
            )
        except Exception:
            initial_planned = _classify(
                query_text=query_text,
                answer_mode=answer_mode,
                confidence=0.0,
            )

    query_options = (
        _adaptive_query_graph_options(initial_planned)
        if initial_planned is not None
        else {}
    )

    query_result = run_query(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        query_text=query_text,
        k=k,
        profile=profile,
        return_explain=return_explain,
        index=None,
        cache=None,
        **query_options,
    )

    effective_session_id = session_id or turn_id
    recent_turns = load_recent_cortex_turns(
        session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        session_id=effective_session_id,
        limit=6,
    )
    session_summary = load_cortex_session_summary(
        session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        session_id=effective_session_id,
    )

    answer_packet = _answer_packet_from_result(query_text, query_result)
    if effective_think_enabled:
        try:
            from core.cortex.planner_enhanced import plan_turn_enhanced

            planned = plan_turn_enhanced(
                query_text=query_text,
                answer_mode=answer_mode,
                confidence=float(answer_packet.get("confidence") or 0.0),
                enable_multi_hop=True,
            )
        except Exception:
            # Import or planning failure — fall back to the standard classifier
            planned = _classify(
                query_text=query_text,
                answer_mode=answer_mode,
                confidence=float(answer_packet.get("confidence") or 0.0),
            )
    else:
        planned = _classify(
            query_text=query_text,
            answer_mode=answer_mode,
            confidence=float(answer_packet.get("confidence") or 0.0),
        )

    branch_state = {
        "session": session,
        "tenant_id": tenant_id,
        "graph_id": graph_id,
        "query_text": query_text,
        "answer_packet": answer_packet,
        "results": query_result.results,
        "planned_task_type": planned.task_type.value,
        "planned_enable_multi_hop": bool(getattr(planned, "enable_multi_hop", False)),
        "planned_max_hops": int(getattr(planned, "max_hops", 1) or 1),
        "planned_traversal_goal": str(getattr(planned, "traversal_goal", "") or ""),
        "planned_constraints": getattr(planned, "constraints", None),
        "planned_min_source_reliability": float(
            getattr(planned, "min_source_reliability", 0.1) or 0.1
        ),
        "recent_turns": recent_turns,
        "session_summary": session_summary.model_dump() if session_summary else None,
    }

    reasoning_tree = await run_parallel_branches(branch_state)
    brain_state = reduce_cortex_state(
        turn_id=turn_id,
        tenant_id=tenant_id,
        graph_id=graph_id,
        session_id=session_id or turn_id,
        query_text=query_text,
        answer_mode=answer_mode,
        task_type=planned.task_type,
        query_hash=query_result.query_hash,
        graph_version=query_result.graph_version,
        graph_hash=query_result.graph_hash,
        answer_packet=answer_packet,
        results=query_result.results,
        reasoning_tree=reasoning_tree,
        recent_turns=[turn.model_dump() for turn in recent_turns],
    )

    narrative = _render_narrative(brain_state)
    brain_state.narrative = narrative
    persist_cortex_turn(session, brain_state)

    duration_ms = (time.perf_counter() - start) * 1000.0

    return CortexTurnResponse(
        tenant_id=tenant_id,
        graph_id=graph_id,
        session_id=session_id or turn_id,
        turn_id=turn_id,
        query_hash=query_result.query_hash,
        task_type=planned.task_type,
        answer_mode=answer_mode,
        answer=QueryAnswer(**answer_packet) if answer_packet else None,
        brain_state=brain_state,
        narrative=narrative,
        duration_ms=duration_ms,
    )
