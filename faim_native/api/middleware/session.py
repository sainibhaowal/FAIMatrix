"""
FAIM-Native Session Middleware (Stage-11).

Provides secure session token management for browser UIs:
- Short-lived session tokens via HttpOnly cookies
- Token exchange flow (API key → session token)
- No API keys stored in browser localStorage

Architecture:
1. Client has API key (from admin)
2. Client calls POST /v1/auth/exchange with API key
3. Server validates, returns HttpOnly session cookie
4. Subsequent requests use session cookie
5. Session auto-expires after timeout
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Session duration (15 minutes default, rolling)
SESSION_DURATION_MINUTES = int(os.getenv("FAIM_SESSION_DURATION", "15"))

# Cookie settings
SESSION_COOKIE_NAME = "faim_session"
SESSION_COOKIE_SECURE = os.getenv("FAIM_COOKIE_SECURE", "true").lower() == "true"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "strict"

# Secret for HMAC (generate if not provided)
SESSION_SECRET = os.getenv("FAIM_SESSION_SECRET", "").encode() or secrets.token_bytes(32)


# =============================================================================
# Session Token
# =============================================================================

class SessionToken:
    """
    Secure session token.
    
    Format: <timestamp>.<tenant_id>.<random>.<signature>
    """
    
    def __init__(
        self,
        tenant_id: str,
        created_at: datetime,
        random_part: str,
    ):
        self.tenant_id = tenant_id
        self.created_at = created_at
        self.random_part = random_part
    
    @classmethod
    def generate(cls, tenant_id: str) -> "SessionToken":
        """Generate a new session token."""
        return cls(
            tenant_id=tenant_id,
            created_at=datetime.utcnow(),
            random_part=secrets.token_urlsafe(24),
        )
    
    def to_string(self) -> str:
        """Serialize token to string with HMAC signature."""
        timestamp = int(self.created_at.timestamp())
        payload = f"{timestamp}.{self.tenant_id}.{self.random_part}"
        
        # Sign with HMAC
        signature = hmac.new(
            SESSION_SECRET,
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()[:32]
        
        return f"{payload}.{signature}"
    
    @classmethod
    def from_string(cls, token_str: str) -> Optional["SessionToken"]:
        """
        Parse and verify a session token string.
        
        Returns None if token is invalid or tampered.
        """
        try:
            parts = token_str.split(".")
            if len(parts) != 4:
                return None
            
            timestamp_str, tenant_id, random_part, signature = parts
            
            # Reconstruct and verify signature
            payload = f"{timestamp_str}.{tenant_id}.{random_part}"
            expected_sig = hmac.new(
                SESSION_SECRET,
                payload.encode(),
                hashlib.sha256,
            ).hexdigest()[:32]
            
            if not hmac.compare_digest(signature, expected_sig):
                logger.warning("Invalid session signature")
                return None
            
            # Parse timestamp
            timestamp = int(timestamp_str)
            created_at = datetime.fromtimestamp(timestamp)
            
            return cls(
                tenant_id=tenant_id,
                created_at=created_at,
                random_part=random_part,
            )
            
        except (ValueError, TypeError, IndexError) as e:
            logger.warning(f"Failed to parse session token: {e}")
            return None
    
    def is_expired(self) -> bool:
        """Check if session has expired."""
        expiry = self.created_at + timedelta(minutes=SESSION_DURATION_MINUTES)
        return datetime.utcnow() > expiry
    
    def refresh(self) -> "SessionToken":
        """Create a refreshed token (rolling session)."""
        return SessionToken(
            tenant_id=self.tenant_id,
            created_at=datetime.utcnow(),
            random_part=self.random_part,
        )


# =============================================================================
# Cookie Helpers
# =============================================================================

def set_session_cookie(response: Response, token: SessionToken) -> None:
    """Set the session cookie on a response."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token.to_string(),
        max_age=SESSION_DURATION_MINUTES * 60,
        httponly=SESSION_COOKIE_HTTPONLY,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
    )


def clear_session_cookie(response: Response) -> None:
    """Clear the session cookie."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=SESSION_COOKIE_HTTPONLY,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
    )


def get_session_from_request(request: Request) -> Optional[SessionToken]:
    """Extract and validate session from request cookies."""
    token_str = request.cookies.get(SESSION_COOKIE_NAME)
    if not token_str:
        return None
    
    token = SessionToken.from_string(token_str)
    if token is None:
        return None
    
    if token.is_expired():
        logger.debug("Session expired")
        return None
    
    return token


# =============================================================================
# Session Middleware
# =============================================================================

class SessionMiddleware(BaseHTTPMiddleware):
    """
    Middleware for session-based authentication.
    
    Allows requests authenticated via:
    1. X-Api-Key header (traditional API key)
    2. Session cookie (for browser UIs)
    
    When a valid session is found, sets request.state.tenant_id.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Check for existing session
        session = get_session_from_request(request)
        
        if session:
            # Valid session found
            request.state.tenant_id = session.tenant_id
            request.state.session = session
            
            response = await call_next(request)
            
            # Rolling session: refresh on each request
            refreshed = session.refresh()
            set_session_cookie(response, refreshed)
            
            return response
        
        # No session, fall through to API key auth
        return await call_next(request)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "SessionToken",
    "SessionMiddleware",
    "set_session_cookie",
    "clear_session_cookie",
    "get_session_from_request",
    "SESSION_COOKIE_NAME",
    "SESSION_DURATION_MINUTES",
]
