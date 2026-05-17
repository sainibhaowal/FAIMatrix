"""Feedback models for FAIM learning system.

Separate module to avoid circular imports.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# JSONB type compatible
JSONBType = JSONB


class ReasoningFeedbackModel(Base):
    """Stores user feedback on reasoning quality for learning."""

    __tablename__ = "reasoning_feedback"
    __table_args__ = ({"schema": "faim_native"},)

    feedback_id = Column(String(36), primary_key=True)
    turn_id = Column(String(36), nullable=False, index=True)
    session_id = Column(String(36), nullable=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    graph_id = Column(String(64), nullable=True, index=True)

    # Query and reasoning details
    query_text = Column(Text, nullable=False)
    reasoning_path_json = Column(JSONBType, nullable=False, default={})
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
