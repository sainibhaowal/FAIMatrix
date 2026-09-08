"""Structured Cortex state and turn schemas.

Phase 1 uses structured reasoning state, not raw chain-of-thought.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from api.routers.query import QueryAnswer
from pydantic import BaseModel, Field


class CortexTaskType(str, Enum):
    """Top-level turn classification."""

    answer = "answer"
    timeline = "timeline"
    contradiction = "contradiction"
    provenance = "provenance"
    compare = "compare"
    predict = "predict"
    investigate = "investigate"
    consolidate = "consolidate"
    ask_follow_up = "ask_follow_up"


class CortexReasoningNode(BaseModel):
    """One structured reasoning step in the Cortex tree."""

    node_id: str = Field(default_factory=lambda: uuid4().hex)
    branch: str
    title: str
    summary: str
    evidence_node_ids: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    depends_on: List[str] = Field(default_factory=list)
    output: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CortexTurnSummary(BaseModel):
    """Compact summary of one prior Cortex turn."""

    turn_id: str
    query_text: str
    answer_mode: str
    task_type: CortexTaskType
    confidence: float = 0.0
    narrative: str = ""
    open_question_count: int = 0
    contradiction_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CortexSessionSummary(BaseModel):
    """Compact summary of a Cortex session."""

    session_id: str
    tenant_id: str
    graph_id: str
    title: str = ""
    turn_count: int = 0
    last_turn_id: Optional[str] = None
    last_task_type: Optional[str] = None
    last_confidence: Optional[float] = None
    last_turn_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CortexBrainState(BaseModel):
    """Structured per-turn brain state."""

    turn_id: str
    tenant_id: str
    graph_id: str
    session_id: Optional[str] = None
    query_text: str
    answer_mode: str
    task_type: CortexTaskType
    query_hash: str = ""
    graph_version: int = 0
    graph_hash: str = ""
    goal: str = ""
    session_turn_count: int = 0
    session_summary: str = ""
    active_facts: List[str] = Field(default_factory=list)
    evidence_nodes: List[Dict[str, Any]] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    hypotheses: List[str] = Field(default_factory=list)
    predictions: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    retrieval_summary: Dict[str, Any] = Field(default_factory=dict)
    recent_turns: List[CortexTurnSummary] = Field(default_factory=list)
    reasoning_tree: List[CortexReasoningNode] = Field(default_factory=list)
    writeback_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    answer_packet: Dict[str, Any] = Field(default_factory=dict)
    narrative: str = ""


class CortexTurnRequest(BaseModel):
    """Cortex turn request."""

    graph_id: str = Field(..., description="Graph to query")
    query_text: str = Field(..., description="User prompt")
    session_id: Optional[str] = Field(
        default=None, description="Optional conversation/session id"
    )
    k: int = Field(15, ge=1, le=100, description="Number of results to recall")
    profile: str = Field(
        "RELAXED", description="STRICT, BALANCED, RELAXED, or FAST"
    )
    return_explain: bool = Field(True, description="Include explain payload")
    answer_mode: str = Field(
        "direct",
        description="direct, timeline, contradiction, or provenance",
    )
    think_enabled: bool = Field(
        True,
        description=(
            "Deprecated client hint. Cortex structured thinking is enabled by "
            "default and the runtime treats false as a compatibility no-op."
        ),
    )


class CortexTurnResponse(BaseModel):
    """Response for a Cortex turn."""

    tenant_id: str
    graph_id: str
    session_id: Optional[str] = None
    turn_id: str
    query_hash: str
    task_type: CortexTaskType
    answer_mode: str
    answer: Optional[QueryAnswer] = None
    brain_state: CortexBrainState
    narrative: str
    duration_ms: float
