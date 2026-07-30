"""Feedback storage and retrieval for reasoning improvement.

Captures user feedback on reasoning quality and stores for pattern learning.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

# Database imports
try:
    from faim.Faim_Native.store.pg.models_faim import ReasoningFeedbackModel
except (ImportError, RuntimeError, ModuleNotFoundError):
    ReasoningFeedbackModel = Any


@dataclass
class ReasoningFeedback:
    """
    User feedback on a specific reasoning turn.

    Captures both ratings and corrections for learning.
    """

    feedback_id: str
    turn_id: str
    session_id: Optional[str]
    tenant_id: str
    graph_id: Optional[str]

    # What was the reasoning?
    query_text: str
    reasoning_path: List[str]  # Sequence of reasoning steps
    answer_given: str

    # User feedback
    user_rating: float  # 0.0 to 1.0
    user_correction: Optional[str] = None
    correction_type: Optional[str] = (
        None  # "factual", "incomplete", "wrong_inference", "irrelevant"
    )

    # Pattern identification
    pattern_hash: str  # Hash of reasoning structure
    query_signature: str  # Categorized query type

    # Metadata
    created_at: datetime
    processed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "feedback_id": self.feedback_id,
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "graph_id": self.graph_id,
            "query_text": self.query_text,
            "reasoning_path": self.reasoning_path,
            "answer_given": self.answer_given,
            "user_rating": self.user_rating,
            "user_correction": self.user_correction,
            "correction_type": self.correction_type,
            "pattern_hash": self.pattern_hash,
            "query_signature": self.query_signature,
            "created_at": self.created_at.isoformat(),
            "processed": self.processed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReasoningFeedback":
        """Create from dictionary."""
        return cls(
            feedback_id=data["feedback_id"],
            turn_id=data["turn_id"],
            session_id=data.get("session_id"),
            tenant_id=data["tenant_id"],
            graph_id=data.get("graph_id"),
            query_text=data["query_text"],
            reasoning_path=data["reasoning_path"],
            answer_given=data["answer_given"],
            user_rating=data["user_rating"],
            user_correction=data.get("user_correction"),
            correction_type=data.get("correction_type"),
            pattern_hash=data["pattern_hash"],
            query_signature=data["query_signature"],
            created_at=datetime.fromisoformat(data["created_at"]),
            processed=data.get("processed", False),
        )


class FeedbackStore:
    """
    Persistent storage for reasoning feedback.

    Enables learning from user corrections over time.
    """

    def __init__(self, session):
        self.session = session
        self._cache: Dict[str, ReasoningFeedback] = {}

    def record_feedback(
        self,
        turn_id: str,
        tenant_id: str,
        query_text: str,
        reasoning_path: List[str],
        answer_given: str,
        user_rating: float,
        user_correction: Optional[str] = None,
        correction_type: Optional[str] = None,
        session_id: Optional[str] = None,
        graph_id: Optional[str] = None,
    ) -> ReasoningFeedback:
        """
        Record user feedback on a reasoning turn.

        Args:
            turn_id: Unique turn identifier
            tenant_id: Tenant for isolation
            query_text: Original query
            reasoning_path: Steps taken during reasoning
            answer_given: Answer provided to user
            user_rating: 0.0 (terrible) to 1.0 (perfect)
            user_correction: What should have been said
            correction_type: Category of correction

        Returns:
            Created feedback object
        """
        # Generate pattern hash
        pattern_hash = self._hash_reasoning_path(reasoning_path)
        query_signature = self._extract_query_signature(query_text)

        feedback = ReasoningFeedback(
            feedback_id=str(uuid4()),
            turn_id=turn_id,
            session_id=session_id,
            tenant_id=tenant_id,
            graph_id=graph_id,
            query_text=query_text,
            reasoning_path=reasoning_path,
            answer_given=answer_given,
            user_rating=user_rating,
            user_correction=user_correction,
            correction_type=correction_type,
            pattern_hash=pattern_hash,
            query_signature=query_signature,
            created_at=datetime.utcnow(),
            processed=False,
        )

        # Persist to database
        self._persist(feedback)

        # Update cache
        self._cache[feedback.feedback_id] = feedback

        return feedback

    def _hash_reasoning_path(self, reasoning_path: List[str]) -> str:
        """Generate deterministic hash for reasoning pattern."""
        path_str = json.dumps(reasoning_path, sort_keys=True)
        return hashlib.sha256(path_str.encode()).hexdigest()[:16]

    def _extract_query_signature(self, query_text: str) -> str:
        """Extract query type signature for categorization."""
        text = query_text.lower()

        # Simple keyword-based signature
        if any(w in text for w in ["why", "cause", "reason"]):
            return "causal"
        elif any(w in text for w in ["how", "what is", "explain"]):
            return "explanatory"
        elif any(w in text for w in ["compare", "difference", "vs"]):
            return "comparative"
        elif any(w in text for w in ["when", "timeline", "history"]):
            return "temporal"
        elif any(w in text for w in ["predict", "forecast", "future"]):
            return "predictive"
        else:
            return "factual"

    def _persist(self, feedback: ReasoningFeedback) -> None:
        """Save feedback to database."""
        # Create model instance
        model = ReasoningFeedbackModel(
            feedback_id=feedback.feedback_id,
            turn_id=feedback.turn_id,
            session_id=feedback.session_id,
            tenant_id=feedback.tenant_id,
            graph_id=feedback.graph_id,
            query_text=feedback.query_text[:500],  # Limit length
            reasoning_path_json=json.dumps(feedback.reasoning_path),
            answer_given=feedback.answer_given[:1000],
            user_rating=feedback.user_rating,
            user_correction=(
                feedback.user_correction[:1000] if feedback.user_correction else None
            ),
            correction_type=feedback.correction_type,
            pattern_hash=feedback.pattern_hash,
            query_signature=feedback.query_signature,
            created_at=feedback.created_at,
            processed=feedback.processed,
        )

        self.session.add(model)
        self.session.flush()

    def get_feedback_for_pattern(
        self,
        pattern_hash: str,
        min_samples: int = 5,
    ) -> List[ReasoningFeedback]:
        """
        Get all feedback for a specific reasoning pattern.

        Used to calculate pattern success rate.
        """
        if pattern_hash in self._cache:
            return [f for f in self._cache.values() if f.pattern_hash == pattern_hash]

        # Query database
        models = (
            self.session.query(ReasoningFeedbackModel)
            .filter(ReasoningFeedbackModel.pattern_hash == pattern_hash)
            .all()
        )

        feedbacks = [self._model_to_feedback(m) for m in models]

        # Update cache
        for f in feedbacks:
            self._cache[f.feedback_id] = f

        return feedbacks

    def get_feedback_stats(
        self,
        tenant_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get feedback statistics for monitoring.

        Returns:
            Stats dict with average ratings, correction rates, etc.
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        models = (
            self.session.query(ReasoningFeedbackModel)
            .filter(
                ReasoningFeedbackModel.tenant_id == tenant_id,
                ReasoningFeedbackModel.created_at >= cutoff,
            )
            .all()
        )

        if not models:
            return {
                "total_feedback": 0,
                "average_rating": 0.0,
                "correction_rate": 0.0,
                "by_type": {},
            }

        ratings = [m.user_rating for m in models]
        corrections = [m for m in models if m.user_correction]

        # By correction type
        by_type = {}
        for m in models:
            ctype = m.correction_type or "unknown"
            by_type[ctype] = by_type.get(ctype, 0) + 1

        return {
            "total_feedback": len(models),
            "average_rating": sum(ratings) / len(ratings),
            "correction_rate": len(corrections) / len(models),
            "by_type": by_type,
            "rating_distribution": {
                "excellent": sum(1 for r in ratings if r >= 0.8),
                "good": sum(1 for r in ratings if 0.6 <= r < 0.8),
                "fair": sum(1 for r in ratings if 0.4 <= r < 0.6),
                "poor": sum(1 for r in ratings if r < 0.4),
            },
        }

    def _model_to_feedback(self, model) -> ReasoningFeedback:
        """Convert database model to feedback object."""
        return ReasoningFeedback(
            feedback_id=model.feedback_id,
            turn_id=model.turn_id,
            session_id=model.session_id,
            tenant_id=model.tenant_id,
            graph_id=model.graph_id,
            query_text=model.query_text,
            reasoning_path=json.loads(model.reasoning_path_json),
            answer_given=model.answer_given,
            user_rating=model.user_rating,
            user_correction=model.user_correction,
            correction_type=model.correction_type,
            pattern_hash=model.pattern_hash,
            query_signature=model.query_signature,
            created_at=model.created_at,
            processed=model.processed,
        )

    def mark_processed(self, feedback_id: str) -> None:
        """Mark feedback as processed (incorporated into patterns)."""
        model = (
            self.session.query(ReasoningFeedbackModel)
            .filter(ReasoningFeedbackModel.feedback_id == feedback_id)
            .first()
        )

        if model:
            model.processed = True
            self.session.flush()

        if feedback_id in self._cache:
            self._cache[feedback_id].processed = True
