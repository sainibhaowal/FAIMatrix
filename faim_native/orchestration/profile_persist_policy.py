"""Central profile/persist policy resolver (Phase R2).

Single source of truth for mapping requested (profile, persist_mode, operation)
into effective runtime behavior knobs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from runtime.feature_flags import get_feature_flags


class PolicyOperation(str, Enum):
    """Operations that consume profile/persist policies."""

    INGEST = "ingest"
    EVOLVE = "evolve"


VALID_PROFILES = {"strict", "fast", "relaxed"}
VALID_PERSIST_MODES = {"strict", "relaxed"}


@dataclass(frozen=True)
class ProfilePersistPolicy:
    """Resolved runtime policy for one operation call."""

    operation: str
    requested_profile: str
    requested_persist_mode: str
    effective_profile: str
    effective_persist_mode: str
    compatibility_mode: bool
    coerced: bool
    coercion_reason: Optional[str]
    durability_path: str
    index_enabled: bool
    evolve_aggressiveness: str


def _normalize_profile(value: Optional[str]) -> tuple[str, Optional[str]]:
    profile = str(value or "").strip().lower()
    if profile in VALID_PROFILES:
        return profile, None
    return "strict", "invalid_profile"


def _normalize_persist_mode(value: Optional[str]) -> tuple[str, Optional[str]]:
    persist_mode = str(value or "").strip().lower()
    if persist_mode in VALID_PERSIST_MODES:
        return persist_mode, None
    return "relaxed", "invalid_persist_mode"


def _durability_path_for_mode(persist_mode: str) -> str:
    if persist_mode == "strict":
        return "sync_strict"
    return "core_sync_secondary_async"


def _evolve_aggressiveness_for_profile(profile: str) -> str:
    if profile == "strict":
        return "conservative"
    if profile == "fast":
        return "performance"
    return "adaptive"


def resolve_profile_persist_policy(
    *,
    operation: PolicyOperation | str,
    requested_profile: Optional[str],
    requested_persist_mode: Optional[str],
    compatibility_mode: Optional[bool] = None,
) -> ProfilePersistPolicy:
    """Resolve effective policy knobs for ingest/evolve operations."""
    if compatibility_mode is None:
        compatibility_mode = bool(get_feature_flags().profile_persist_compat_mode)

    if isinstance(operation, PolicyOperation):
        op = operation.value
    else:
        op = str(operation).strip().lower()
    if op not in {PolicyOperation.INGEST.value, PolicyOperation.EVOLVE.value}:
        op = PolicyOperation.INGEST.value

    effective_profile, profile_reason = _normalize_profile(requested_profile)
    effective_persist_mode, persist_reason = _normalize_persist_mode(
        requested_persist_mode
    )

    # R2 compatibility mode keeps current behavior while centralizing decisions.
    # Full differentiated semantics can be expanded in later phases.
    if compatibility_mode:
        effective_profile = effective_profile
        effective_persist_mode = effective_persist_mode

    reasons = [r for r in (profile_reason, persist_reason) if r]
    coercion_reason = ",".join(reasons) if reasons else None

    index_enabled = (
        op == PolicyOperation.INGEST.value and effective_profile != "strict"
    )

    return ProfilePersistPolicy(
        operation=op,
        requested_profile=str(requested_profile or "").strip().lower(),
        requested_persist_mode=str(requested_persist_mode or "").strip().lower(),
        effective_profile=effective_profile,
        effective_persist_mode=effective_persist_mode,
        compatibility_mode=bool(compatibility_mode),
        coerced=bool(coercion_reason),
        coercion_reason=coercion_reason,
        durability_path=_durability_path_for_mode(effective_persist_mode),
        index_enabled=index_enabled,
        evolve_aggressiveness=_evolve_aggressiveness_for_profile(effective_profile),
    )


__all__ = [
    "PolicyOperation",
    "ProfilePersistPolicy",
    "resolve_profile_persist_policy",
]
