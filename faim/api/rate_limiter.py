"""
FAIM Redis Rate Limiting

Provides rate limiting using SlowAPI + Redis backend.
Supports different limits for:
- Authenticated users (by user_id)
- API keys (by key_id)
- IP-based limiting for auth endpoints
"""
import logging
import os

from fastapi import HTTPException, Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RATE_LIMIT_USER = os.getenv("RATE_LIMIT_USER", "100/minute")
RATE_LIMIT_API_KEY = os.getenv("RATE_LIMIT_API_KEY", "1000/minute")
RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", "10/minute")
RATE_LIMIT_STORAGE = os.getenv("RATE_LIMIT_STORAGE", "20/minute")
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")


def get_user_identifier(request: Request) -> str:
    """
    Get rate limit key based on authentication method.
    Priority: user_id > api_key_id > IP address
    """
    # Check for authenticated user (set by JWT middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    
    # Check for API key (set by API key middleware)
    key_id = getattr(request.state, "api_key_id", None)
    if key_id:
        return f"key:{key_id}"
    
    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


def get_ip_only(request: Request) -> str:
    """Get IP address only (for auth endpoints)."""
    return f"ip:{get_remote_address(request)}"


# Check if Redis is available
def is_redis_available() -> bool:
    """Check if Redis is configured and reachable."""
    try:
        import redis
        url = os.getenv("REDIS_URL", "").strip()
        if not url:
            return False
        r = redis.from_url(url, socket_connect_timeout=1)
        r.ping()
        return True
    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        return False


def get_redis():
    """Get Redis client (returns None if not available)."""
    try:
        import redis
        url = os.getenv("REDIS_URL", "").strip()
        if not url:
            return None
        return redis.from_url(url, socket_connect_timeout=1)
    except Exception:
        return None


# Create limiter based on Redis availability
def create_limiter() -> Limiter:
    """Create rate limiter with appropriate storage backend."""
    if is_redis_available():
        logger.info(f"Using Redis for rate limiting: {REDIS_URL}")
        return Limiter(
            key_func=get_user_identifier,
            storage_uri=REDIS_URL,
            default_limits=[RATE_LIMIT_DEFAULT],
        )
    else:
        logger.warning("Redis not available, using in-memory rate limiting")
        return Limiter(
            key_func=get_user_identifier,
            default_limits=[RATE_LIMIT_DEFAULT],
        )


# Global limiter instance
limiter = create_limiter()


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded errors."""
    logger.warning(f"Rate limit exceeded: {get_user_identifier(request)} on {request.url.path}")
    return HTTPException(
        status_code=429,
        detail={
            "error": "rate_limit_exceeded",
            "message": f"Too many requests. Limit: {exc.detail}",
            "retry_after": getattr(exc, "retry_after", 60),
        },
    )


# Decorator factories for different limit types
def user_rate_limit(limit: str = None):
    """Rate limit decorator for user-authenticated endpoints."""
    return limiter.limit(limit or RATE_LIMIT_USER, key_func=get_user_identifier)


def api_key_rate_limit(limit: str = None):
    """Rate limit decorator for API key endpoints."""
    return limiter.limit(limit or RATE_LIMIT_API_KEY, key_func=get_user_identifier)


def auth_rate_limit(limit: str = None):
    """Rate limit decorator for auth endpoints (IP-based)."""
    return limiter.limit(limit or RATE_LIMIT_AUTH, key_func=get_ip_only)


def storage_rate_limit(limit: str = None):
    """Rate limit decorator for storage/upload endpoints."""
    return limiter.limit(limit or RATE_LIMIT_STORAGE, key_func=get_user_identifier)


def setup_rate_limiting(app):
    """
    Configure rate limiting for a FastAPI app.
    
    NOTE: We do NOT use SlowAPIMiddleware globally as it conflicts with SSE streaming.
    Instead, use @limiter.limit() decorators on individual routes.
    
    Call this in your app setup:
        from faim.api.rate_limiter import setup_rate_limiting
        setup_rate_limiting(app)
    """
    app.state.limiter = limiter
    # Do NOT add SlowAPIMiddleware - it breaks SSE streaming responses
    # app.add_middleware(SlowAPIMiddleware)  # DISABLED
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    logger.info("Rate limiting configured (decorator-based, no global middleware)")


# Utility function to check remaining quota
async def check_rate_limit(request: Request, limit: str = "60/minute") -> dict:
    """
    Check rate limit status without consuming a request.
    Returns info about current limit state.
    """
    key = get_user_identifier(request)
    # This would require direct Redis access to get remaining count
    # For now, return a simple status
    return {
        "key": key,
        "limit": limit,
        "status": "ok",
    }
