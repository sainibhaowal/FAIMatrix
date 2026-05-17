"""FAIM-Native Learning Engine: Feedback loops and reinforcement.

Self-improving reasoning through user feedback and pattern learning.
Deterministic, auditable, zero ML.
"""

from __future__ import annotations

from .calibration import ConfidenceCalibrator
from .feedback_store import FeedbackStore, ReasoningFeedback
from .pattern_matcher import LearnedPattern, PatternMatcher
from .reinforcement import ReinforcementLearner

__all__ = [
    "FeedbackStore",
    "ReasoningFeedback",
    "PatternMatcher",
    "LearnedPattern",
    "ReinforcementLearner",
    "ConfidenceCalibrator",
]
