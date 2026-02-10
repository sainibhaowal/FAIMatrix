"""Runtime feature flags and guardrail validation (Phase A)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Tuple


def _parse_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(frozen=True)
class FeatureFlags:
    """Operational feature flags that gate risky behavior."""

    encryption_fail_closed: bool = False
    storage_hard_delete_enabled: bool = False
    storage_live_job_stream_enabled: bool = False
    storage_contract_strict: bool = True


def get_feature_flags() -> FeatureFlags:
    """Load feature flags from environment."""
    return FeatureFlags(
        encryption_fail_closed=_parse_bool("FAIM_ENCRYPTION_FAIL_CLOSED", False),
        storage_hard_delete_enabled=_parse_bool(
            "FAIM_STORAGE_HARD_DELETE_ENABLED", False
        ),
        storage_live_job_stream_enabled=_parse_bool(
            "FAIM_STORAGE_LIVE_JOB_STREAM_ENABLED", False
        ),
        storage_contract_strict=_parse_bool("FAIM_STORAGE_CONTRACT_STRICT", True),
    )


def validate_feature_flags(flags: FeatureFlags) -> Tuple[List[str], List[str]]:
    """Validate flag combinations.

    Returns:
        (errors, warnings)
    """
    errors: List[str] = []
    warnings: List[str] = []

    env = os.getenv("FAIM_ENV", "").strip().lower()
    encryption_enabled = _parse_bool("FAIM_ENCRYPTION_AT_REST", False)
    jobs_enabled = _parse_bool("FAIM_ENABLE_JOBS", False)

    if flags.storage_hard_delete_enabled and not jobs_enabled:
        errors.append(
            "FAIM_STORAGE_HARD_DELETE_ENABLED requires FAIM_ENABLE_JOBS=true"
        )

    if env in {"prod", "production"} and encryption_enabled and not flags.encryption_fail_closed:
        errors.append(
            "Production mode with FAIM_ENCRYPTION_AT_REST=true requires FAIM_ENCRYPTION_FAIL_CLOSED=true"
        )

    if flags.storage_live_job_stream_enabled:
        warnings.append(
            "FAIM_STORAGE_LIVE_JOB_STREAM_ENABLED is enabled but live stream integration must be verified at UI rollout"
        )

    return errors, warnings


__all__ = [
    "FeatureFlags",
    "get_feature_flags",
    "validate_feature_flags",
]
