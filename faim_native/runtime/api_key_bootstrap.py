"""One-time, database-backed tenant API-key bootstrap support.

This module is deliberately *not* imported by the API startup path.  It is
used only by ``scripts/bootstrap_tenant_api_keys.py`` to move an explicitly
provided, short-lived JSON secret into ``tenant_api_keys`` as Argon2id hashes.
Normal production processes authenticate only against the database and must
not retain plaintext tenant credentials in ``TENANT_KEYS_JSON``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from dataclasses import dataclass
from typing import Mapping, MutableMapping, Sequence

from runtime.secrets import hash_api_key, verify_api_key
from sqlalchemy import text
from sqlalchemy.orm import Session
from store.pg.models_auth import AuthKeyAuditLog, TenantApiKey

BOOTSTRAP_ENV_NAME = "FAIM_TENANT_KEY_BOOTSTRAP_JSON"

# Keep this contract aligned with api.middleware.auth.TENANT_PATTERN without
# importing middleware into an operator-only runtime utility.
TENANT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# Bootstrap credentials are bearer credentials sent as HTTP headers.  Require
# a practical minimum and reject whitespace/control characters so accidental
# quoting, line wrapping, and weak test placeholders cannot reach production.
MIN_API_KEY_LENGTH = 16
MAX_API_KEY_LENGTH = 512
MAX_BOOTSTRAP_JSON_BYTES = 256 * 1024
MAX_BOOTSTRAP_TENANTS = 1_000
MAX_KEYS_PER_TENANT = 100

# A bootstrap key must be able to create narrower keys and then be revoked.
# Callers should rotate/revoke it after first use.  These are the only scopes
# currently accepted by the API-key management route.
DEFAULT_BOOTSTRAP_SCOPES = (
    "keys.read",
    "keys.write",
    "memory.read",
    "memory.write",
    "memory.admin",
)


class BootstrapValidationError(ValueError):
    """Raised for safe-to-display bootstrap input and runtime errors.

    Messages intentionally never include a plaintext API key or the raw JSON
    payload.  The command-line wrapper may display these messages safely.
    """


class BootstrapDatabaseError(RuntimeError):
    """Raised when a bootstrap cannot safely determine existing DB state."""


@dataclass(frozen=True)
class TenantKeyBootstrapResult:
    """Non-secret outcome summary for one bootstrap invocation."""

    requested: int
    imported: int
    already_present: int
    dry_run: bool

    @property
    def would_import(self) -> int:
        """Return keys that would be inserted (or were inserted) this run."""
        return self.requested - self.already_present


def _strict_json_object(pairs: Sequence[tuple[object, object]]) -> dict[object, object]:
    """Build a JSON object while rejecting duplicate keys.

    ``json.loads`` otherwise silently retains the last duplicate key, which is
    inappropriate for a security bootstrap input.
    """
    result: dict[object, object] = {}
    for key, value in pairs:
        if key in result:
            raise BootstrapValidationError(
                "Bootstrap JSON contains duplicate object keys"
            )
        result[key] = value
    return result


def _validate_api_key(value: object) -> str:
    """Validate one plaintext bootstrap key without ever echoing it."""
    if not isinstance(value, str):
        raise BootstrapValidationError("Each bootstrap API key must be a string")
    if len(value) < MIN_API_KEY_LENGTH:
        raise BootstrapValidationError(
            f"Each bootstrap API key must be at least {MIN_API_KEY_LENGTH} characters"
        )
    if len(value) > MAX_API_KEY_LENGTH:
        raise BootstrapValidationError(
            f"Each bootstrap API key must be at most {MAX_API_KEY_LENGTH} characters"
        )
    if value != value.strip() or any(ch.isspace() for ch in value):
        raise BootstrapValidationError("Bootstrap API keys must not contain whitespace")
    if any(ord(ch) < 33 or ord(ch) > 126 for ch in value):
        raise BootstrapValidationError(
            "Bootstrap API keys must contain only printable ASCII characters"
        )
    return value


def normalize_bootstrap_payload(payload: object) -> dict[str, tuple[str, ...]]:
    """Validate and normalize a parsed bootstrap JSON payload.

    The canonical shape is ``{"tenant_id": ["plaintext-key", ...]}``.
    A single string value remains supported only to make a deliberate migration
    from the legacy ``TENANT_KEYS_JSON`` shape straightforward.  It is never
    read automatically from that legacy environment variable.
    """
    if not isinstance(payload, dict):
        raise BootstrapValidationError("Bootstrap JSON must be an object")
    if not payload:
        raise BootstrapValidationError(
            "Bootstrap JSON must contain at least one tenant"
        )
    if len(payload) > MAX_BOOTSTRAP_TENANTS:
        raise BootstrapValidationError("Bootstrap JSON contains too many tenants")

    normalized: dict[str, tuple[str, ...]] = {}
    seen_plaintext_keys: set[str] = set()

    for raw_tenant_id, raw_keys in payload.items():
        if not isinstance(raw_tenant_id, str) or not TENANT_ID_PATTERN.fullmatch(
            raw_tenant_id
        ):
            raise BootstrapValidationError(
                "Bootstrap JSON contains an invalid tenant ID"
            )

        if isinstance(raw_keys, str):
            candidate_keys: Sequence[object] = [raw_keys]
        elif isinstance(raw_keys, list):
            candidate_keys = raw_keys
        else:
            raise BootstrapValidationError(
                "Each bootstrap tenant value must be an API-key string or list"
            )

        if not candidate_keys:
            raise BootstrapValidationError(
                "Each bootstrap tenant must have at least one key"
            )
        if len(candidate_keys) > MAX_KEYS_PER_TENANT:
            raise BootstrapValidationError("A bootstrap tenant contains too many keys")

        keys: list[str] = []
        for candidate in candidate_keys:
            key = _validate_api_key(candidate)
            if key in seen_plaintext_keys:
                raise BootstrapValidationError(
                    "A bootstrap API key may be assigned to only one tenant"
                )
            seen_plaintext_keys.add(key)
            keys.append(key)
        normalized[raw_tenant_id] = tuple(keys)

    return normalized


def load_bootstrap_from_environment(
    environ: Mapping[str, str] | None = None,
) -> dict[str, tuple[str, ...]]:
    """Load the explicit one-time JSON payload without inspecting legacy env keys."""
    source = environ if environ is not None else os.environ
    raw = str(source.get(BOOTSTRAP_ENV_NAME, "") or "")
    if not raw:
        raise BootstrapValidationError(
            f"{BOOTSTRAP_ENV_NAME} must be set for a one-time bootstrap"
        )
    if len(raw.encode("utf-8")) > MAX_BOOTSTRAP_JSON_BYTES:
        raise BootstrapValidationError("Bootstrap JSON is too large")

    try:
        payload = json.loads(raw, object_pairs_hook=_strict_json_object)
    except BootstrapValidationError:
        raise
    except (TypeError, json.JSONDecodeError) as exc:
        raise BootstrapValidationError("Bootstrap JSON is invalid") from exc

    return normalize_bootstrap_payload(payload)


def _parse_bool(value: str | None, default: bool) -> bool:
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _is_production(source: Mapping[str, str]) -> bool:
    values = (source.get("FAIM_MODE", ""), source.get("FAIM_ENV", ""))
    return any(str(value).strip().lower() in {"prod", "production"} for value in values)


def validate_bootstrap_runtime(environ: Mapping[str, str] | None = None) -> None:
    """Assert that a production bootstrap preserves DB-only auth policy."""
    source = environ if environ is not None else os.environ
    if not _is_production(source):
        return

    if not _parse_bool(source.get("FAIM_AUTH_DB_PRIMARY"), True):
        raise BootstrapValidationError(
            "Production bootstrap requires FAIM_AUTH_DB_PRIMARY=true"
        )
    if _parse_bool(source.get("FAIM_AUTH_ENV_FALLBACK_ENABLED"), False):
        raise BootstrapValidationError(
            "Production bootstrap requires FAIM_AUTH_ENV_FALLBACK_ENABLED=false"
        )
    if _parse_bool(source.get("FAIM_ALLOW_DEV_AUTH_BYPASS"), False):
        raise BootstrapValidationError(
            "Production bootstrap requires FAIM_ALLOW_DEV_AUTH_BYPASS=false"
        )


def _postgres_advisory_lock_id(tenant_id: str) -> int:
    """Return a stable signed 64-bit PostgreSQL advisory-lock ID for a tenant."""
    digest = hashlib.sha256(tenant_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)


def _lock_tenant_for_bootstrap(session: Session, tenant_id: str) -> None:
    """Serialize same-tenant bootstrap runs on PostgreSQL.

    A lock is transaction-scoped and has no persistent schema or operational
    state.  SQLite is used by local tests and has no equivalent advisory lock.
    """
    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        return
    session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_id)"),
        {"lock_id": _postgres_advisory_lock_id(tenant_id)},
    )


def _matching_existing_key(
    records: Sequence[TenantApiKey], plaintext_key: str
) -> TenantApiKey | None:
    """Return an existing matching record, including revoked/expired records.

    A revoked or expired matching key counts as present.  Bootstrap must never
    silently reactivate a credential whose lifecycle was intentionally changed.
    """
    for record in records:
        try:
            if verify_api_key(plaintext_key, record.key_hash):
                return record
        except Exception as exc:  # fail closed on a corrupted persisted hash
            raise BootstrapDatabaseError(
                "Cannot safely verify an existing tenant API-key record"
            ) from exc
    return None


def _new_bootstrap_key_id(session: Session, tenant_id: str) -> str:
    """Create an opaque display/revocation ID without deriving from plaintext."""
    for _ in range(10):
        key_id = f"bootstrap_{secrets.token_hex(8)}"
        existing = (
            session.query(TenantApiKey.id)
            .filter(
                TenantApiKey.tenant_id == tenant_id,
                TenantApiKey.key_id == key_id,
            )
            .first()
        )
        if existing is None:
            return key_id
    raise BootstrapDatabaseError("Could not allocate a unique bootstrap key ID")


def bootstrap_tenant_api_keys(
    session: Session,
    payload: object,
    *,
    apply: bool,
) -> TenantKeyBootstrapResult:
    """Plan or import only missing tenant keys as Argon2id hashes.

    The caller owns the transaction: commit on an accepted ``apply`` result,
    otherwise roll it back.  Every source input is validated before database
    mutation.  The function intentionally creates no plaintext DB columns,
    logs no credentials, and does not read ``TENANT_KEYS_JSON``.
    """
    normalized = normalize_bootstrap_payload(payload)
    requested = sum(len(keys) for keys in normalized.values())
    imported = 0
    already_present = 0

    for tenant_id in sorted(normalized):
        _lock_tenant_for_bootstrap(session, tenant_id)
        records = (
            session.query(TenantApiKey)
            .filter(TenantApiKey.tenant_id == tenant_id)
            .all()
        )

        for plaintext_key in normalized[tenant_id]:
            if _matching_existing_key(records, plaintext_key) is not None:
                already_present += 1
                continue

            if not apply:
                continue

            record = TenantApiKey(
                tenant_id=tenant_id,
                key_id=_new_bootstrap_key_id(session, tenant_id),
                key_prefix="bootstrap",
                key_hash=hash_api_key(plaintext_key),
                scopes=list(DEFAULT_BOOTSTRAP_SCOPES),
                created_by="one-time-bootstrap",
            )
            session.add(record)
            session.flush()
            session.add(
                AuthKeyAuditLog(
                    tenant_id=tenant_id,
                    key_id=record.key_id,
                    action="bootstrapped",
                    actor="operator:one-time-bootstrap",
                    meta={
                        "source": BOOTSTRAP_ENV_NAME,
                        "scopes": list(DEFAULT_BOOTSTRAP_SCOPES),
                    },
                )
            )
            records.append(record)
            imported += 1

    return TenantKeyBootstrapResult(
        requested=requested,
        imported=imported,
        already_present=already_present,
        dry_run=not apply,
    )


def bootstrap_from_environment(
    session: Session,
    *,
    apply: bool,
    environ: Mapping[str, str] | None = None,
) -> TenantKeyBootstrapResult:
    """Validate runtime policy and execute a plan/import from the explicit env."""
    source = environ if environ is not None else os.environ
    validate_bootstrap_runtime(source)
    payload = load_bootstrap_from_environment(source)
    # Convert immutable tuples into JSON-shape lists so the central validator
    # remains the only source of input-normalization rules.
    mutable_payload: MutableMapping[str, list[str]] = {
        tenant_id: list(keys) for tenant_id, keys in payload.items()
    }
    return bootstrap_tenant_api_keys(session, mutable_payload, apply=apply)


__all__ = [
    "BOOTSTRAP_ENV_NAME",
    "BootstrapDatabaseError",
    "BootstrapValidationError",
    "DEFAULT_BOOTSTRAP_SCOPES",
    "TenantKeyBootstrapResult",
    "bootstrap_from_environment",
    "bootstrap_tenant_api_keys",
    "load_bootstrap_from_environment",
    "normalize_bootstrap_payload",
    "validate_bootstrap_runtime",
]
