"""Feedback models for FAIM learning system.

Separate module to avoid circular imports. Shares the core ``Base`` metadata
with ``models_faim`` so ``create_all_tables`` registers the feedback table in
the same schema as the rest of the store (also keeps SQLite test runs green).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from store.pg.models_faim import Base, JSONBType


class ReasoningFeedbackModel(Base):
    """Stores user feedback on reasoning quality for learning."""

    __tablename__ = "reasoning_feedback"

    feedback_id = Column(String(36), primary_key=True)
    turn_id = Column(String(36), nullable=False, index=True)
    session_id = Column(String(36), nullable=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    graph_id = Column(String(64), nullable=True, index=True)

    # Query and reasoning details
    query_text = Column(Text, nullable=False)
    reasoning_path_json = Column(JSONBType, nullable=False, default=list)
    answer_given = Column(Text, nullable=False)

    # User feedback
    user_rating = Column(Float, nullable=False)  # 0.0 to 1.0
    user_correction = Column(Text, nullable=True)
    correction_type = Column(String(32), nullable=True)  # factual, incomplete, etc.

    # Pattern identification
    pattern_hash = Column(String(16), nullable=False, index=True)
    query_signature = Column(String(32), nullable=False)  # causal, explanatory, etc.

    # Metadata
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    processed = Column(String(1), nullable=False, default="0")  # "0" or "1"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "feedback_id": self.feedback_id,
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "graph_id": self.graph_id,
            "query_text": self.query_text,
            "reasoning_path_json": self.reasoning_path_json,
            "answer_given": self.answer_given,
            "user_rating": self.user_rating,
            "user_correction": self.user_correction,
            "correction_type": self.correction_type,
            "pattern_hash": self.pattern_hash,
            "query_signature": self.query_signature,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed": self.processed == "1",
        }


class ReinforcementPatternStatsModel(Base):
    """Persistent, learned statistics for a reasoning pattern.

    Backed by the ReinforcementLearner: as user feedback accumulates for a
    pattern, its reliability score and confidence-threshold adjustment are
    updated and durable. This closes the feedback → policy loop so learning
    survives restarts and can drive future reasoning paths.
    """

    __tablename__ = "reinforcement_pattern_stats"

    pattern_hash = Column(String(16), primary_key=True)
    tenant_id = Column(String(64), nullable=False, primary_key=True, index=True)
    query_signature = Column(String(32), nullable=False)

    total_uses = Column(Integer, nullable=False, default=0)
    successful_uses = Column(Integer, nullable=False, default=0)
    failed_uses = Column(Integer, nullable=False, default=0)
    average_rating = Column(Float, nullable=False, default=0.0)
    correction_rate = Column(Float, nullable=False, default=0.0)
    reliability_score = Column(Float, nullable=False, default=0.5)
    threshold_adjustment = Column(Float, nullable=False, default=0.0)

    first_seen = Column(DateTime(timezone=True), nullable=False)
    last_used = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API consumers."""
        return {
            "pattern_hash": self.pattern_hash,
            "tenant_id": self.tenant_id,
            "query_signature": self.query_signature,
            "total_uses": self.total_uses,
            "successful_uses": self.successful_uses,
            "failed_uses": self.failed_uses,
            "average_rating": self.average_rating,
            "correction_rate": self.correction_rate,
            "reliability_score": self.reliability_score,
            "threshold_adjustment": self.threshold_adjustment,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
