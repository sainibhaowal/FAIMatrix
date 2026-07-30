"""Lightweight middleware to record per-request latency for benchmarks.

Records request latencies in an in-memory buffer. Latencies are available
for querying but not persisted to database by this middleware.
Adds < 1ms overhead per request.
"""

import time
from collections import deque
from datetime import datetime
from typing import Callable, Deque, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class LatencySample:
    """Single request latency sample."""

    __slots__ = (
        "tenant_id",
        "graph_id",
        "endpoint",
        "method",
        "latency_ms",
        "status",
        "recorded_at",
    )

    def __init__(
        self,
        tenant_id: str,
        graph_id: Optional[str],
        endpoint: str,
        method: str,
        latency_ms: float,
        status: int,
    ):
        self.tenant_id = tenant_id
        self.graph_id = graph_id
        self.endpoint = endpoint
        self.method = method
        self.latency_ms = latency_ms
        self.status = status
        self.recorded_at = datetime.now()


class LatencyCollector:
    """In-memory buffer for latency samples."""

    def __init__(self, max_buffer: int = 500):
        self.buffer: Deque[LatencySample] = deque(maxlen=max_buffer)
        self.max_buffer = max_buffer

    def record(self, sample: LatencySample) -> None:
        """Add sample to buffer. Non-blocking."""
        self.buffer.append(sample)

    def get_samples(
        self,
        graph_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get recent samples, optionally filtered by graph_id or endpoint."""
        samples = list(self.buffer)
        if graph_id:
            samples = [s for s in samples if s.graph_id == graph_id]
        if endpoint:
            samples = [s for s in samples if s.endpoint == endpoint]

        # Convert to dict for JSON serialization
        result = []
        for s in samples[-limit:]:
            result.append(
                {
                    "tenant_id": s.tenant_id,
                    "graph_id": s.graph_id,
                    "endpoint": s.endpoint,
                    "method": s.method,
                    "latency_ms": s.latency_ms,
                    "status": s.status,
                    "recorded_at": s.recorded_at.isoformat(),
                }
            )
        return result

    def get_percentile(
        self,
        percentile: int,
        graph_id: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> float:
        """Get latency percentile for a graph_id/endpoint or all."""
        samples = list(self.buffer)
        if graph_id:
            samples = [s for s in samples if s.graph_id == graph_id]
        if endpoint:
            samples = [s for s in samples if s.endpoint == endpoint]

        if not samples:
            return 0.0
        latencies = sorted([s.latency_ms for s in samples])
        idx = max(0, int(len(latencies) * percentile / 100) - 1)
        return float(latencies[idx])


# Global singleton
_collector = LatencyCollector()


class LatencyCollectorMiddleware(BaseHTTPMiddleware):
    """Record request latency for benchmarking."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.monotonic()

        # Extract tenant_id and graph_id from headers/scope
        tenant_id = request.headers.get("x-tenant-id", "unknown")
        graph_id = request.query_params.get("graph_id") or request.headers.get(
            "x-graph-id"
        )

        try:
            response = await call_next(request)
        except Exception:
            # If call_next raises, still record it
            elapsed_ms = (time.monotonic() - start) * 1000
            sample = LatencySample(
                tenant_id=tenant_id,
                graph_id=graph_id,
                endpoint=request.url.path,
                method=request.method,
                latency_ms=elapsed_ms,
                status=500,
            )
            _collector.record(sample)
            raise

        elapsed_ms = (time.monotonic() - start) * 1000

        # Skip recording for health/ready endpoints
        if request.url.path not in ("/health", "/ready"):
            sample = LatencySample(
                tenant_id=tenant_id,
                graph_id=graph_id,
                endpoint=request.url.path,
                method=request.method,
                latency_ms=elapsed_ms,
                status=response.status_code,
            )
            _collector.record(sample)

        return response


def get_latency_collector() -> LatencyCollector:
    """Get global latency collector singleton."""
    return _collector
