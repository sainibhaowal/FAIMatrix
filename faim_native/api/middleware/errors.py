"""
FAIM-Native Error Handling Middleware (Stage-11).

Security-focused error handling:
- Generic error messages to clients (no stack traces)
- Detailed logging for debugging (redacted)
- Consistent error response format
"""

from __future__ import annotations

import logging
import traceback
from typing import Callable

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# =============================================================================
# Error Response Model
# =============================================================================

def create_error_response(
    status_code: int,
    message: str,
    request_id: str | None = None,
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        status_code: HTTP status code.
        message: Generic, safe error message for the client.
        request_id: Optional request ID for correlation.
        
    Returns:
        JSONResponse with error details.
    """
    content = {
        "error": message,
        "status_code": status_code,
    }
    
    if request_id:
        content["request_id"] = request_id
    
    return JSONResponse(status_code=status_code, content=content)


# =============================================================================
# Generic Error Messages (Security: No internal details)
# =============================================================================

GENERIC_ERROR_MESSAGES = {
    400: "Bad request",
    401: "Authentication required",
    403: "Access denied",
    404: "Resource not found",
    405: "Method not allowed",
    409: "Conflict",
    413: "Payload too large",
    415: "Unsupported media type",
    422: "Validation error",
    429: "Too many requests",
    500: "Internal server error",
    502: "Bad gateway",
    503: "Service unavailable",
    504: "Gateway timeout",
}


def get_safe_error_message(status_code: int, detail: str | None = None) -> str:
    """
    Get a safe error message for a status code.
    
    For 4xx errors, we can include some detail.
    For 5xx errors, always return generic message.
    
    Args:
        status_code: HTTP status code.
        detail: Optional detail (only used for 4xx).
        
    Returns:
        Safe error message.
    """
    if 400 <= status_code < 500:
        # For client errors, we can be slightly more specific
        if detail and len(detail) < 200:
            return detail
        return GENERIC_ERROR_MESSAGES.get(status_code, "Client error")
    else:
        # For server errors, always generic
        return GENERIC_ERROR_MESSAGES.get(status_code, "Internal server error")


# =============================================================================
# Error Handling Middleware
# =============================================================================

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for secure error handling.
    
    Stage-11 Security:
    - Never expose stack traces to clients
    - Never expose internal paths or configurations
    - Log full details for debugging (with redaction)
    - Return consistent error format
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        try:
            response = await call_next(request)
            return response
            
        except HTTPException as exc:
            # FastAPI/Starlette HTTPException
            request_id = getattr(request.state, "request_id", None)
            
            # Log the exception (will be redacted by RedactingFilter)
            logger.warning(
                f"HTTP {exc.status_code} on {request.url.path}: {exc.detail}",
                extra={"request_id": request_id},
            )
            
            return create_error_response(
                status_code=exc.status_code,
                message=get_safe_error_message(exc.status_code, str(exc.detail)),
                request_id=request_id,
            )
            
        except Exception as exc:
            # Unexpected exception - NEVER expose details
            request_id = getattr(request.state, "request_id", None)
            
            # Log full traceback for debugging (will be redacted)
            logger.error(
                f"Unhandled exception on {request.url.path}: {type(exc).__name__}",
                exc_info=True,
                extra={"request_id": request_id},
            )
            
            # Return generic 500 error
            return create_error_response(
                status_code=500,
                message="Internal server error",
                request_id=request_id,
            )


# =============================================================================
# Exception Handlers for FastAPI
# =============================================================================

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTPException with secure messaging.
    
    Register with FastAPI:
        app.add_exception_handler(HTTPException, http_exception_handler)
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={"request_id": request_id},
    )
    
    return create_error_response(
        status_code=exc.status_code,
        message=get_safe_error_message(exc.status_code, str(exc.detail)),
        request_id=request_id,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all unhandled exceptions securely.
    
    Register with FastAPI:
        app.add_exception_handler(Exception, generic_exception_handler)
    """
    request_id = getattr(request.state, "request_id", None)
    
    # Log full traceback for debugging
    logger.error(
        f"Unhandled exception: {type(exc).__name__}",
        exc_info=True,
        extra={"request_id": request_id},
    )
    
    # Return generic error to client
    return create_error_response(
        status_code=500,
        message="Internal server error",
        request_id=request_id,
    )
