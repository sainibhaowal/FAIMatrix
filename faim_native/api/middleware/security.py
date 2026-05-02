"""FAIM-Native API: Security Headers Middleware.

Adds standard security headers to all responses:
- Strict-Transport-Security (HSTS)
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Content-Security-Policy
- X-XSS-Protection
- Permissions-Policy
"""

from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


def _normalize_origin(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""

    parsed = urlparse(raw)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return raw.rstrip("/")


def _split_source_list(raw: str) -> list[str]:
    parts: list[str] = []
    for chunk in raw.replace(" ", ",").split(","):
        source = _normalize_origin(chunk)
        if source and source not in parts:
            parts.append(source)
    return parts


def _is_production_mode() -> bool:
    mode = (os.getenv("FAIM_MODE") or os.getenv("FAIM_ENV") or "").strip().lower()
    return mode in {"prod", "production"}


def _get_csp_connect_sources() -> list[str]:
    explicit = os.getenv("FAIM_CSP_CONNECT_SRC", "").strip()
    if explicit:
        return _split_source_list(explicit)

    sources = ["'self'", "https://api.resend.com"]
    for env_name in ("FAIM_PUBLIC_ORIGIN", "NEXTAUTH_URL"):
        origin = _normalize_origin(os.getenv(env_name, ""))
        if origin and origin not in sources:
            sources.append(origin)

    if not _is_production_mode():
        for origin in (
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:8010",
            "http://127.0.0.1:8010",
            "http://localhost:8011",
            "http://127.0.0.1:8011",
        ):
            if origin not in sources:
                sources.append(origin)

    return sources


def build_content_security_policy() -> str:
    """Build a CSP that is strict in production and relaxed only for local dev."""
    script_sources = ["'self'", "'unsafe-inline'"]
    if not _is_production_mode():
        script_sources.append("'unsafe-eval'")

    return (
        "default-src 'self'; "
        f"script-src {' '.join(script_sources)}; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https:; "
        f"connect-src {' '.join(_get_csp_connect_sources())}; "
        "frame-ancestors 'none';"
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # HSTS - Enforce HTTPS (1 year)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Content Security Policy (Strict)
        # Allows only same-origin and specific trusted sources
        response.headers["Content-Security-Policy"] = build_content_security_policy()

        # XSS Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        )

        return response
