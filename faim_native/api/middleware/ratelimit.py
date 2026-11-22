"""FAIM-Native Rate Limiting Middleware (Stage-9).

Per-tenant token bucket rate limiting.
Fallback: Redis → in-memory.
"""

from __future__ import annotations

import logging
import math
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("faim.ratelimit")

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
        allowed, remaining, _, _ = self.try_consume_detailed(tokens)
        return allowed, remaining

    def try_consume_detailed(self, tokens: int = 1) -> Tuple[bool, int, int, int]:
        """Try to consume tokens.

        Returns (allowed, remaining, retry_after_seconds, reset_epoch).
        """
        now = time.time()
        elapsed = max(0.0, now - self.last_refill)

        # Refill tokens
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            needed_to_full = max(0.0, self.capacity - self.tokens)
            reset_seconds = (
                math.ceil(needed_to_full / self.refill_rate)
                if self.refill_rate > 0
                else 0
            )
            return True, int(self.tokens), 0, int(now + reset_seconds)

        deficit = max(0.0, tokens - self.tokens)
        retry_after = (
            max(1, math.ceil(deficit / self.refill_rate))
            if self.refill_rate > 0
            else 60
        )
        needed_to_full = max(0.0, self.capacity - self.tokens)
        reset_seconds = (
            math.ceil(needed_to_full / self.refill_rate) if self.refill_rate > 0 else 60
        )
        return False, int(self.tokens), retry_after, int(now + reset_seconds)


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
            "events_stream": 600,
            "storage_read": 600,
            "storage_write": 300,
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
        allowed, remaining, _, _, _ = self.check_rate_limit_detailed(
            tenant_id, endpoint, identity=identity
        )
        return allowed, remaining

    def check_rate_limit_detailed(
        self, tenant_id: str, endpoint: str, identity: Optional[str] = None
    ) -> Tuple[bool, int, int, int, int]:
        """Check rate limit with full header metadata.

        Returns (allowed, remaining, limit, retry_after_seconds, reset_epoch).
        """
        bucket = self._get_or_create_bucket(
            tenant_id, endpoint, identity or f"tenant:{tenant_id}"
        )
        allowed, remaining, retry_after, reset_epoch = bucket.try_consume_detailed(1)
        return allowed, remaining, bucket.capacity, retry_after, reset_epoch


_REDIS_TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])

local data = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(data[1])
local last_refill = tonumber(data[2])

if tokens == nil or last_refill == nil then
    tokens = capacity
    last_refill = now
else
    local elapsed = math.max(0, now - last_refill)
    tokens = math.min(capacity, tokens + elapsed * refill_rate)
    last_refill = now
end

local allowed = 0
local retry_after = 0
if tokens >= requested then
    tokens = tokens - requested
    allowed = 1
else
    local deficit = math.max(0, requested - tokens)
    if refill_rate > 0 then
        retry_after = math.max(1, math.ceil(deficit / refill_rate))
    else
        retry_after = 60
    end
end

local reset_seconds = 0
if refill_rate > 0 then
    reset_seconds = math.ceil(math.max(0, capacity - tokens) / refill_rate)
end

redis.call('HMSET', key, 'tokens', tokens, 'last_refill', last_refill)
redis.call('EXPIRE', key, ttl)

return {allowed, math.floor(tokens), retry_after, math.floor(now + reset_seconds)}
"""


class RedisRateLimiter(InMemoryRateLimiter):
    """Distributed Redis-backed token bucket limiter with in-memory fallback."""

    def __init__(self, redis_url: Optional[str] = None):
        super().__init__()
        self._redis_url = redis_url or os.getenv("REDIS_URL", "").strip()
        self._redis_client: Any = None
        self._redis_script: Any = None
        self._redis_lock = threading.Lock()
        self._next_reconnect_at = 0.0

    def _get_script(self):
        if not self._redis_url:
            return None
        now = time.time()
        if self._redis_script is not None:
            return self._redis_script
        if now < self._next_reconnect_at:
            return None
        with self._redis_lock:
            if self._redis_script is not None:
                return self._redis_script
            if time.time() < self._next_reconnect_at:
                return None
            try:
                import redis

                client = redis.from_url(
                    self._redis_url,
                    decode_responses=True,
                    socket_connect_timeout=0.5,
                    socket_timeout=0.5,
                )
                client.ping()
                self._redis_client = client
                self._redis_script = client.register_script(_REDIS_TOKEN_BUCKET_LUA)
                return self._redis_script
            except Exception as exc:
                self._next_reconnect_at = time.time() + 15.0
                logger.warning(
                    "Redis rate limiter unavailable, using in-memory fallback: %s", exc
                )
                return None

    def check_rate_limit_detailed(
        self, tenant_id: str, endpoint: str, identity: Optional[str] = None
    ) -> Tuple[bool, int, int, int, int]:
        limit = int(self._limits.get(endpoint, 60))
        script = self._get_script()
        if script is not None:
            ident = identity or f"tenant:{tenant_id}"
            key = f"faim:rl:{self._get_bucket_key(tenant_id, endpoint, ident)}"
            now = time.time()
            refill_rate = limit / 60.0
            try:
                res = script(
                    keys=[key],
                    args=[limit, refill_rate, now, 1, 180],
                )
                allowed = bool(int(res[0]))
                remaining = int(res[1])
                retry_after = int(res[2])
                reset_epoch = int(res[3])
                return allowed, remaining, limit, retry_after, reset_epoch
            except Exception as exc:
                self._redis_script = None
                self._next_reconnect_at = time.time() + 15.0
                logger.warning(
                    "Redis rate limit eval failed, falling back to in-memory: %s", exc
                )

        return super().check_rate_limit_detailed(tenant_id, endpoint, identity=identity)


# =============================================================================
# Global Rate Limiter
# =============================================================================

_rate_limiter: Optional[InMemoryRateLimiter] = None


def get_rate_limiter() -> InMemoryRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        if os.getenv("REDIS_URL", "").strip():
            _rate_limiter = RedisRateLimiter()
        else:
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
        allowed, remaining, limit, retry_after, reset_epoch = (
            limiter.check_rate_limit_detailed(tenant_id, category, identity=identity)
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "category": category,
                    "limit": limit,
                    "remaining": remaining,
                    "retry_after_seconds": retry_after,
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_epoch),
                    "Retry-After": str(retry_after),
                },
            )

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_epoch)

        return response


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "TokenBucket",
    "InMemoryRateLimiter",
    "RedisRateLimiter",
    "RateLimitMiddleware",
    "get_rate_limiter",
]
