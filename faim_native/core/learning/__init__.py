"""FAIM-Native Learning Engine: Feedback loops and reinforcement.

Self-improving reasoning through user feedback and pattern learning.
Deterministic, auditable, zero ML.
"""

from __future__ import annotations

from .evolution_policy import (
    KNOB_DEFAULTS,
    KNOB_GRIDS,
    ArmState,
    EvolutionPolicy,
    LambdaCalibration,
    ResolvedKnobs,
    compute_reward,
)
from .feedback_store import FeedbackStore, ReasoningFeedback
from .reinforcement import ReinforcementLearner

__all__ = [
    "FeedbackStore",
    "ReasoningFeedback",
    "ReinforcementLearner",
    "ArmState",
    "LambdaCalibration",
    "ResolvedKnobs",
    "EvolutionPolicy",
    "KNOB_DEFAULTS",
    "KNOB_GRIDS",
    "compute_reward",
]
