# =============================================================================
# FAIM OTP Authentication - Cryptographically Secure
# =============================================================================
# File: faim/api/auth/otp.py
#
# Security Features:
# - OTP generated with secrets.randbelow (CSPRNG)
# - OTP stored as SHA256 hash (never plaintext)
# - Constant-time comparison for verification
# - Rate limiting: 3 requests per email per 15 minutes
# - Max 3 verification attempts per OTP
# - 5-minute expiration
# =============================================================================

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from faim.config.models import GraphOwnership, OTPCode, User

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

OTP_EXPIRY_SECONDS = 300  # 5 minutes
MAX_VERIFICATION_ATTEMPTS = 3
RATE_LIMIT_WINDOW_SECONDS = 900  # 15 minutes
RATE_LIMIT_MAX_REQUESTS = 3


# =============================================================================
# OTP Generation
# =============================================================================


def generate_otp() -> Tuple[str, str]:
    """
    Generate a cryptographically secure 6-digit OTP.

    Returns:
        Tuple of (plaintext_code, sha256_hash)

    Security:
        - Uses secrets.randbelow() which is backed by os.urandom()
        - CSPRNG (Cryptographically Secure Pseudo-Random Number Generator)
    """
    # Generate 6-digit code (000000 to 999999)
    code = f"{secrets.randbelow(1_000_000):06d}"
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    return code, code_hash


def hash_otp(code: str) -> str:
    """Hash an OTP code using SHA256."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def verify_otp_hash(code: str, stored_hash: str) -> bool:
    """
    Verify OTP using constant-time comparison.

    Security:
        - Uses secrets.compare_digest() for timing-attack resistance
    """
    computed_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    return secrets.compare_digest(computed_hash, stored_hash)


# =============================================================================
# Rate Limiting
# =============================================================================


def check_rate_limit(db: Session, email: str) -> Tuple[bool, int]:
    """
    Check if email has exceeded rate limit for OTP requests.

    Returns:
        Tuple of (is_allowed, seconds_until_reset)
    """
    window_start = datetime.utcnow() - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)

    # Count recent OTP requests for this email
    recent_count = (
        db.query(OTPCode).filter(OTPCode.email == email.lower()).filter(OTPCode.created_at >= window_start).count()
    )

    if recent_count >= RATE_LIMIT_MAX_REQUESTS:
        # Find oldest request in window to calculate reset time
        oldest = (
            db.query(OTPCode)
            .filter(OTPCode.email == email.lower())
            .filter(OTPCode.created_at >= window_start)
            .order_by(OTPCode.created_at.asc())
            .first()
        )
        if oldest:
            reset_at = oldest.created_at + timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
            seconds_until_reset = int((reset_at - datetime.utcnow()).total_seconds())
            return False, max(0, seconds_until_reset)
        return False, RATE_LIMIT_WINDOW_SECONDS

    return True, 0


# =============================================================================
# OTP Creation
# =============================================================================


def create_otp(db: Session, email: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Create a new OTP for the given email.

    Returns:
        Tuple of (plaintext_code, error_message)
        If successful: (code, None)
        If rate limited: (None, error_message)
    """
    email = email.lower().strip()

    # Check rate limit
    is_allowed, seconds_until_reset = check_rate_limit(db, email)
    if not is_allowed:
        minutes = (seconds_until_reset // 60) + 1
        return None, f"Too many requests. Try again in {minutes} minute(s)."

    # Invalidate any existing unused OTPs for this email
    db.query(OTPCode).filter(
        OTPCode.email == email,
        OTPCode.used_at.is_(None),
    ).update({"used_at": datetime.utcnow()})

    # Generate new OTP
    code, code_hash = generate_otp()
    expires_at = datetime.utcnow() + timedelta(seconds=OTP_EXPIRY_SECONDS)

    otp_record = OTPCode(
        email=email,
        code_hash=code_hash,
        expires_at=expires_at,
    )
    db.add(otp_record)
    db.commit()

    logger.info(f"OTP created for {email}, expires at {expires_at}")
    return code, None


# =============================================================================
# OTP Verification
# =============================================================================


def verify_otp(db: Session, email: str, code: str) -> Tuple[bool, Optional[str], Optional[User]]:
    """
    Verify an OTP code.

    Returns:
        Tuple of (success, error_message, user)
        If successful: (True, None, user)
        If failed: (False, error_message, None)
    """
    email = email.lower().strip()
    code = code.strip()

    # Validate code format
    if not code.isdigit() or len(code) != 6:
        return False, "Invalid code format", None

    # Find the most recent unused OTP for this email
    otp_record = (
        db.query(OTPCode)
        .filter(OTPCode.email == email)
        .filter(OTPCode.used_at.is_(None))
        .order_by(OTPCode.created_at.desc())
        .first()
    )

    if not otp_record:
        return False, "No pending verification. Please request a new code.", None

    # Check expiration
    if datetime.utcnow() > otp_record.expires_at:
        otp_record.used_at = datetime.utcnow()  # Mark as used (expired)
        db.commit()
        return False, "Code expired. Please request a new code.", None

    # Check attempts
    if otp_record.attempts >= MAX_VERIFICATION_ATTEMPTS:
        otp_record.used_at = datetime.utcnow()  # Mark as used (locked out)
        db.commit()
        return False, "Too many attempts. Please request a new code.", None

    # Increment attempts
    otp_record.attempts += 1
    db.commit()

    # Verify code (constant-time comparison)
    if not verify_otp_hash(code, otp_record.code_hash):
        remaining = MAX_VERIFICATION_ATTEMPTS - otp_record.attempts
        if remaining > 0:
            return False, f"Invalid code. {remaining} attempt(s) remaining.", None
        else:
            otp_record.used_at = datetime.utcnow()
            db.commit()
            return False, "Too many attempts. Please request a new code.", None

    # Success! Mark OTP as used
    otp_record.used_at = datetime.utcnow()
    db.commit()

    # Get or create user
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Create new user (JIT provisioning)
        import uuid

        user = User(
            keycloak_sub=str(uuid.uuid4()),  # Legacy field, use UUID
            email=email,
            full_name=email.split("@")[0].title(),
            email_verified=True,  # Verified by OTP
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created new user via OTP: {email}")

    # Mark email as verified if not already
    if not user.email_verified:
        user.email_verified = True
        db.commit()

    # Ensure user has a graph
    graph = db.query(GraphOwnership).filter(GraphOwnership.user_id == user.id).first()
    if not graph:
        import uuid

        graph_id = f"U:{uuid.uuid4().hex[:8]}"
        graph = GraphOwnership(
            graph_id=graph_id,
            user_id=user.id,
            name="My Universe",
        )
        db.add(graph)
        db.commit()
        logger.info(f"Created graph {graph_id} for user {user.id}")

    logger.info(f"OTP verified successfully for {email}")
    return True, None, user


# =============================================================================
# Cleanup (Optional - for maintenance)
# =============================================================================


def cleanup_expired_otps(db: Session) -> int:
    """
    Delete expired OTP records older than 24 hours.

    Returns:
        Number of deleted records
    """
    cutoff = datetime.utcnow() - timedelta(hours=24)

    deleted = db.query(OTPCode).filter(OTPCode.created_at < cutoff).delete()
    db.commit()

    if deleted > 0:
        logger.info(f"Cleaned up {deleted} expired OTP records")

    return deleted
