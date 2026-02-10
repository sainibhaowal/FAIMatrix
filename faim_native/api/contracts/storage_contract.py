"""Storage API contract freeze and compatibility checks (Phase A).

This module defines the canonical storage route/method matrix and required
response fields. It is used at startup and in tests to detect accidental
breaking changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Set, Tuple

from fastapi.routing import APIRoute

CONTRACT_VERSION = "2026-02-10.phaseA"

# Canonical method+path matrix for /api/v1/storage endpoints.
REQUIRED_STORAGE_ROUTES: Set[Tuple[str, str]] = {
    ("POST", "/storage/uploads"),
    ("GET", "/storage/uploads/{job_id}"),
    ("GET", "/storage/uploads/{job_id}/events"),
    ("GET", "/storage/files"),
    ("GET", "/storage/files/{raw_id}"),
    ("DELETE", "/storage/files/{raw_id}"),
    ("POST", "/storage/files/{raw_id}/ingest"),
    ("POST", "/storage/files/{raw_id}/retry"),
    ("GET", "/storage/summary"),
    ("GET", "/storage/ops/metrics"),
    ("GET", "/storage/backends/health"),
}

# Required fields by response model name.
REQUIRED_MODEL_FIELDS: Dict[str, Set[str]] = {
    "StorageFileItem": {
        "raw_id",
        "graph_id",
        "filename",
        "mime_type",
        "size_bytes",
        "sha256",
        "ingest_status",
        "packet_hash",
        "node_count",
        "vector_count",
        "error",
        "uploaded_at",
        "ingested_at",
        "updated_at",
        "delete_requested",
    },
    "StorageUploadBatchResponse": {
        "job_id",
        "graph_id",
        "status",
        "requested_files",
        "processed_files",
        "success_files",
        "failed_files",
        "dedup_hits",
        "files",
    },
    "StorageUploadStatusResponse": {
        "job_id",
        "graph_id",
        "status",
        "requested_files",
        "processed_files",
        "success_files",
        "failed_files",
        "dedup_hits",
        "created_at",
        "updated_at",
        "completed_at",
        "files",
    },
    "StorageJobEventsResponse": {"job_id", "events"},
    "StorageFileListResponse": {"items", "total", "limit", "offset"},
    "StorageSummaryResponse": {
        "graph_id",
        "total_files",
        "total_bytes",
        "by_status",
        "by_type",
    },
    "StorageBackendsHealth": {"postgres", "redis", "qdrant", "raw_store"},
    "StorageOpsMetricsResponse": {
        "graph_id",
        "window_seconds",
        "generated_at",
        "upload_count",
        "upload_bytes",
        "processed_files",
        "dedup_hits",
        "dedup_ratio",
        "failures_total",
        "failure_reasons",
        "phase_latency_ms",
        "backend_states",
    },
    "StorageIngestActionResponse": {"status", "file", "ingest"},
}


@dataclass(frozen=True)
class ContractValidationResult:
    """Result object for contract validation."""

    version: str
    errors: List[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def _iter_storage_routes(routes: Iterable[object]) -> Iterable[APIRoute]:
    for route in routes:
        if isinstance(route, APIRoute):
            yield route


def validate_storage_router_contract(routes: Iterable[object]) -> ContractValidationResult:
    """Validate storage route matrix and response model field contracts."""
    errors: List[str] = []
    observed: Set[Tuple[str, str]] = set()

    for route in _iter_storage_routes(routes):
        for method in sorted(route.methods or []):
            if method in {"HEAD", "OPTIONS"}:
                continue
            observed.add((method.upper(), route.path))

        response_model = route.response_model
        if response_model is None:
            continue

        model_name = getattr(response_model, "__name__", "")
        required = REQUIRED_MODEL_FIELDS.get(model_name)
        if not required:
            continue

        fields = set(getattr(response_model, "model_fields", {}).keys())
        missing = sorted(required - fields)
        if missing:
            errors.append(
                f"Response model {model_name} missing required fields: {', '.join(missing)}"
            )

    missing_routes = sorted(REQUIRED_STORAGE_ROUTES - observed)
    for method, path in missing_routes:
        errors.append(f"Missing required storage route: {method} {path}")

    return ContractValidationResult(version=CONTRACT_VERSION, errors=errors)


def assert_storage_router_contract(routes: Iterable[object]) -> None:
    """Raise on contract violations."""
    result = validate_storage_router_contract(routes)
    if result.ok:
        return
    details = "; ".join(result.errors)
    raise RuntimeError(
        f"Storage API contract validation failed (v={result.version}): {details}"
    )


__all__ = [
    "CONTRACT_VERSION",
    "REQUIRED_STORAGE_ROUTES",
    "REQUIRED_MODEL_FIELDS",
    "ContractValidationResult",
    "validate_storage_router_contract",
    "assert_storage_router_contract",
]
