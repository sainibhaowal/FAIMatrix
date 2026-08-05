"""Structured Cortex session history helpers with configurable context window."""

from __future__ import annotations

import os
from typing import List, Optional

from .schemas import CortexSessionSummary, CortexTaskType, CortexTurnSummary

# Import profile configuration
try:
    from faim.Faim_Native.orchestration.perf.spec import (
        FaimSpeedProfile,
    )
except (ImportError, RuntimeError, ModuleNotFoundError):
    from orchestration.perf.spec import FaimSpeedProfile


# Default context window sizes by profile
_DEFAULT_CONTEXT_WINDOWS = {
    FaimSpeedProfile.STRICT: 6,
    FaimSpeedProfile.FAST: 12,
    FaimSpeedProfile.RELAXED: 20,
    FaimSpeedProfile.CORE_DEV: 10,
    FaimSpeedProfile.CORE_REALTIME: 8,
    FaimSpeedProfile.CORE_SCALE: 20,
    FaimSpeedProfile.CORE_HARDENED: 12,
    FaimSpeedProfile.AUTO: 12,
}

# Absolute max for safety (prevent runaway memory)
_MAX_CONTEXT_WINDOW = 50


def get_context_window_limit(
    profile: Optional[FaimSpeedProfile] = None, explicit_limit: Optional[int] = None
) -> int:
    """
    Get configured context window limit.

    Resolution order:
    1. Explicit limit (if provided)
    2. Environment variable FAIM_CONTEXT_WINDOW_TURNS
    3. Profile-based default
    4. Global default (6)

    Args:
        profile: Speed profile for default lookup
        explicit_limit: Explicitly requested limit (highest priority)

    Returns:
        Configured limit (clamped to 1-50)
    """
    # Priority 1: Explicit limit
    if explicit_limit is not None:
        return max(1, min(_MAX_CONTEXT_WINDOW, explicit_limit))

    # Priority 2: Environment variable
    env_limit = os.getenv("FAIM_CONTEXT_WINDOW_TURNS")
    if env_limit:
        try:
            env_val = int(env_limit)
            return max(1, min(_MAX_CONTEXT_WINDOW, env_val))
        except ValueError:
            pass  # Fall through to next priority

    # Priority 3: Profile-based default
    if profile is not None:
        default = _DEFAULT_CONTEXT_WINDOWS.get(profile, 6)
        return default

    # Priority 4: Global default
    return 6


def _coerce_task_type(value: str | None) -> CortexTaskType:
    raw = (value or "answer").strip().lower()
    try:
        return CortexTaskType(raw)
    except Exception:
        return CortexTaskType.answer


def load_recent_cortex_turns(
    session,
    *,
    tenant_id: str,
    graph_id: str,
    session_id: str,
    limit: Optional[int] = None,
    profile: Optional[FaimSpeedProfile] = None,
) -> List[CortexTurnSummary]:
    """Load prior turns for the same session in reverse-chronological order.

    Context window size is configurable via:
    - Explicit limit parameter (highest priority)
    - FAIM_CONTEXT_WINDOW_TURNS environment variable
    - Profile-based defaults
    - Global default of 6 turns (lowest priority)

    Args:
        session: Database session
        tenant_id: Tenant identifier
        graph_id: Graph identifier
        session_id: Session identifier
        limit: Explicit turn limit (overrides all other config)
        profile: Speed profile for default limit lookup

    Returns:
        List of recent turns (chronological order, oldest first)
    """

    from store.pg.models_faim import CortexTurnModel

    # Resolve effective limit from configuration
    effective_limit = get_context_window_limit(profile=profile, explicit_limit=limit)

    rows = (
        session.query(CortexTurnModel)
        .filter(
            CortexTurnModel.tenant_id == tenant_id,
            CortexTurnModel.graph_id == graph_id,
            CortexTurnModel.session_id == session_id,
        )
        .order_by(CortexTurnModel.created_at.desc())
        .limit(effective_limit)
        .all()
    )
    turns = [
        CortexTurnSummary(
            turn_id=row.turn_id,
            query_text=row.query_text,
            answer_mode=row.answer_mode,
            task_type=_coerce_task_type(row.task_type),
            confidence=float(row.confidence or 0.0),
            narrative=row.narrative or "",
            open_question_count=int(row.open_question_count or 0),
            contradiction_count=int(row.contradiction_count or 0),
            created_at=row.created_at,
        )
        for row in rows
    ]
    return list(reversed(turns))


def list_cortex_sessions(
    session,
    *,
    tenant_id: str,
    graph_id: str,
    limit: int = 20,
) -> List[CortexSessionSummary]:
    """List recent Cortex sessions for a graph."""

    from store.pg.models_faim import CortexSessionModel

    rows = (
        session.query(CortexSessionModel)
        .filter(
            CortexSessionModel.tenant_id == tenant_id,
            CortexSessionModel.graph_id == graph_id,
        )
        .order_by(CortexSessionModel.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [
        CortexSessionSummary(
            session_id=row.session_id,
            tenant_id=row.tenant_id,
            graph_id=row.graph_id,
            title=row.title or "",
            turn_count=int(row.turn_count or 0),
            last_turn_id=row.last_turn_id,
            last_task_type=row.last_task_type,
            last_confidence=row.last_confidence,
            last_turn_at=row.last_turn_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


def load_cortex_session_summary(
    session,
    *,
    tenant_id: str,
    graph_id: str,
    session_id: str,
) -> CortexSessionSummary | None:
    """Load a single Cortex session summary."""

    from store.pg.models_faim import CortexSessionModel

    row = (
        session.query(CortexSessionModel)
        .filter(
            CortexSessionModel.tenant_id == tenant_id,
            CortexSessionModel.graph_id == graph_id,
            CortexSessionModel.session_id == session_id,
        )
        .first()
    )
    if row is None:
        return None
    return CortexSessionSummary(
        session_id=row.session_id,
        tenant_id=row.tenant_id,
        graph_id=row.graph_id,
        title=row.title or "",
        turn_count=int(row.turn_count or 0),
        last_turn_id=row.last_turn_id,
        last_task_type=row.last_task_type,
        last_confidence=row.last_confidence,
        last_turn_at=row.last_turn_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def delete_cortex_session(
    session,
    *,
    tenant_id: str,
    graph_id: str,
    session_id: str,
) -> bool:
    """Delete a Cortex session and all its associated turns."""

    from store.pg.models_faim import CortexSessionModel, CortexTurnModel

    session.query(CortexTurnModel).filter(
        CortexTurnModel.tenant_id == tenant_id,
        CortexTurnModel.graph_id == graph_id,
        CortexTurnModel.session_id == session_id,
    ).delete(synchronize_session=False)

    deleted_count = session.query(CortexSessionModel).filter(
        CortexSessionModel.tenant_id == tenant_id,
        CortexSessionModel.graph_id == graph_id,
        CortexSessionModel.session_id == session_id,
    ).delete(synchronize_session=False)

    session.commit()
    return deleted_count > 0

