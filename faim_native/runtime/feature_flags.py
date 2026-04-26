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


def _parse_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
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
    self_evolve_enabled: bool = False
    self_evolve_trigger_mode: str = "manual"
    self_evolve_min_interval_seconds: int = 300
    self_evolve_min_version_delta: int = 1
    self_evolve_max_actions: int = 25
    self_evolve_scan_interval_seconds: int = 60
    profile_persist_compat_mode: bool = True
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
        self_evolve_enabled=_parse_bool("FAIM_SELF_EVOLVE_ENABLED", False),
        self_evolve_trigger_mode=(
            os.getenv("FAIM_SELF_EVOLVE_TRIGGER_MODE", "manual").strip().lower()
            or "manual"
        ),
        self_evolve_min_interval_seconds=_parse_int(
            "FAIM_SELF_EVOLVE_MIN_INTERVAL_SECONDS", 300
        ),
        self_evolve_min_version_delta=_parse_int(
            "FAIM_SELF_EVOLVE_MIN_VERSION_DELTA", 1
        ),
        self_evolve_max_actions=_parse_int("FAIM_SELF_EVOLVE_MAX_ACTIONS", 25),
        self_evolve_scan_interval_seconds=_parse_int(
            "FAIM_SELF_EVOLVE_SCAN_INTERVAL_SECONDS", 60
        ),
        profile_persist_compat_mode=_parse_bool(
            "FAIM_PROFILE_PERSIST_COMPAT_MODE", True
        ),
        auth_db_primary=_parse_bool("FAIM_AUTH_DB_PRIMARY", True),
        auth_env_fallback_enabled=_parse_bool("FAIM_AUTH_ENV_FALLBACK_ENABLED", False),
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
        errors.append("FAIM_STORAGE_HARD_DELETE_ENABLED requires FAIM_ENABLE_JOBS=true")

    allowed_trigger_modes = {"manual", "post_upload", "periodic", "hybrid"}
    trigger_mode = str(flags.self_evolve_trigger_mode or "").strip().lower()
    if trigger_mode not in allowed_trigger_modes:
        errors.append(
            "FAIM_SELF_EVOLVE_TRIGGER_MODE must be one of: "
            "manual, post_upload, periodic, hybrid"
        )
    if (
        flags.self_evolve_enabled
        and trigger_mode in {"post_upload", "periodic", "hybrid"}
        and not jobs_enabled
    ):
        errors.append(
            "FAIM_SELF_EVOLVE_ENABLED with trigger mode "
            f"'{trigger_mode}' requires FAIM_ENABLE_JOBS=true"
        )
    if flags.self_evolve_min_interval_seconds < 30:
        errors.append("FAIM_SELF_EVOLVE_MIN_INTERVAL_SECONDS must be >= 30")
    if flags.self_evolve_min_version_delta < 1:
        errors.append("FAIM_SELF_EVOLVE_MIN_VERSION_DELTA must be >= 1")
    if flags.self_evolve_max_actions < 1:
        errors.append("FAIM_SELF_EVOLVE_MAX_ACTIONS must be >= 1")
    if flags.self_evolve_scan_interval_seconds < 30:
        errors.append("FAIM_SELF_EVOLVE_SCAN_INTERVAL_SECONDS must be >= 30")
    if env in {"prod", "production"} and flags.profile_persist_compat_mode:
        warnings.append(
            "FAIM_PROFILE_PERSIST_COMPAT_MODE=true keeps legacy profile/persist behavior; disable only after R2 rollout validation."
        )

    if env in {"prod", "production"}:
        if not encryption_enabled:
            errors.append("Production mode requires FAIM_ENCRYPTION_AT_REST=true")
        if not flags.encryption_fail_closed:
            errors.append("Production mode requires FAIM_ENCRYPTION_FAIL_CLOSED=true")

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
        if not flags.auth_scope_enforcement_enabled:
            errors.append(
                "Production mode requires FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED=true"
            )
    return errors, warnings


__all__ = [
    "FeatureFlags",
    "get_feature_flags",
    "validate_feature_flags",
]
