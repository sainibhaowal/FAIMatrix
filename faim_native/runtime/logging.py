"""FAIM-Native Structured Logging (Stage-9, Stage-11 hardened).

JSON-formatted logs with request context and secret redaction.

Stage-11: Added RedactingFilter to prevent sensitive data leaks.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Pattern

# =============================================================================
# Stage-11: Redaction Patterns
# =============================================================================

# Patterns that will be redacted from log messages
REDACT_PATTERNS: List[Pattern] = [
    # API keys and authorization headers
    re.compile(
        r'(?i)(x-api-key|x-admin-key|authorization)[=:\s"\']+[^\s"\']+', re.IGNORECASE
    ),
    re.compile(r'(?i)(api[_-]?key|apikey)[=:\s"\']+[^\s"\']+', re.IGNORECASE),
    # Passwords and secrets
    re.compile(r'(?i)(password|passwd|secret|token)[=:\s"\']+[^\s"\']+', re.IGNORECASE),
    # Database URLs with credentials
    re.compile(r"(?i)postgresql://[^@]+@", re.IGNORECASE),
    re.compile(r"(?i)redis://[^@]+@", re.IGNORECASE),
    # Bearer tokens (redact entire line portion after Bearer)
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    # Authorization header with full value
    re.compile(r"(?i)Authorization:\s+\S+.*", re.IGNORECASE),
    # FAIM-specific key patterns
    re.compile(r"faim_[a-f0-9]{6}_[a-zA-Z0-9_-]+"),  # Generated API keys
    re.compile(r"admin_[a-f0-9]{6}_[a-zA-Z0-9_-]+"),  # Admin keys
    # JSON key values (common in env vars)
    re.compile(r'"key":\s*"[^"]+"'),
    re.compile(r'"api_key":\s*"[^"]+"'),
]

REDACTION_PLACEHOLDER = "[REDACTED]"


def redact_sensitive(message: str) -> str:
    """Redact sensitive patterns from a log message."""
    result = message
    for pattern in REDACT_PATTERNS:
        result = pattern.sub(REDACTION_PLACEHOLDER, result)
    return result


class RedactingFilter(logging.Filter):
    """
    Log filter that redacts sensitive information.

    Stage-11: Prevents secrets from leaking to logs.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Redact the main message
        if record.msg:
            record.msg = redact_sensitive(str(record.msg))

        # Redact args if present
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: redact_sensitive(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    redact_sensitive(str(a)) if isinstance(a, str) else a
                    for a in record.args
                )

        return True


# =============================================================================
# JSON Formatter
# =============================================================================


class JSONFormatter(logging.Formatter):
    """JSON log formatter with FAIM context."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "msg": record.getMessage(),
            "module": record.module,
        }

        # Add FAIM context if present
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "tenant_id"):
            log_entry["tenant_id"] = record.tenant_id
        if hasattr(record, "graph_id"):
            log_entry["graph_id"] = record.graph_id
        if hasattr(record, "latency_ms"):
            log_entry["latency_ms"] = record.latency_ms

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


# =============================================================================
# Context Logger
# =============================================================================


class ContextLogger:
    """Logger that includes request context."""

    def __init__(self, logger: logging.Logger):
        self._logger = logger
        self._context: Dict[str, Any] = {}

    def bind(self, **kwargs) -> "ContextLogger":
        """Bind context values to logger."""
        new_logger = ContextLogger(self._logger)
        new_logger._context = {**self._context, **kwargs}
        return new_logger

    def _log(self, level: int, msg: str, *args, **kwargs):
        extra = {**self._context, **kwargs.get("extra", {})}
        self._logger.log(level, msg, *args, extra=extra)

    def debug(self, msg: str, *args, **kwargs):
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self._log(logging.ERROR, msg, *args, **kwargs)


# =============================================================================
# Setup
# =============================================================================


def setup_logging(level: str = "INFO", json_format: bool = True) -> None:
    """Configure logging for FAIM.

    Stage-11: Adds RedactingFilter to prevent secret leaks.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add new handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    # Stage-11: Add redacting filter
    handler.addFilter(RedactingFilter())

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(module)s | %(message)s")
        )

    root_logger.addHandler(handler)


def get_logger(name: str) -> ContextLogger:
    """Get a context logger."""
    return ContextLogger(logging.getLogger(name))


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "JSONFormatter",
    "ContextLogger",
    "RedactingFilter",
    "redact_sensitive",
    "setup_logging",
    "get_logger",
]
