"""Persistence helpers for structured Cortex turns."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.encoders import jsonable_encoder

from .schemas import CortexBrainState

# Import writeback processing
try:
    from faim.Faim_Native.core.cortex.consolidation import (
        WritebackConfig,
        process_writeback_candidates,
    )
    from faim.Faim_Native.core.cortex.writeback_executor import (
        execute_cortex_writeback_candidate,
    )
except (ImportError, RuntimeError, ModuleNotFoundError):
    from core.cortex.consolidation import (
        WritebackConfig,
        process_writeback_candidates,
    )
    from core.cortex.writeback_executor import execute_cortex_writeback_candidate


def persist_cortex_turn(session, state: CortexBrainState) -> None:
    """Persist one structured Cortex turn.

    Phase 3 stores structured state only. It does not persist raw chain-of-thought.
    """

    from store.pg.models_faim import (
        CortexReasoningNodeModel,
        CortexSessionModel,
        CortexTurnModel,
        CortexWritebackCandidateModel,
    )

    now = datetime.now(timezone.utc)
    session_id = state.session_id or state.turn_id

    session_row = (
        session.query(CortexSessionModel)
        .filter(
            CortexSessionModel.tenant_id == state.tenant_id,
            CortexSessionModel.graph_id == state.graph_id,
            CortexSessionModel.session_id == session_id,
        )
        .first()
    )

    if session_row is None:
        session_row = CortexSessionModel(
            session_id=session_id,
            tenant_id=state.tenant_id,
            graph_id=state.graph_id,
            title=state.query_text[:120],
            turn_count=0,
            created_at=now,
            updated_at=now,
        )
        session.add(session_row)

    session_row.turn_count = (session_row.turn_count or 0) + 1
    session_row.last_turn_id = state.turn_id
    session_row.last_task_type = state.task_type.value
    session_row.last_query_hash = state.query_hash
    session_row.last_confidence = state.confidence
    session_row.last_turn_at = now
    session_row.updated_at = now

    turn_row = CortexTurnModel(
        turn_id=state.turn_id,
        session_id=session_id,
        tenant_id=state.tenant_id,
        graph_id=state.graph_id,
        query_text=state.query_text,
        answer_mode=state.answer_mode,
        task_type=state.task_type.value,
        query_hash=state.query_hash,
        graph_version=state.graph_version,
        graph_hash=state.graph_hash,
        confidence=state.confidence,
        narrative=state.narrative,
        answer_json=jsonable_encoder(state.answer_packet),
        brain_state_json=jsonable_encoder(state.model_dump()),
        reasoning_count=len(state.reasoning_tree),
        open_question_count=len(state.open_questions),
        contradiction_count=len(state.contradictions),
        created_at=now,
        updated_at=now,
    )
    session.add(turn_row)

    for node in state.reasoning_tree:
        session.add(
            CortexReasoningNodeModel(
                node_id=node.node_id,
                turn_id=state.turn_id,
                session_id=session_id,
                tenant_id=state.tenant_id,
                graph_id=state.graph_id,
                branch=node.branch,
                title=node.title,
                summary=node.summary,
                evidence_node_ids=jsonable_encoder(node.evidence_node_ids),
                confidence=node.confidence,
                depends_on=jsonable_encoder(node.depends_on),
                output_json=jsonable_encoder(node.output),
                created_at=node.created_at,
            )
        )

    # Process writeback candidates with auto-approval logic
    config = WritebackConfig.from_env()
    auto_approved, manual_review = process_writeback_candidates(
        list(state.writeback_candidates), config
    )

    # Persist auto-approved candidates and execute them with a receipt.
    for candidate in auto_approved:
        candidate_row = CortexWritebackCandidateModel(
            turn_id=state.turn_id,
            session_id=session_id,
            tenant_id=state.tenant_id,
            graph_id=state.graph_id,
            kind=str(candidate.get("kind") or "summary"),
            status="auto_approved",
            execution_status="pending",
            reason=str(candidate.get("reason") or ""),
            payload_json=jsonable_encoder(candidate),
            confidence=float(candidate.get("confidence") or 0.0),
            created_at=now,
        )
        session.add(candidate_row)
        session.flush()

        result = execute_cortex_writeback_candidate(
            session=session,
            tenant_id=state.tenant_id,
            graph_id=state.graph_id,
            turn_id=state.turn_id,
            candidate_row=candidate_row,
            candidate_payload=candidate,
            request_id=state.session_id or state.turn_id,
        )
        candidate.update(
            {
                "status": candidate_row.status,
                "execution_status": candidate_row.execution_status,
                "execution_key": candidate_row.execution_key,
                "execution_request_hash": candidate_row.execution_request_hash,
                "execution_receipt": candidate_row.execution_receipt_json or {},
                "execution_receipt_json": candidate_row.execution_receipt_json or {},
                "execution_error": candidate_row.execution_error,
                "executed_at": (
                    candidate_row.executed_at.isoformat()
                    if candidate_row.executed_at
                    else None
                ),
                "execution_replayed": result.replayed,
            }
        )

    # Persist manual review candidates
    for candidate in manual_review:
        candidate_row = CortexWritebackCandidateModel(
            turn_id=state.turn_id,
            session_id=session_id,
            tenant_id=state.tenant_id,
            graph_id=state.graph_id,
            kind=str(candidate.get("kind") or "summary"),
            status=str(candidate.get("status") or "proposed"),
            execution_status="skipped",
            reason=str(candidate.get("reason") or ""),
            payload_json=jsonable_encoder(candidate),
            confidence=float(candidate.get("confidence") or 0.0),
            created_at=now,
        )
        session.add(candidate_row)
        candidate.update(
            {
                "status": candidate_row.status,
                "execution_status": candidate_row.execution_status,
                "execution_key": None,
                "execution_request_hash": None,
                "execution_receipt": {},
                "execution_receipt_json": {},
                "execution_error": None,
                "executed_at": None,
                "execution_replayed": False,
            }
        )

    session.flush()
