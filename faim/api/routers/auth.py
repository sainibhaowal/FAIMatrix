# =============================================================================
# FAIM Auth Router - OTP Passwordless Authentication
# =============================================================================
# File: faim/api/routers/auth.py
#
# Endpoints:
#     POST /api/v1/auth/otp/request  - Request OTP code
#     POST /api/v1/auth/otp/verify   - Verify OTP and get tokens
#     POST /api/v1/auth/refresh      - Refresh access token
#     POST /api/v1/auth/logout       - Revoke refresh token
#     GET  /api/v1/auth/me           - Get current user info
#
# Security:
#     - OTP via cryptographically secure secrets module
#     - SHA256 hashing for OTP storage
#     - JWT with HMAC-SHA256 signing
#     - Rate limiting: 3 requests per email per 15 minutes
# =============================================================================

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from faim.api.auth.email import send_otp_email
from faim.api.auth.jwt_auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    revoke_refresh_token,
    verify_refresh_token,
)
from faim.api.auth.otp import create_otp, verify_otp
from faim.config.database import get_db
from faim.config.models import GraphOwnership, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class OTPRequestPayload(BaseModel):
    """Request body for OTP code request."""

    email: EmailStr


class OTPRequestResponse(BaseModel):
    """Response for OTP code request."""

    success: bool
    message: str
    expires_in: int = 300  # 5 minutes


class OTPVerifyPayload(BaseModel):
    """Request body for OTP verification."""

    email: EmailStr
    code: str


class OTPVerifyResponse(BaseModel):
    """Response for successful OTP verification."""

    success: bool
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600  # 1 hour
    user: dict


class RefreshPayload(BaseModel):
    """Request body for token refresh."""

    refresh_token: str


class RefreshResponse(BaseModel):
    """Response for token refresh."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600


class LogoutPayload(BaseModel):
    """Request body for logout."""

    refresh_token: str


class LogoutResponse(BaseModel):
    """Response for logout."""

    success: bool
    message: str


class ErrorResponse(BaseModel):
    """Error response."""

    success: bool = False
    error: str


# =============================================================================
# OTP Endpoints
# =============================================================================


@router.post("/otp/request", response_model=OTPRequestResponse)
async def request_otp(payload: OTPRequestPayload, db: Session = Depends(get_db)):
    """
    Request an OTP code for passwordless login.

    Rate limited: 3 requests per email per 15 minutes.
    OTP expires in 5 minutes.

    The OTP is sent to the provided email address.
    """
    email = payload.email.lower().strip()

    # Create OTP
    code, error = create_otp(db, email)

    if error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error,
        )

    # Get user name if exists (for email personalization)
    user = db.query(User).filter(User.email == email).first()
    name = user.full_name if user else None

    # Send OTP email
    try:
        await send_otp_email(email, code, name)
    except Exception as e:
        logger.error(f"Failed to send OTP email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code. Please try again.",
        )

    logger.info(f"OTP requested for {email}")

    return OTPRequestResponse(
        success=True,
        message="Verification code sent to your email.",
        expires_in=300,
    )


@router.post("/otp/verify")
async def verify_otp_endpoint(payload: OTPVerifyPayload, db: Session = Depends(get_db)):
    """
    Verify OTP code and receive authentication tokens.

    On success:
    - Returns access_token (1 hour) and refresh_token (7 days)
    - Creates user account if first login
    - Creates user's graph if first login

    Security:
    - Max 3 verification attempts per OTP
    - OTP expires in 5 minutes
    - Constant-time comparison
    """
    email = payload.email.lower().strip()
    code = payload.code.strip()

    # Verify OTP
    success, error, user = verify_otp(db, email, code)

    if not success:
        # Determine appropriate status code
        if "Too many" in error or "attempts" in error.lower():
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        elif "expired" in error.lower():
            status_code = status.HTTP_410_GONE
        else:
            status_code = status.HTTP_401_UNAUTHORIZED

        raise HTTPException(status_code=status_code, detail=error)

    # Get user's graph
    graph = db.query(GraphOwnership).filter(GraphOwnership.user_id == user.id).first()
    graph_id = graph.graph_id if graph else None

    # Create tokens
    access_token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        graph_id=graph_id,
    )
    refresh_token = create_refresh_token(db, str(user.id))

    logger.info(f"User logged in via OTP: {email}")

    return OTPVerifyResponse(
        success=True,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,
        user={
            "id": str(user.id),
            "email": user.email,
            "name": user.full_name,
            "graph_id": graph_id,
        },
    )


# =============================================================================
# Token Management Endpoints
# =============================================================================


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_access_token(payload: RefreshPayload, db: Session = Depends(get_db)):
    """
    Refresh an access token using a valid refresh token.

    Returns a new access token (1 hour).
    The refresh token remains valid until expiration or logout.
    """
    user = verify_refresh_token(db, payload.refresh_token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Get user's graph
    graph = db.query(GraphOwnership).filter(GraphOwnership.user_id == user.id).first()
    graph_id = graph.graph_id if graph else None

    # Create new access token
    access_token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        graph_id=graph_id,
    )

    logger.info(f"Token refreshed for user {user.email}")

    return RefreshResponse(
        access_token=access_token,
        expires_in=3600,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(payload: LogoutPayload, db: Session = Depends(get_db)):
    """
    Logout by revoking the refresh token.

    The access token will remain valid until expiration (1 hour max).
    For immediate invalidation, implement token blacklist (future).
    """
    revoked = revoke_refresh_token(db, payload.refresh_token)

    if not revoked:
        # Don't reveal if token existed - just acknowledge
        pass

    return LogoutResponse(
        success=True,
        message="Logged out successfully.",
    )


# =============================================================================
# User Info Endpoint
# =============================================================================


class UserInfoResponse(BaseModel):
    """Response for user info."""

    id: str
    email: str
    name: Optional[str]
    graph_id: Optional[str]
    email_verified: bool
    plan: str


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    db: Session = Depends(get_db),
    token_payload: dict = Depends(get_current_user),
):
    """
    Get current authenticated user's information.

    Requires valid access token in Authorization header.
    """
    user_id = token_payload.get("sub")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get user's graph
    graph = db.query(GraphOwnership).filter(GraphOwnership.user_id == user.id).first()
    graph_id = graph.graph_id if graph else None

    return UserInfoResponse(
        id=str(user.id),
        email=user.email,
        name=user.full_name,
        graph_id=graph_id,
        email_verified=user.email_verified or False,
        plan=user.plan or "free",
    )
