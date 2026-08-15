"""FAIM Cortex runtime package."""

from .schemas import (
    CortexBrainState,
    CortexReasoningNode,
    CortexTurnRequest,
    CortexTurnResponse,
)

def __getattr__(name: str):
    if name == "run_cortex_turn":
        from .runtime import run_cortex_turn
        return run_cortex_turn
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "CortexBrainState",
    "CortexReasoningNode",
    "CortexTurnRequest",
    "CortexTurnResponse",
    "run_cortex_turn",
]
