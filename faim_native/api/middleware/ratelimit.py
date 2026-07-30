"""FAIM-Native Rate Limiting Middleware (Stage-9).

Per-tenant token bucket rate limiting.
Fallback: Redis → in-memory.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# =============================================================================
# Token Bucket
# =============================================================================


@dataclass
class TokenBucket:
    """Simple token bucket for rate limiting."""

    capacity: int
    refill_rate: float  # tokens per second
    tokens: float
    last_refill: float

    @classmethod
    def create(cls, capacity: int, refill_per_minute: int) -> "TokenBucket":
        now = time.time()
        return cls(
            capacity=capacity,
            refill_rate=refill_per_minute / 60.0,
            tokens=float(capacity),
            last_refill=now,
        )

    def try_consume(self, tokens: int = 1) -> Tuple[bool, int]:
        """Try to consume tokens. Returns (allowed, remaining)."""
        now = time.time()
        elapsed = now - self.last_refill

        # Refill tokens
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, int(self.tokens)
        else:
            return False, int(self.tokens)


# =============================================================================
# Rate Limiter Store
# =============================================================================


class InMemoryRateLimiter:
    """In-memory rate limiter (fallback when Redis unavailable)."""

    def __init__(self):
        self._buckets: Dict[str, TokenBucket] = {}
        self._limits: Dict[str, int] = {
            "ingest": 60,
            "query": 120,
            "events": 300,
            "storage": 60,
            "api_keys": 30,
            # K6 endpoint policy categories
            "ingest_write": 60,
            "query_read": 120,
            "events_stream": 300,
            "storage_read": 120,
            "storage_write": 60,
            "api_keys_read": 60,
            "api_keys_write": 20,
            "memory_search": 120,
            "memory_read": 120,
            "memory_write": 60,
        }

    def set_limits(self, limits: Dict[str, int]) -> None:
        """Set rate limits from config."""
        if "ingest_per_minute" in limits:
            self._limits["ingest"] = limits["ingest_per_minute"]
        if "query_per_minute" in limits:
            self._limits["query"] = limits["query_per_minute"]
        if "events_per_minute" in limits:
            self._limits["events"] = limits["events_per_minute"]
        if "storage_per_minute" in limits:
            self._limits["storage"] = limits["storage_per_minute"]
        if "api_keys_per_minute" in limits:
            self._limits["api_keys"] = limits["api_keys_per_minute"]
        if "ingest_write_per_minute" in limits:
            self._limits["ingest_write"] = limits["ingest_write_per_minute"]
        if "query_read_per_minute" in limits:
            self._limits["query_read"] = limits["query_read_per_minute"]
        if "events_stream_per_minute" in limits:
            self._limits["events_stream"] = limits["events_stream_per_minute"]
        if "storage_read_per_minute" in limits:
            self._limits["storage_read"] = limits["storage_read_per_minute"]
        if "storage_write_per_minute" in limits:
            self._limits["storage_write"] = limits["storage_write_per_minute"]
        if "api_keys_read_per_minute" in limits:
            self._limits["api_keys_read"] = limits["api_keys_read_per_minute"]
        if "api_keys_write_per_minute" in limits:
            self._limits["api_keys_write"] = limits["api_keys_write_per_minute"]
        if "memory_search_per_minute" in limits:
            self._limits["memory_search"] = limits["memory_search_per_minute"]
        if "memory_read_per_minute" in limits:
            self._limits["memory_read"] = limits["memory_read_per_minute"]
        if "memory_write_per_minute" in limits:
            self._limits["memory_write"] = limits["memory_write_per_minute"]

    def _get_bucket_key(self, tenant_id: str, endpoint: str, identity: str) -> str:
        return f"{tenant_id}:{identity}:{endpoint}"

    def _get_or_create_bucket(
        self, tenant_id: str, endpoint: str, identity: str
    ) -> TokenBucket:
        key = self._get_bucket_key(tenant_id, endpoint, identity)
        if key not in self._buckets:
            limit = self._limits.get(endpoint, 60)
            self._buckets[key] = TokenBucket.create(
                capacity=limit, refill_per_minute=limit
            )
        return self._buckets[key]

    def check_rate_limit(
        self, tenant_id: str, endpoint: str, identity: Optional[str] = None
    ) -> Tuple[bool, int]:
        """Check if request is allowed. Returns (allowed, remaining)."""
        bucket = self._get_or_create_bucket(
            tenant_id, endpoint, identity or f"tenant:{tenant_id}"
        )
        return bucket.try_consume(1)


# =============================================================================
# Global Rate Limiter
# =============================================================================

_rate_limiter: Optional[InMemoryRateLimiter] = None


def get_rate_limiter() -> InMemoryRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = InMemoryRateLimiter()
    return _rate_limiter


# =============================================================================
# Middleware
# =============================================================================

# Endpoint to rate limit category mapping (legacy compatibility)
ENDPOINT_CATEGORIES = {
    # Current API routes
    "/api/v1/storage": "storage",
    "/api/v1/ingest": "ingest",
    "/api/v1/query": "query",
    "/api/v1/events": "events",
    "/api/v1/api-keys": "api_keys",
    "/api/v1/evolve": "query",
    "/api/v1/memory/search": "query",
    "/api/v1/memory/write": "ingest",
    "/api/v1/memory": "query",
    # Legacy compatibility routes
    "/v1/ingest": "ingest",
    "/v1/query": "query",
    "/v1/events": "events",
}


@dataclass(frozen=True)
class EndpointRateRule:
    method: str
    prefix: str
    category: str


ENDPOINT_METHOD_CATEGORIES: Sequence[EndpointRateRule] = (
    EndpointRateRule("POST", "/api/v1/ingest/upload", "ingest_write"),
    EndpointRateRule("POST", "/api/v1/ingest", "ingest_write"),
    EndpointRateRule("POST", "/api/v1/query", "query_read"),
    EndpointRateRule("GET", "/api/v1/events", "events_stream"),
    EndpointRateRule("POST", "/api/v1/storage", "storage_write"),
    EndpointRateRule("DELETE", "/api/v1/storage", "storage_write"),
    EndpointRateRule("GET", "/api/v1/storage", "storage_read"),
    EndpointRateRule("POST", "/api/v1/api-keys", "api_keys_write"),
    EndpointRateRule("GET", "/api/v1/api-keys", "api_keys_read"),
    EndpointRateRule("POST", "/api/v1/evolve", "ingest_write"),
    EndpointRateRule("GET", "/api/v1/evolve", "query_read"),
    EndpointRateRule("POST", "/api/v1/memory/search", "memory_search"),
    EndpointRateRule("GET", "/api/v1/memory", "memory_read"),
    EndpointRateRule("POST", "/api/v1/memory/write", "memory_write"),
    EndpointRateRule("PATCH", "/api/v1/memory", "memory_write"),
    # Legacy compatibility routes
    EndpointRateRule("POST", "/v1/ingest", "ingest_write"),
    EndpointRateRule("POST", "/v1/query", "query_read"),
    EndpointRateRule("GET", "/v1/events", "events_stream"),
    EndpointRateRule("POST", "/v1/evolve", "ingest_write"),
    EndpointRateRule("GET", "/v1/evolve", "query_read"),
)


def _path_matches(path: str, prefix: str) -> bool:
    normalized = prefix.rstrip("/")
    if path == normalized:
        return True
    return path.startswith(normalized + "/")


def classify_endpoint_category(method: str, path: str) -> Optional[str]:
    """Classify endpoint into rate-limit category (method-aware first)."""
    upper_method = method.upper()
    for rule in ENDPOINT_METHOD_CATEGORIES:
        if rule.method != upper_method:
            continue
        if _path_matches(path, rule.prefix):
            return rule.category

    for prefix in sorted(ENDPOINT_CATEGORIES.keys(), key=len, reverse=True):
        if _path_matches(path, prefix):
            return ENDPOINT_CATEGORIES[prefix]
    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware per tenant."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Get tenant ID from auth middleware context first, then headers fallback.
        tenant_id = getattr(request.state, "tenant_id", None) or request.headers.get(
            "X-Tenant-Id", ""
        )
        if not tenant_id:
            # Let auth middleware handle missing tenant
            return await call_next(request)

        # Determine identity for per-tenant-and-identity buckets.
        auth_method = getattr(request.state, "auth_method", None)
        if auth_method == "jwt":
            user_id = getattr(request.state, "user_id", None) or "unknown"
            identity = f"jwt:{user_id}"
        elif auth_method in {"api_key_db", "api_key_env", "api_key"}:
            key_id = getattr(request.state, "auth_key_id", None)
            identity = f"key:{key_id}" if key_id else f"tenant:{tenant_id}"
        else:
            identity = f"tenant:{tenant_id}"

        # Determine endpoint category
        path = request.url.path
        category = classify_endpoint_category(request.method, path)

        if not category:
            # Not a rate-limited endpoint
            return await call_next(request)

        # Check rate limit
        limiter = get_rate_limiter()
        allowed, remaining = limiter.check_rate_limit(
            tenant_id, category, identity=identity
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "category": category,
                    "remaining": remaining,
                    "retry_after_seconds": 60,
                },
                headers={
                    "X-RateLimit-Remaining": str(remaining),
                    "Retry-After": "60",
                },
            )

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "TokenBucket",
    "InMemoryRateLimiter",
    "RateLimitMiddleware",
    "get_rate_limiter",
]
