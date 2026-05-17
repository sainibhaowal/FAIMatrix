"""Cortex writeback proposal gate with auto-approval support."""

from __future__ import annotations

from typing import Dict, List, Optional

from .schemas import CortexBrainState

# Import writeback configuration
try:
    from faim.Faim_Native.orchestration.perf.spec import WritebackConfig, WritebackMode
except (ImportError, RuntimeError, ModuleNotFoundError):
    from orchestration.perf.spec import WritebackConfig, WritebackMode


def should_auto_approve_candidate(
    candidate: Dict[str, object], config: Optional[WritebackConfig] = None
) -> bool:
    """
    Determine if a writeback candidate should be auto-approved.

    Uses configurable thresholds and safety rules:
    - Confidence must exceed threshold
    - Contradictions require manual review (configurable)
    - Within safety limits (max per turn)

    Args:
        candidate: Writeback candidate dictionary
        config: Writeback configuration (loads from env if not provided)

    Returns:
        True if candidate should be auto-approved, False for manual review
    """
    if config is None:
        config = WritebackConfig.from_env()

    # MANUAL mode: never auto-approve
    if config.mode == WritebackMode.MANUAL:
        return False

    # AUTO mode: always auto-approve (except explicit contradictions)
    if config.mode == WritebackMode.AUTO:
        has_contradiction = candidate.get("has_contradiction", False)
        return not (has_contradiction and config.require_manual_for_contradictions)

    # SEMI_AUTO mode: check thresholds
    confidence = float(candidate.get("confidence", 0.0))

    # Below minimum threshold: require manual
    if confidence < config.min_candidate_confidence:
        return False

    # Below auto-approve threshold: require manual
    if confidence < config.auto_approve_threshold:
        return False

    # Has contradiction and contradictions require manual: require manual
    has_contradiction = candidate.get("has_contradiction", False)
    if has_contradiction and config.require_manual_for_contradictions:
        return False

    # All checks passed: auto-approve
    return True


def build_writeback_candidates(state: CortexBrainState) -> List[Dict[str, object]]:
    """Return writeback candidates already embedded in state.

    Phase 1 keeps consolidation proposal-only; actual persistence comes later.
    """

    return list(state.writeback_candidates)


def process_writeback_candidates(
    candidates: List[Dict[str, object]], config: Optional[WritebackConfig] = None
) -> tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    """
    Process candidates and separate into auto-approved and manual review queues.

    Args:
        candidates: List of writeback candidate dictionaries
        config: Writeback configuration (loads from env if not provided)

    Returns:
        Tuple of (auto_approved_candidates, manual_review_candidates)
    """
    if config is None:
        config = WritebackConfig.from_env()

    auto_approved: List[Dict[str, object]] = []
    manual_review: List[Dict[str, object]] = []
    auto_count = 0

    for candidate in candidates:
        # Check if auto-approvable
        if should_auto_approve_candidate(candidate, config):
            # Safety limit: max auto-approvals per turn
            if auto_count < config.max_auto_approve_per_turn:
                candidate["status"] = "auto_approved"
                auto_approved.append(candidate)
                auto_count += 1
            else:
                # Exceeded safety limit: move to manual
                candidate["status"] = "proposed"
                manual_review.append(candidate)
        else:
            candidate["status"] = "proposed"
            manual_review.append(candidate)

    return auto_approved, manual_review
