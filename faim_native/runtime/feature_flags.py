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
    storage_observability_enabled: bool = True
    storage_structured_lifecycle_logs: bool = True
    ocr_enabled: bool = False
    ocr_fail_closed: bool = False
    self_invent_enabled: bool = False
    self_invent_on_evolve: bool = True
    self_invent_after_upload: bool = False
    auth_db_primary: bool = True
    auth_env_fallback_enabled: bool = False
    auth_scope_enforcement_enabled: bool = False


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
        storage_observability_enabled=_parse_bool(
            "FAIM_STORAGE_OBSERVABILITY_ENABLED", True
        ),
        storage_structured_lifecycle_logs=_parse_bool(
            "FAIM_STORAGE_STRUCTURED_LIFECYCLE_LOGS", True
        ),
        ocr_enabled=_parse_bool("FAIM_OCR_ENABLED", False),
        ocr_fail_closed=_parse_bool("FAIM_OCR_FAIL_CLOSED", False),
        self_invent_enabled=_parse_bool("FAIM_SELF_INVENT_ENABLED", False),
        self_invent_on_evolve=_parse_bool("FAIM_SELF_INVENT_ON_EVOLVE", True),
        self_invent_after_upload=_parse_bool("FAIM_SELF_INVENT_AFTER_UPLOAD", False),
        auth_db_primary=_parse_bool("FAIM_AUTH_DB_PRIMARY", True),
        auth_env_fallback_enabled=_parse_bool(
            "FAIM_AUTH_ENV_FALLBACK_ENABLED", False
        ),
        auth_scope_enforcement_enabled=_parse_bool(
            "FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED", False
        ),
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

    if env in {"prod", "production"}:
        if not encryption_enabled:
            errors.append(
                "Production mode requires FAIM_ENCRYPTION_AT_REST=true"
            )
        if not flags.encryption_fail_closed:
            errors.append(
                "Production mode requires FAIM_ENCRYPTION_FAIL_CLOSED=true"
            )

    if flags.storage_live_job_stream_enabled:
        warnings.append(
            "FAIM_STORAGE_LIVE_JOB_STREAM_ENABLED is enabled but live stream integration must be verified at UI rollout"
        )
    if env in {"prod", "production"} and not flags.storage_observability_enabled:
        warnings.append(
            "FAIM_STORAGE_OBSERVABILITY_ENABLED=false in production reduces incident visibility"
        )
    if flags.ocr_fail_closed and not flags.ocr_enabled:
        warnings.append(
            "FAIM_OCR_FAIL_CLOSED=true while FAIM_OCR_ENABLED=false (OCR fail-closed is inactive)"
        )

    if not flags.auth_db_primary:
        warnings.append(
            "FAIM_AUTH_DB_PRIMARY=false enables legacy auth ordering and should be temporary."
        )

    if env in {"prod", "production"}:
        if not flags.auth_db_primary:
            errors.append("Production mode requires FAIM_AUTH_DB_PRIMARY=true")
        if flags.auth_env_fallback_enabled:
            errors.append(
                "Production mode requires FAIM_AUTH_ENV_FALLBACK_ENABLED=false"
            )
    return errors, warnings


__all__ = [
    "FeatureFlags",
    "get_feature_flags",
    "validate_feature_flags",
]
