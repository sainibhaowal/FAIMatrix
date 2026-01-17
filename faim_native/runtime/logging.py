"""FAIM-Native Structured Logging (Stage-9).

JSON-formatted logs with request context.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict

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
    """Configure logging for FAIM."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add new handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

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
    "setup_logging",
    "get_logger",
]
