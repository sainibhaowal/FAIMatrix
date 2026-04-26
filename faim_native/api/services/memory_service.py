"""K5 memory API service helpers."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional


def decode_base64_payload(payload: str) -> bytes:
    """Decode strict base64 payload with explicit errors."""
    try:
        return base64.b64decode(payload, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid bytes_base64 payload") from exc


def normalize_datetime_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Normalize datetime to UTC timezone."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def build_write_request_hash(
    *,
    graph_id: str,
    filename: str,
    content_type: str,
    payload_bytes: bytes,
    profile: str,
    persist_mode: str,
) -> str:
    """Build deterministic request hash for idempotency matching."""
    payload = {
        "graph_id": str(graph_id or "").strip(),
        "filename": str(filename or "").strip(),
        "content_type": str(content_type or "").strip().lower(),
        "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
        "profile": str(profile or "").strip().lower(),
        "persist_mode": str(persist_mode or "").strip().lower(),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_idempotency_key(
    *,
    header_value: Optional[str],
    body_value: Optional[str],
) -> Optional[str]:
    """Resolve and validate idempotency key from header/body values."""
    header_key = str(header_value or "").strip()
    body_key = str(body_value or "").strip()

    if header_key and body_key and header_key != body_key:
        raise ValueError("Idempotency key mismatch between header and body")
    key = header_key or body_key
    if not key:
        return None
    if len(key) > 128:
        raise ValueError("idempotency_key must be <= 128 characters")
    return key


def redact_error_text(text: Optional[str]) -> str:
    """Normalize and bound error text."""
    return str(text or "memory write failed").strip()[:1024]
