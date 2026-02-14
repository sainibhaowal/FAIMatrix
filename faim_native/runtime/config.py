"""FAIM-Native Runtime Config (Stage-9).

Loads and validates environment configuration for production.

Required env vars:
- DATABASE_URL
- TENANT_KEYS_JSON

Optional env vars:
- ADMIN_KEYS_JSON
- FAIM_PROFILE_DEFAULT (STRICT/FAST/RELAXED)
- FAIM_ENABLE_INDEX, FAIM_ENABLE_CACHE, FAIM_ENABLE_JOBS
- FAIM_ENCRYPTION_FAIL_CLOSED
- FAIM_STORAGE_HARD_DELETE_ENABLED
- FAIM_STORAGE_LIVE_JOB_STREAM_ENABLED
- FAIM_STORAGE_CONTRACT_STRICT
- FAIM_STORAGE_OBSERVABILITY_ENABLED
- FAIM_STORAGE_STRUCTURED_LIFECYCLE_LOGS
- FAIM_SELF_INVENT_ENABLED
- FAIM_SELF_INVENT_ON_EVOLVE
- FAIM_SELF_INVENT_AFTER_UPLOAD
- FAIM_SELF_INVENT_MAX_MACROS_PER_CYCLE
- FAIM_SELF_INVENT_EVENT_WINDOW
- FAIM_SELF_INVENT_MIN_COACTIVATION_COUNT
- FAIM_SELF_INVENT_LAMBDA_THRESHOLD
- FAIM_SELF_INVENT_MIN_REDUNDANCY_REDUCTION
- FAIM_OCR_ENABLED
- FAIM_OCR_ENGINE
- FAIM_OCR_FAIL_CLOSED
- FAIM_OCR_LANGS
- FAIM_OCR_TIMEOUT_SECONDS
- FAIM_OCR_MAX_IMAGE_PIXELS
- FAIM_OCR_PDF_RENDER_DPI
- FAIM_RATE_LIMITS_JSON
- FAIM_EVENT_PAYLOAD_MAX_BYTES
- FAIM_EXPLAIN_MAX_ITEMS
- FAIM_AUTH_DB_PRIMARY
- FAIM_AUTH_ENV_FALLBACK_ENABLED
- FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED
- FAIM_LOG_LEVEL
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# =============================================================================
# Validation Helpers
# =============================================================================

TENANT_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]+$")


def validate_tenant_id(tenant_id: str) -> bool:
    """Validate tenant ID format."""
    return bool(tenant_id and TENANT_ID_REGEX.match(tenant_id))


def parse_json_env(name: str, default: str = "{}") -> Dict[str, Any]:
    """Parse JSON from environment variable."""
    raw = os.environ.get(name, default)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {name}: {e}")  # noqa: B904


def parse_bool_env(name: str, default: bool = False) -> bool:
    """Parse boolean from environment variable."""
    raw = os.environ.get(name, "").lower()
    if raw in ("true", "1", "yes", "on"):
        return True
    if raw in ("false", "0", "no", "off"):
        return False
    if raw == "":
        return default
    return default


def parse_int_env(name: str, default: int) -> int:
    """Parse integer from environment variable."""
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def parse_float_env(name: str, default: float) -> float:
    """Parse float from environment variable."""
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


# =============================================================================
# Config Class
# =============================================================================


@dataclass
class FAIMConfig:
    """FAIM runtime configuration."""

    # Required
    database_url: str
    tenant_keys: Dict[str, List[str]]

    # Optional - auth
    admin_keys: List[str] = field(default_factory=list)

    # Optional - behavior
    profile_default: str = "STRICT"
    enable_index: bool = False
    enable_cache: bool = False
    enable_jobs: bool = False
    log_level: str = "INFO"
    encryption_fail_closed: bool = False
    storage_hard_delete_enabled: bool = False
    storage_live_job_stream_enabled: bool = False
    storage_contract_strict: bool = True
    storage_observability_enabled: bool = True
    storage_structured_lifecycle_logs: bool = True
    self_invent_enabled: bool = False
    self_invent_on_evolve: bool = True
    self_invent_after_upload: bool = False
    self_invent_max_macros_per_cycle: int = 3
    self_invent_event_window: int = 5000
    self_invent_min_coactivation_count: int = 3
    self_invent_lambda_threshold: float = 0.3
    self_invent_min_redundancy_reduction: float = 0.01
    ocr_enabled: bool = False
    ocr_engine: str = "tesseract"
    ocr_fail_closed: bool = False
    ocr_languages: str = "eng"
    ocr_timeout_seconds: int = 20
    ocr_max_image_pixels: int = 24_000_000
    ocr_pdf_render_dpi: int = 180
    auth_db_primary: bool = True
    auth_env_fallback_enabled: bool = False
    auth_scope_enforcement_enabled: bool = False

    # Optional - rate limits
    rate_limits: Dict[str, int] = field(
        default_factory=lambda: {
            "ingest_per_minute": 60,
            "query_per_minute": 120,
            "events_per_minute": 300,
            "storage_per_minute": 60,
            "api_keys_per_minute": 30,
            "ingest_write_per_minute": 60,
            "query_read_per_minute": 120,
            "events_stream_per_minute": 300,
            "storage_read_per_minute": 120,
            "storage_write_per_minute": 60,
            "api_keys_read_per_minute": 60,
            "api_keys_write_per_minute": 20,
            "memory_search_per_minute": 120,
            "memory_read_per_minute": 120,
            "memory_write_per_minute": 60,
        }
    )

    # Optional - payload bounds
    event_payload_max_bytes: int = 4096
    explain_max_items: int = 25

    def validate(self) -> List[str]:
        """Validate configuration. Returns list of errors."""
        errors = []

        if not self.database_url:
            errors.append("DATABASE_URL is required")

        if not self.tenant_keys:
            errors.append("TENANT_KEYS_JSON is required and cannot be empty")

        # Validate tenant IDs
        for tenant_id in self.tenant_keys:
            if not validate_tenant_id(tenant_id):
                errors.append(f"Invalid tenant ID: {tenant_id}")

        # Validate tenant keys are not empty
        for tenant_id, keys in self.tenant_keys.items():
            if not keys or not any(k for k in keys):
                errors.append(f"Tenant {tenant_id} has no valid keys")

        # Validate profile
        if self.profile_default not in ("STRICT", "FAST", "RELAXED"):
            errors.append(f"Invalid profile: {self.profile_default}")

        if self.storage_hard_delete_enabled and not self.enable_jobs:
            errors.append(
                "FAIM_STORAGE_HARD_DELETE_ENABLED requires FAIM_ENABLE_JOBS=true"
            )

        env = os.environ.get("FAIM_ENV", "").strip().lower()
        encryption_enabled = parse_bool_env("FAIM_ENCRYPTION_AT_REST", False)
        if env in ("prod", "production"):
            if not encryption_enabled:
                errors.append("Production requires FAIM_ENCRYPTION_AT_REST=true")
            if not self.encryption_fail_closed:
                errors.append("Production requires FAIM_ENCRYPTION_FAIL_CLOSED=true")
            if self.ocr_enabled and self.ocr_engine != "tesseract":
                errors.append("Production OCR currently supports only FAIM_OCR_ENGINE=tesseract")
            if not self.auth_db_primary:
                errors.append("Production requires FAIM_AUTH_DB_PRIMARY=true")
            if self.auth_env_fallback_enabled:
                errors.append(
                    "Production requires FAIM_AUTH_ENV_FALLBACK_ENABLED=false"
                )
            if not self.auth_scope_enforcement_enabled:
                errors.append(
                    "Production requires FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED=true"
                )

        if self.ocr_engine not in ("tesseract",):
            errors.append(f"Unsupported OCR engine: {self.ocr_engine}")
        if self.ocr_timeout_seconds < 1:
            errors.append("FAIM_OCR_TIMEOUT_SECONDS must be >= 1")
        if self.ocr_max_image_pixels < 1:
            errors.append("FAIM_OCR_MAX_IMAGE_PIXELS must be >= 1")
        if self.ocr_pdf_render_dpi < 72:
            errors.append("FAIM_OCR_PDF_RENDER_DPI must be >= 72")
        if self.self_invent_max_macros_per_cycle < 0:
            errors.append("FAIM_SELF_INVENT_MAX_MACROS_PER_CYCLE must be >= 0")
        if self.self_invent_event_window < 100:
            errors.append("FAIM_SELF_INVENT_EVENT_WINDOW must be >= 100")
        if self.self_invent_min_coactivation_count < 2:
            errors.append("FAIM_SELF_INVENT_MIN_COACTIVATION_COUNT must be >= 2")
        if not (0.0 <= self.self_invent_lambda_threshold <= 1.0):
            errors.append("FAIM_SELF_INVENT_LAMBDA_THRESHOLD must be in [0, 1]")
        if not (0.0 <= self.self_invent_min_redundancy_reduction <= 1.0):
            errors.append(
                "FAIM_SELF_INVENT_MIN_REDUNDANCY_REDUCTION must be in [0, 1]"
            )

        return errors


# =============================================================================
# Loader
# =============================================================================


def load_config() -> FAIMConfig:
    """Load configuration from environment variables.

    Raises:
        ValueError: If required vars missing or invalid.
    """
    database_url = os.environ.get("DATABASE_URL", "")

    # Parse tenant keys
    tenant_keys_raw = parse_json_env("TENANT_KEYS_JSON", "{}")
    tenant_keys: Dict[str, List[str]] = {}
    for tid, keys in tenant_keys_raw.items():
        if isinstance(keys, str):
            tenant_keys[tid] = [keys] if keys else []
        elif isinstance(keys, list):
            tenant_keys[tid] = [k for k in keys if k]
        else:
            tenant_keys[tid] = []

    # Parse admin keys
    admin_keys_raw = parse_json_env("ADMIN_KEYS_JSON", "[]")
    if isinstance(admin_keys_raw, list):
        admin_keys = [k for k in admin_keys_raw if k]
    else:
        admin_keys = []

    # Parse rate limits
    rate_limits = parse_json_env("FAIM_RATE_LIMITS_JSON", "{}")
    default_limits = {
        "ingest_per_minute": 60,
        "query_per_minute": 120,
        "events_per_minute": 300,
        "storage_per_minute": 60,
        "api_keys_per_minute": 30,
        "ingest_write_per_minute": 60,
        "query_read_per_minute": 120,
        "events_stream_per_minute": 300,
        "storage_read_per_minute": 120,
        "storage_write_per_minute": 60,
        "api_keys_read_per_minute": 60,
        "api_keys_write_per_minute": 20,
        "memory_search_per_minute": 120,
        "memory_read_per_minute": 120,
        "memory_write_per_minute": 60,
    }
    default_limits.update(rate_limits)

    config = FAIMConfig(
        database_url=database_url,
        tenant_keys=tenant_keys,
        admin_keys=admin_keys,
        profile_default=os.environ.get("FAIM_PROFILE_DEFAULT", "STRICT").upper(),
        enable_index=parse_bool_env("FAIM_ENABLE_INDEX", False),
        enable_cache=parse_bool_env("FAIM_ENABLE_CACHE", False),
        enable_jobs=parse_bool_env("FAIM_ENABLE_JOBS", False),
        log_level=os.environ.get("FAIM_LOG_LEVEL", "INFO").upper(),
        encryption_fail_closed=parse_bool_env("FAIM_ENCRYPTION_FAIL_CLOSED", False),
        storage_hard_delete_enabled=parse_bool_env(
            "FAIM_STORAGE_HARD_DELETE_ENABLED", False
        ),
        storage_live_job_stream_enabled=parse_bool_env(
            "FAIM_STORAGE_LIVE_JOB_STREAM_ENABLED", False
        ),
        storage_contract_strict=parse_bool_env("FAIM_STORAGE_CONTRACT_STRICT", True),
        storage_observability_enabled=parse_bool_env(
            "FAIM_STORAGE_OBSERVABILITY_ENABLED", True
        ),
        storage_structured_lifecycle_logs=parse_bool_env(
            "FAIM_STORAGE_STRUCTURED_LIFECYCLE_LOGS", True
        ),
        self_invent_enabled=parse_bool_env("FAIM_SELF_INVENT_ENABLED", False),
        self_invent_on_evolve=parse_bool_env("FAIM_SELF_INVENT_ON_EVOLVE", True),
        self_invent_after_upload=parse_bool_env("FAIM_SELF_INVENT_AFTER_UPLOAD", False),
        self_invent_max_macros_per_cycle=parse_int_env(
            "FAIM_SELF_INVENT_MAX_MACROS_PER_CYCLE", 3
        ),
        self_invent_event_window=parse_int_env("FAIM_SELF_INVENT_EVENT_WINDOW", 5000),
        self_invent_min_coactivation_count=parse_int_env(
            "FAIM_SELF_INVENT_MIN_COACTIVATION_COUNT", 3
        ),
        self_invent_lambda_threshold=parse_float_env(
            "FAIM_SELF_INVENT_LAMBDA_THRESHOLD", 0.3
        ),
        self_invent_min_redundancy_reduction=parse_float_env(
            "FAIM_SELF_INVENT_MIN_REDUNDANCY_REDUCTION", 0.01
        ),
        ocr_enabled=parse_bool_env("FAIM_OCR_ENABLED", False),
        ocr_engine=os.environ.get("FAIM_OCR_ENGINE", "tesseract").strip().lower()
        or "tesseract",
        ocr_fail_closed=parse_bool_env("FAIM_OCR_FAIL_CLOSED", False),
        ocr_languages=os.environ.get("FAIM_OCR_LANGS", "eng").strip() or "eng",
        ocr_timeout_seconds=parse_int_env("FAIM_OCR_TIMEOUT_SECONDS", 20),
        ocr_max_image_pixels=parse_int_env("FAIM_OCR_MAX_IMAGE_PIXELS", 24_000_000),
        ocr_pdf_render_dpi=parse_int_env("FAIM_OCR_PDF_RENDER_DPI", 180),
        auth_db_primary=parse_bool_env("FAIM_AUTH_DB_PRIMARY", True),
        auth_env_fallback_enabled=parse_bool_env(
            "FAIM_AUTH_ENV_FALLBACK_ENABLED", False
        ),
        auth_scope_enforcement_enabled=parse_bool_env(
            "FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED", False
        ),
        rate_limits=default_limits,
        event_payload_max_bytes=parse_int_env("FAIM_EVENT_PAYLOAD_MAX_BYTES", 4096),
        explain_max_items=parse_int_env("FAIM_EXPLAIN_MAX_ITEMS", 25),
    )

    errors = config.validate()
    if errors:
        raise ValueError(f"Config validation failed: {'; '.join(errors)}")

    return config


# =============================================================================
# Global Config (lazy loaded)
# =============================================================================

_config: Optional[FAIMConfig] = None


def get_config() -> FAIMConfig:
    """Get the global config, loading if needed."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    """Reset config (for testing)."""
    global _config
    _config = None


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "FAIMConfig",
    "load_config",
    "get_config",
    "reset_config",
    "validate_tenant_id",
]
