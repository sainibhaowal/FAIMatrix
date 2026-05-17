"""Cortex turn planner.

Classifies a user request into a structured turn type before narration.
"""

from __future__ import annotations

from dataclasses import dataclass

from .semantics import SEMANTICS
from .schemas import CortexTaskType


@dataclass(frozen=True)
class PlannedTurn:
    task_type: CortexTaskType
    goal: str


def classify_turn(query_text: str, answer_mode: str, confidence: float) -> PlannedTurn:
    text = query_text.strip().lower()

    # 1. Primary Signal: Professional Semantic Alias Registry
    semantic_type = SEMANTICS.classify(text)
    if semantic_type:
        return PlannedTurn(
            task_type=semantic_type,
            goal=f"Execute {semantic_type.value} task derived from professional semantics."
        )

    # 2. Secondary Signal: Explicit User Answer Mode
    if answer_mode == "timeline":
        return PlannedTurn(
            task_type=CortexTaskType.timeline,
            goal="Reconstruct the memory sequence in time order.",
        )
    # ... existing fallbacks ...
    if answer_mode == "contradiction" or any(
        token in text for token in ("conflict", "contradict", "contradiction", "vs ")
    ):
        return PlannedTurn(
            task_type=CortexTaskType.contradiction,
            goal="Surface conflicting memories and preserve both sides.",
        )

    if answer_mode == "provenance" or any(
        token in text for token in ("source", "provenance", "cite", "where from")
    ):
        return PlannedTurn(
            task_type=CortexTaskType.provenance,
            goal="Explain the source trail before the conclusion.",
        )

    if any(token in text for token in ("compare", "difference", "versus", "vs")):
        return PlannedTurn(
            task_type=CortexTaskType.compare,
            goal="Compare the strongest memories and explain the distinction.",
        )

    if any(token in text for token in ("predict", "forecast", "likely next", "future")):
        return PlannedTurn(
            task_type=CortexTaskType.predict,
            goal="Infer likely next states from the memory pattern.",
        )

    if confidence < 0.35 or any(
        token in text for token in ("what else", "need more", "missing", "clarify")
    ):
        return PlannedTurn(
            task_type=CortexTaskType.ask_follow_up,
            goal="Ask for the missing evidence instead of forcing a guess.",
        )

    if any(token in text for token in ("save", "remember", "write", "update")):
        return PlannedTurn(
            task_type=CortexTaskType.consolidate,
            goal="Consolidate the current memory into a grounded writeback candidate.",
        )

    return PlannedTurn(
        task_type=CortexTaskType.answer,
        goal="Answer the user from memory with grounded synthesis.",
    )
