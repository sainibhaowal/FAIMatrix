"""
FAIM Auth Router - Email/Password Authentication

NEW MODULE - Provides endpoints for user registration and verification.
Uses Argon2 for password hashing (strongest algorithm).

Endpoints:
    POST /api/v1/auth/register - Create new user account
    POST /api/v1/auth/verify - Verify credentials for NextAuth
    POST /api/v1/auth/verify-email - Verify email with token
    POST /api/v1/auth/resend-verification - Resend verification email
"""

import datetime
import logging
import re
import uuid
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from faim.db import get_db
from faim.models_sql import GraphOwnership, Org, OrgMember, Project, User
from faim.services.email_service import (
    generate_verification_token,
    send_verification_email,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Argon2 password hasher with secure defaults
ph = PasswordHasher(
    time_cost=3,  # Number of iterations
    memory_cost=65536,  # 64 MB memory usage
    parallelism=4,  # Parallel threads
    hash_len=32,  # Hash length
    salt_len=16,  # Salt length
)


# =============================================================================
# Schemas
# =============================================================================


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str
    name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        return v


class RegisterResponse(BaseModel):
    """User registration response."""

    success: bool
    user_id: str
    email: str
    message: str


class VerifyRequest(BaseModel):
    """Credential verification request (for NextAuth)."""

    email: EmailStr
    password: str


class VerifyResponse(BaseModel):
    """Credential verification response."""

    valid: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    project_id: Optional[str] = None
    graph_id: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================


def hash_password(password: str) -> str:
    """Hash password using Argon2."""
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against Argon2 hash."""
    try:
        ph.verify(password_hash, password)
        return True
    except VerifyMismatchError:
        return False


def ensure_user_resources(user: User, db: Session) -> tuple[str, str]:
    """Create default org, project, and graph for user."""
    # Check for existing org membership
    membership = db.query(OrgMember).filter(OrgMember.user_id == user.id).first()

    if not membership:
        # Create personal org
        org = Org(
            name=f"{user.full_name or user.email}'s Workspace",
            owner_user_id=user.id,
        )
        db.add(org)
        db.commit()
        db.refresh(org)

        membership = OrgMember(
            org_id=org.id,
            user_id=user.id,
            role="owner",
        )
        db.add(membership)
        db.commit()

    org_id = membership.org_id

    # Find or create project
    project = db.query(Project).filter(Project.org_id == org_id).first()

    if not project:
        project = Project(
            org_id=org_id,
            name="My FAIM Project",
        )
        db.add(project)
        db.commit()
        db.refresh(project)

    # Find or create graph
    graph = db.query(GraphOwnership).filter(GraphOwnership.project_id == project.id).first()

    if not graph:
        # Uses full UUID for production collision safety
        graph_id = f"U:{uuid.uuid4()}"

        graph = GraphOwnership(
            graph_id=graph_id,
            project_id=project.id,
            name="My Universe",
        )
        db.add(graph)
        db.commit()
        db.refresh(graph)

    return str(project.id), graph.graph_id


# =============================================================================
# API Endpoints
# =============================================================================


@router.post("/register", response_model=RegisterResponse)
async def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account.

    Creates user with hashed password and sends verification email.

    Args:
        email: User's email address
        password: Password (min 8 chars, must have letter and number)
        name: Optional display name

    Returns:
        User ID and success message
    """
    # Check if email already exists
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Hash password with Argon2
    password_hash = hash_password(request.password)

    # Generate verification token
    token = generate_verification_token()
    expires = datetime.datetime.utcnow() + datetime.timedelta(hours=24)

    # Create user (pending verification)
    user = User(
        email=request.email,
        password_hash=password_hash,
        full_name=request.name,
        status="active",  # Active immediately (can change to pending_verification)
        email_verified=False,
        email_verification_token=token,
        email_verification_expires=expires,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create default resources (org, project, graph)
    try:
        ensure_user_resources(user, db)
    except Exception as e:
        logger.error(f"Failed to create user resources: {e}")

    # Send verification email (async, don't block on failure)
    try:
        await send_verification_email(request.email, token, request.name)
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")

    logger.info(f"Registered new user: {user.email} ({user.id})")

    return RegisterResponse(
        success=True,
        user_id=str(user.id),
        email=user.email,
        message="Account created! Check your email to verify your account.",
    )


@router.post("/verify", response_model=VerifyResponse)
async def verify_credentials(request: VerifyRequest, db: Session = Depends(get_db)):
    """
    Verify user credentials for NextAuth.

    Called by NextAuth CredentialsProvider to validate login.

    Args:
        email: User's email
        password: User's password

    Returns:
        User info if valid, or valid=false if invalid
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        logger.warning(f"Login attempt for non-existent email: {request.email}")
        return VerifyResponse(valid=False)

    if not user.password_hash:
        # User exists but has no password (maybe OAuth user)
        logger.warning(f"Login attempt for user without password: {request.email}")
        return VerifyResponse(valid=False)

    if user.status != "active":
        logger.warning(f"Login attempt for inactive user: {request.email}")
        return VerifyResponse(valid=False)

    # Verify password
    if not verify_password(request.password, user.password_hash):
        logger.warning(f"Invalid password for user: {request.email}")
        return VerifyResponse(valid=False)

    # Check email verification
    if not user.email_verified:
        logger.warning(f"Login attempt for unverified email: {request.email}")
        return VerifyResponse(valid=False, email=user.email)

    # Get user's project and graph
    try:
        project_id, graph_id = ensure_user_resources(user, db)
    except Exception as e:
        logger.error(f"Failed to get user resources: {e}")
        project_id, graph_id = None, None

    logger.info(f"Successful login for user: {user.email}")

    return VerifyResponse(
        valid=True,
        user_id=str(user.id),
        email=user.email,
        name=user.full_name,
        project_id=project_id,
        graph_id=graph_id,
    )


# =============================================================================
# Email Verification Endpoint
# =============================================================================


class VerifyEmailRequest(BaseModel):
    """Email verification request."""

    token: str


class VerifyEmailResponse(BaseModel):
    """Email verification response."""

    success: bool
    message: str


@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """
    Verify user's email with token from verification link.

    Args:
        token: Verification token from email

    Returns:
        Success message if verified
    """
    # Find user by token
    user = db.query(User).filter(User.email_verification_token == request.token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token"
        )

    # Check if token expired
    if user.email_verification_expires:
        if datetime.datetime.utcnow() > user.email_verification_expires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Verification token has expired"
            )

    # Mark email as verified
    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_expires = None
    db.commit()

    logger.info(f"Email verified for user: {user.email}")

    return VerifyEmailResponse(
        success=True, message="Email verified successfully! You can now sign in."
    )
