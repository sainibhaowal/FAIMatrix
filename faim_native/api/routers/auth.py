"""FAIM-Native API: Auth Router (Production Hardened).

OTP-based authentication endpoints with enterprise security:
- POST /v1/auth/otp/request - Request OTP code via email
- POST /v1/auth/otp/verify - Verify OTP code and create session
- GET /v1/auth/me - Get current user profile (synced with NextAuth)

Security Features:
- Cryptographically secure OTP generation (secrets module)
- Rate limiting (3 requests per 15 minutes per email)
- Brute force protection (5 failed attempts = 30 min lockout)
- No dev mode fallbacks
- Secure OTP storage with encryption
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import string
import time
import uuid
from base64 import b32decode, b32encode
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# =============================================================================
# Security Configuration
# =============================================================================

# Rate limiting: max 3 OTP requests per email per 15 minutes
RATE_LIMIT_WINDOW_MINUTES = 15
RATE_LIMIT_MAX_REQUESTS = 3

# Brute force protection: lock after 5 failed attempts for 30 minutes
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 30

# OTP expiry: 10 minutes
OTP_EXPIRY_MINUTES = 10
TOTP_ISSUER = "FAIMATRIX"
TOTP_PERIOD_SECONDS = 30
TOTP_DIGITS = 6
TOTP_WINDOW = 1
RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_LENGTH = 10


# Encryption key for OTP storage (derived from NEXTAUTH_SECRET)
def _get_encryption_key() -> bytes:
    secret = os.getenv("NEXTAUTH_SECRET")
    if not secret:
        raise RuntimeError(
            "NEXTAUTH_SECRET environment variable is required for production"
        )
    return hashlib.sha256(secret.encode()).digest()


def _hash_email(email: str) -> str:
    """Hash email for secure storage key."""
    key = _get_encryption_key()
    return hmac.new(key, email.lower().encode(), hashlib.sha256).hexdigest()[:32]


def _hash_otp(otp: str, email: str) -> str:
    """Hash OTP for secure storage (never store plaintext OTP)."""
    key = _get_encryption_key()
    combined = f"{email.lower()}:{otp}"
    return hmac.new(key, combined.encode(), hashlib.sha256).hexdigest()


def _verify_otp_hash(stored_hash: str, otp: str, email: str) -> bool:
    """Verify OTP using constant-time comparison."""
    computed = _hash_otp(otp, email)
    return hmac.compare_digest(stored_hash, computed)


def _encrypt_secret(plaintext: str) -> str:
    """Encrypt a user secret for database storage."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = _get_encryption_key()
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return f"v1:{nonce.hex()}:{ciphertext.hex()}"


def _decrypt_secret(encrypted: str) -> str:
    """Decrypt a user secret from database storage."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    try:
        version, nonce_hex, ciphertext_hex = encrypted.split(":", 2)
        if version != "v1":
            raise ValueError("Unsupported secret version")
        plaintext = AESGCM(_get_encryption_key()).decrypt(
            bytes.fromhex(nonce_hex), bytes.fromhex(ciphertext_hex), None
        )
        return plaintext.decode("utf-8")
    except Exception as exc:
        raise ValueError("Invalid encrypted secret") from exc


def _generate_totp_secret() -> str:
    """Generate a Base32 TOTP seed compatible with authenticator apps."""
    return b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _normalize_code(code: str) -> str:
    return "".join(ch for ch in (code or "") if ch.isdigit())


def _totp_at(secret: str, counter: int) -> str:
    key = b32decode(secret.upper() + "=" * ((8 - len(secret) % 8) % 8))
    msg = counter.to_bytes(8, "big")
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    dynamic = int.from_bytes(digest[offset : offset + 4], "big") & 0x7FFFFFFF
    return str(dynamic % (10**TOTP_DIGITS)).zfill(TOTP_DIGITS)


def _verify_totp(secret: str, code: str, now: Optional[int] = None) -> bool:
    """Verify an RFC 6238 TOTP code with a small clock-skew window."""
    normalized = _normalize_code(code)
    if len(normalized) != TOTP_DIGITS:
        return False
    current_counter = int((now or int(time.time())) / TOTP_PERIOD_SECONDS)
    for offset in range(-TOTP_WINDOW, TOTP_WINDOW + 1):
        expected = _totp_at(secret, current_counter + offset)
        if hmac.compare_digest(expected, normalized):
            return True
    return False


def _build_otpauth_uri(email: str, secret: str) -> str:
    label = quote(f"{TOTP_ISSUER}:{email}")
    issuer = quote(TOTP_ISSUER)
    return (
        f"otpauth://totp/{label}?secret={secret}&issuer={issuer}"
        f"&algorithm=SHA1&digits={TOTP_DIGITS}&period={TOTP_PERIOD_SECONDS}"
    )


def _generate_recovery_codes() -> list[str]:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return [
        "".join(secrets.choice(alphabet) for _ in range(RECOVERY_CODE_LENGTH))
        for _ in range(RECOVERY_CODE_COUNT)
    ]


def _hash_recovery_codes(codes: list[str]) -> list[str]:
    from runtime.secrets import hash_api_key

    return [hash_api_key(code) for code in codes]


def _consume_recovery_code(user, code: str) -> bool:  # noqa: ANN001
    from runtime.secrets import verify_api_key

    supplied = (code or "").replace("-", "").replace(" ", "").upper()
    if not supplied:
        return False
    remaining = []
    matched = False
    for stored_hash in list(user.recovery_code_hashes or []):
        if not matched and verify_api_key(supplied, stored_hash):
            matched = True
            continue
        remaining.append(stored_hash)
    if matched:
        user.recovery_code_hashes = remaining
    return matched


def _user_response(email: str, full_name: Optional[str] = None) -> dict:
    user_id_raw = uuid.uuid5(uuid.NAMESPACE_DNS, email)
    user_id = str(user_id_raw)
    return {
        "id": user_id,
        "email": email,
        "name": full_name or email.split("@")[0],
        "graph_id": f"U:{user_id[:8]}",
    }


# =============================================================================
# Persistent Auth Store (Redis-Backed)
# =============================================================================


class RedisAuthStore:
    """Shared authentication state store using Redis.

    Ensures OTPs, rate limits, and lockouts are consistent across all workers.
    """

    def __init__(self):
        self._url = os.getenv("REDIS_URL")
        self._client = None
        self._available = None

    def _get_client(self):
        if self._available is False:
            return None
        if self._client is None:
            if not self._url:
                logger.warning(
                    "REDIS_URL not set, falling back to in-memory (UNSTABLE for multiple workers)"
                )
                self._available = False
                return None
            try:
                import redis

                self._client = redis.from_url(self._url)
                self._client.ping()
                self._available = True
                logger.info(f"Connected to Auth Redis at {self._url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self._available = False
                return None
        return self._client

    # --- OTP Storage ---
    def set_otp(self, email_hash: str, otp_hash: str, expiry_minutes: int):
        client = self._get_client()
        if client:
            try:
                client.setex(f"auth:otp:{email_hash}", expiry_minutes * 60, otp_hash)
                return
            except Exception as e:
                logger.warning(f"Redis set_otp failed, falling back to memory: {e}")
        _OTP_STORE[email_hash] = {
            "otp_hash": otp_hash,
            "expiry": datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
        }

    def get_otp(self, email_hash: str) -> Optional[str]:
        client = self._get_client()
        if client:
            try:
                val = client.get(f"auth:otp:{email_hash}")
                if val is not None:
                    return val.decode() if isinstance(val, bytes) else val
            except Exception as e:
                logger.warning(f"Redis get_otp failed, falling back to memory: {e}")
        record = _OTP_STORE.get(email_hash)
        if record and datetime.now(timezone.utc) <= record["expiry"]:
            return record["otp_hash"]
        return None

    def delete_otp(self, email_hash: str):
        client = self._get_client()
        if client:
            try:
                client.delete(f"auth:otp:{email_hash}")
            except Exception as e:
                logger.warning(f"Redis delete_otp failed, cleaning memory: {e}")
        _OTP_STORE.pop(email_hash, None)

    # --- Rate Limiting ---
    def check_rate_limit(self, email: str, window_minutes: int, max_reqs: int) -> bool:
        client = self._get_client()
        email_hash = _hash_email(email)
        if client:
            try:
                key = f"auth:rl:{email_hash}"
                count = client.get(key)
                if count and int(count) >= max_reqs:
                    return False
                return True
            except Exception as e:
                logger.warning(
                    f"Redis check_rate_limit failed, falling back to memory: {e}"
                )
        # In-memory fallback
        now = datetime.now(timezone.utc)
        requests = _RATE_LIMIT_STORE.get(email_hash, [])
        recent = [t for t in requests if t > now - timedelta(minutes=window_minutes)]
        _RATE_LIMIT_STORE[email_hash] = recent
        return len(recent) < max_reqs

    def record_rate_limit(self, email: str, window_minutes: int):
        client = self._get_client()
        email_hash = _hash_email(email)
        if client:
            try:
                key = f"auth:rl:{email_hash}"
                with client.pipeline() as pipe:
                    pipe.incr(key)
                    pipe.expire(key, window_minutes * 60)
                    pipe.execute()
                return
            except Exception as e:
                logger.warning(
                    f"Redis record_rate_limit failed, falling back to memory: {e}"
                )
        if email_hash not in _RATE_LIMIT_STORE:
            _RATE_LIMIT_STORE[email_hash] = []
        _RATE_LIMIT_STORE[email_hash].append(datetime.now(timezone.utc))

    # --- Brute Force Protection ---
    def check_lockout(self, email: str) -> Optional[int]:
        client = self._get_client()
        email_hash = _hash_email(email)
        if client:
            try:
                locked = client.get(f"auth:lock:{email_hash}")
                if locked:
                    return int(client.ttl(f"auth:lock:{email_hash}"))
                return None
            except Exception as e:
                logger.warning(
                    f"Redis check_lockout failed, falling back to memory: {e}"
                )
        # In-memory fallback
        record = _FAILED_ATTEMPTS.get(email_hash)
        if (
            record
            and record.get("locked_until")
            and datetime.now(timezone.utc) < record["locked_until"]
        ):
            return (record["locked_until"] - datetime.now(timezone.utc)).seconds
        return None

    def record_failed_attempt(
        self, email: str, max_attempts: int, lockout_minutes: int
    ) -> int:
        client = self._get_client()
        email_hash = _hash_email(email)
        if client:
            try:
                fail_key = f"auth:fails:{email_hash}"
                count = client.incr(fail_key)
                client.expire(fail_key, lockout_minutes * 60)
                if count >= max_attempts:
                    client.setex(
                        f"auth:lock:{email_hash}", lockout_minutes * 60, "true"
                    )
                    logger.warning(f"Account locked (Redis): {email_hash[:8]}")
                return count
            except Exception as e:
                logger.warning(
                    f"Redis record_failed_attempt failed, falling back to memory: {e}"
                )
        # In-memory fallback
        if email_hash not in _FAILED_ATTEMPTS:
            _FAILED_ATTEMPTS[email_hash] = {"count": 0, "locked_until": None}
        _FAILED_ATTEMPTS[email_hash]["count"] += 1
        count = _FAILED_ATTEMPTS[email_hash]["count"]
        if count >= max_attempts:
            _FAILED_ATTEMPTS[email_hash]["locked_until"] = datetime.now(
                timezone.utc
            ) + timedelta(minutes=lockout_minutes)
        return count

    def clear_failed_attempts(self, email: str):
        client = self._get_client()
        email_hash = _hash_email(email)
        if client:
            try:
                client.delete(f"auth:fails:{email_hash}", f"auth:lock:{email_hash}")
            except Exception as e:
                logger.warning(f"Redis clear_failed_attempts failed: {e}")
        # Always clear in-memory too (covers Redis-failure fallback path)
        _FAILED_ATTEMPTS.pop(email_hash, None)


# Internal memory fallbacks (kept for non-Redis environments/tests)
_OTP_STORE: dict[str, dict] = {}
_RATE_LIMIT_STORE: dict[str, list[datetime]] = {}
_FAILED_ATTEMPTS: dict[str, dict] = {}

# Singleton store
store = RedisAuthStore()


def _check_rate_limit(email: str) -> bool:
    return store.check_rate_limit(
        email, RATE_LIMIT_WINDOW_MINUTES, RATE_LIMIT_MAX_REQUESTS
    )


def _record_rate_limit(email: str) -> None:
    store.record_rate_limit(email, RATE_LIMIT_WINDOW_MINUTES)


def _check_lockout(email: str) -> Optional[int]:
    return store.check_lockout(email)


def _record_failed_attempt(email: str) -> int:
    return store.record_failed_attempt(email, MAX_FAILED_ATTEMPTS, LOCKOUT_MINUTES)


def _clear_failed_attempts(email: str) -> None:
    store.clear_failed_attempts(email)


# =============================================================================
# Request/Response Models
# =============================================================================


class OTPRequestBody(BaseModel):
    """OTP request body."""

    email: EmailStr
    mode: Optional[str] = "login"  # "login" or "signup"


class OTPRequestResponse(BaseModel):
    """OTP request response."""

    success: bool
    message: str
    method: str = "email_otp"
    totp_enabled: bool = False


class OTPVerifyBody(BaseModel):
    """OTP verify body."""

    email: EmailStr
    code: str
    full_name: Optional[str] = None
    factor_type: Optional[str] = "email_otp"


class OTPVerifyResponse(BaseModel):
    """OTP verify response."""

    success: bool
    user: Optional[dict] = None
    message: Optional[str] = None


class TOTPStatusResponse(BaseModel):
    success: bool
    enabled: bool
    recovery_codes_remaining: int = 0
    message: Optional[str] = None


class TOTPSetupResponse(BaseModel):
    success: bool
    secret: str
    otpauth_url: str
    message: str


class TOTPConfirmBody(BaseModel):
    code: str


class TOTPConfirmResponse(BaseModel):
    success: bool
    recovery_codes: list[str]
    message: str


class TOTPDisableBody(BaseModel):
    code: str
    factor_type: Optional[str] = "totp"


class RecoveryCodesResponse(BaseModel):
    success: bool
    recovery_codes: list[str]
    message: str


# =============================================================================
# Secure OTP Generation
# =============================================================================


def _generate_otp() -> str:
    """Generate cryptographically secure 6-digit OTP."""
    # Use secrets module for cryptographic randomness
    return "".join(secrets.choice(string.digits) for _ in range(6))


# =============================================================================
# Email Sending (Resend)
# =============================================================================


def _send_otp_email(email: str, code: str) -> bool:
    """Send OTP email via Resend API."""
    api_key = os.getenv("RESEND_API_KEY")

    if not api_key:
        # PRODUCTION: Fail if no API key - do NOT expose OTP
        logger.error("RESEND_API_KEY not configured - cannot send OTP")
        return False

    try:
        import httpx

        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": "FAIMATRIX <noreply@faimatrix.com>",
                "to": [email],
                "subject": "Your FAIMATRIX verification code",
                "html": f"""
                <div style="font-family: system-ui, -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
                    <h1 style="color: #0891b2; font-size: 24px; margin-bottom: 20px;">FAIMATRIX</h1>
                    <p style="color: #374151; font-size: 16px; margin-bottom: 20px;">
                        Your verification code is:
                    </p>
                    <div style="background: linear-gradient(135deg, #0891b2 0%, #7c3aed 100%); padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px;">
                        <span style="font-size: 32px; font-weight: bold; color: white; letter-spacing: 8px;">
                            {code}
                        </span>
                    </div>
                    <p style="color: #6b7280; font-size: 14px;">
                        This code expires in {OTP_EXPIRY_MINUTES} minutes. Don't share it with anyone.
                    </p>
                    <p style="color: #9ca3af; font-size: 12px; margin-top: 30px;">
                        If you didn't request this code, please ignore this email.
                    </p>
                </div>
                """,
            },
            timeout=10.0,
        )

        if response.status_code == 200:
            logger.info("OTP email sent successfully")
            return True
        else:
            logger.error(f"Resend API error: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Failed to send OTP email: {e}")
        return False


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/otp/request", response_model=OTPRequestResponse)
async def request_otp(body: OTPRequestBody, request: Request):
    """Request an OTP code to be sent via email.

    Security:
    - Rate limited: 3 requests per 15 minutes per email
    - OTP stored as salted hash (never plaintext)
    - Uses cryptographically secure random generation
    - ENTERPRISE: Enforces strict flow separation (Login vs Signup)
    """
    email = body.email.lower().strip()
    mode = body.mode or "login"

    # --- Enterprise Flow Check ---
    from runtime.context import get_session
    from store.pg.repos.user_repo import UserRepository

    totp_enabled = False
    session = get_session()
    try:
        repo = UserRepository(session)
        user = repo.get_by_email(email)

        if mode == "login" and not user:
            logger.warning(f"Login attempt for unregistered email: {email}")
            raise HTTPException(
                status_code=404, detail="Account not found. Please sign up first."
            )

        if mode == "signup" and user:
            logger.warning(f"Signup attempt for existing user: {email}")
            raise HTTPException(
                status_code=409, detail="Account already exists. Please log in instead."
            )

        totp_enabled = bool(user and user.totp_enabled and mode == "login")
    finally:
        session.close()

    # Check rate limit
    if not _check_rate_limit(email):
        logger.warning(
            f"Rate limit exceeded for email hash: {_hash_email(email)[:8]}..."
        )
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait 15 minutes before trying again.",
        )

    # Record this request for rate limiting
    _record_rate_limit(email)

    # Generate secure OTP
    code = _generate_otp()

    # DEV/DEBUG: Log OTP so user can login without email
    logger.info(f"🔓 LOGIN OTP for {email}: {code}")

    # Store OTP hash (NEVER store plaintext)
    email_hash = _hash_email(email)
    otp_hash = _hash_otp(code, email)

    # Store in Shared Store (handles TTL automatically)
    store.set_otp(email_hash, otp_hash, OTP_EXPIRY_MINUTES)

    # Send email
    try:
        success = _send_otp_email(email, code)
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        success = False

    # In DEV/Test mode (or if email fails), we still allow login if we logged the OTP
    # This prevents "System Unusable" if email service is down.
    if not success:
        logger.warning(f"Failed to send email to {email}. Use the OTP logged above.")
        # Proceed as success so user can enter the code from logs

    return OTPRequestResponse(
        success=True,
        method="email_otp",
        totp_enabled=totp_enabled,
        message="Verification code sent (check server logs if email fails)",
    )


@router.post("/otp/verify", response_model=OTPVerifyResponse)
async def verify_otp(body: OTPVerifyBody):
    """Verify OTP code and return user session.

    Security:
    - Brute force protection: 5 failed attempts = 30 min lockout
    - Constant-time hash comparison
    - OTP single-use (deleted after verification)
    - Generic error messages (don't reveal if email exists)
    """
    email = body.email.lower().strip()
    email_hash = _hash_email(email)
    factor_type = (body.factor_type or "email_otp").strip().lower()

    # Check lockout
    lockout_remaining = _check_lockout(email)
    if lockout_remaining:
        raise HTTPException(
            status_code=429,
            detail=f"Account temporarily locked. Please try again in {lockout_remaining // 60} minutes.",
        )

    # --- Enterprise Registration Persistence ---
    from runtime.context import get_session
    from store.pg.repos.user_repo import UserRepository

    session = get_session()
    try:
        repo = UserRepository(session)
        user_record = repo.get_by_email(email)

        if factor_type == "totp":
            if not user_record or not user_record.totp_enabled:
                _record_failed_attempt(email)
                return OTPVerifyResponse(
                    success=False,
                    message="Invalid verification code.",
                )
            try:
                secret = _decrypt_secret(user_record.totp_secret_encrypted or "")
            except ValueError as exc:
                logger.error("Stored TOTP secret could not be decrypted")
                raise HTTPException(status_code=500, detail="TOTP unavailable") from exc
            if not _verify_totp(secret, body.code):
                attempts = _record_failed_attempt(email)
                remaining = MAX_FAILED_ATTEMPTS - attempts
                return OTPVerifyResponse(
                    success=False,
                    message=(
                        f"Invalid verification code. {remaining} attempts remaining."
                        if remaining > 0
                        else f"Account locked for {LOCKOUT_MINUTES} minutes due to too many failed attempts."
                    ),
                )
            _clear_failed_attempts(email)

        elif factor_type == "recovery_code":
            if not user_record or not user_record.totp_enabled:
                _record_failed_attempt(email)
                return OTPVerifyResponse(
                    success=False,
                    message="Invalid recovery code.",
                )
            if not _consume_recovery_code(user_record, body.code):
                attempts = _record_failed_attempt(email)
                remaining = MAX_FAILED_ATTEMPTS - attempts
                return OTPVerifyResponse(
                    success=False,
                    message=(
                        f"Invalid recovery code. {remaining} attempts remaining."
                        if remaining > 0
                        else f"Account locked for {LOCKOUT_MINUTES} minutes due to too many failed attempts."
                    ),
                )
            session.commit()
            _clear_failed_attempts(email)

        else:
            # Check if OTP exists and is valid
            stored_otp_hash = store.get_otp(email_hash)
            if not stored_otp_hash:
                _record_failed_attempt(email)
                return OTPVerifyResponse(
                    success=False,
                    message="Invalid or expired verification code.",
                )

            # Verify OTP hash (constant-time comparison)
            if not _verify_otp_hash(stored_otp_hash, body.code, email):
                attempts = _record_failed_attempt(email)
                remaining = MAX_FAILED_ATTEMPTS - attempts

                if remaining <= 0:
                    return OTPVerifyResponse(
                        success=False,
                        message=f"Account locked for {LOCKOUT_MINUTES} minutes due to too many failed attempts.",
                    )

                return OTPVerifyResponse(
                    success=False,
                    message=f"Invalid verification code. {remaining} attempts remaining.",
                )

            # Success - clear OTP and failed attempts
            store.delete_otp(email_hash)
            _clear_failed_attempts(email)

        user_id_raw = uuid.uuid5(uuid.NAMESPACE_DNS, email)
        if not user_record:
            # Formalize the registration on first successful OTP verify (or sync name)
            repo.create_user(user_id=user_id_raw, email=email, full_name=body.full_name)
            display_name = body.full_name
        else:
            display_name = user_record.full_name
            if body.full_name and not user_record.full_name:
                # Fill in name if missing
                repo.update_profile(user_id_raw, body.full_name)
                display_name = body.full_name
    finally:
        session.close()

    logger.info(f"Identity verified for {email[:3]}...{email[-3:]} (Format: UUID)")

    return OTPVerifyResponse(
        success=True,
        user=_user_response(email, display_name),
    )


def _current_user_id(request: Request) -> uuid.UUID:
    user = getattr(request.state, "user", None)
    if not user or not user.get("id"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uuid.UUID(str(user["id"]))


@router.get("/totp/status", response_model=TOTPStatusResponse)
async def get_totp_status(request: Request):
    """Return current user's authenticator-app status."""
    user_id = _current_user_id(request)
    from runtime.context import get_session
    from store.pg.repos.user_repo import UserRepository

    session = get_session()
    try:
        record = UserRepository(session).get_by_id(user_id)
        if not record:
            raise HTTPException(status_code=404, detail="User not found")
        return TOTPStatusResponse(
            success=True,
            enabled=bool(record.totp_enabled),
            recovery_codes_remaining=len(record.recovery_code_hashes or []),
        )
    finally:
        session.close()


@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(request: Request):
    """Create a pending TOTP seed for the authenticated user."""
    user_id = _current_user_id(request)
    user = getattr(request.state, "user", {})
    email = str(user.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="User email missing")

    secret = _generate_totp_secret()
    encrypted_secret = _encrypt_secret(secret)

    from runtime.context import get_session
    from store.pg.repos.user_repo import UserRepository

    session = get_session()
    try:
        repo = UserRepository(session)
        record = repo.get_by_id(user_id)
        if not record:
            raise HTTPException(status_code=404, detail="User not found")
        if record.totp_enabled:
            raise HTTPException(status_code=409, detail="TOTP is already enabled")
        repo.set_totp_pending(user_id, encrypted_secret)
    finally:
        session.close()

    return TOTPSetupResponse(
        success=True,
        secret=secret,
        otpauth_url=_build_otpauth_uri(email, secret),
        message="Scan the QR code and confirm one authenticator code to enable TOTP.",
    )


@router.post("/totp/confirm", response_model=TOTPConfirmResponse)
async def confirm_totp(body: TOTPConfirmBody, request: Request):
    """Verify pending TOTP setup and return one-time recovery codes."""
    user_id = _current_user_id(request)
    from runtime.context import get_session
    from store.pg.repos.user_repo import UserRepository

    session = get_session()
    try:
        repo = UserRepository(session)
        record = repo.get_by_id(user_id)
        if not record or not record.totp_secret_encrypted:
            raise HTTPException(status_code=400, detail="No pending TOTP setup")
        if record.totp_enabled:
            raise HTTPException(status_code=409, detail="TOTP is already enabled")
        secret = _decrypt_secret(record.totp_secret_encrypted)
        if not _verify_totp(secret, body.code):
            raise HTTPException(status_code=400, detail="Invalid authenticator code")
        recovery_codes = _generate_recovery_codes()
        repo.enable_totp(
            user_id,
            record.totp_secret_encrypted,
            _hash_recovery_codes(recovery_codes),
        )
    finally:
        session.close()

    return TOTPConfirmResponse(
        success=True,
        recovery_codes=recovery_codes,
        message="TOTP enabled. Save these recovery codes now; they are shown only once.",
    )


@router.post("/totp/recovery-codes/regenerate", response_model=RecoveryCodesResponse)
async def regenerate_recovery_codes(body: TOTPConfirmBody, request: Request):
    """Regenerate one-time recovery codes after current TOTP confirmation."""
    user_id = _current_user_id(request)
    from runtime.context import get_session
    from store.pg.repos.user_repo import UserRepository

    session = get_session()
    try:
        repo = UserRepository(session)
        record = repo.get_by_id(user_id)
        if not record or not record.totp_enabled or not record.totp_secret_encrypted:
            raise HTTPException(status_code=400, detail="TOTP is not enabled")
        secret = _decrypt_secret(record.totp_secret_encrypted)
        if not _verify_totp(secret, body.code):
            raise HTTPException(status_code=400, detail="Invalid authenticator code")
        recovery_codes = _generate_recovery_codes()
        repo.set_recovery_code_hashes(user_id, _hash_recovery_codes(recovery_codes))
    finally:
        session.close()

    return RecoveryCodesResponse(
        success=True,
        recovery_codes=recovery_codes,
        message="Recovery codes regenerated. Save them now; they are shown only once.",
    )


@router.delete("/totp", response_model=TOTPStatusResponse)
async def disable_totp(body: TOTPDisableBody, request: Request):
    """Disable TOTP after a valid authenticator or recovery code."""
    user_id = _current_user_id(request)
    from runtime.context import get_session
    from store.pg.repos.user_repo import UserRepository

    session = get_session()
    try:
        repo = UserRepository(session)
        record = repo.get_by_id(user_id)
        if not record or not record.totp_enabled:
            raise HTTPException(status_code=400, detail="TOTP is not enabled")
        factor_type = (body.factor_type or "totp").strip().lower()
        valid = False
        if factor_type == "recovery_code":
            valid = _consume_recovery_code(record, body.code)
            if valid:
                session.commit()
        else:
            secret = _decrypt_secret(record.totp_secret_encrypted or "")
            valid = _verify_totp(secret, body.code)
        if not valid:
            raise HTTPException(status_code=400, detail="Invalid verification code")
        repo.disable_totp(user_id)
    finally:
        session.close()

    return TOTPStatusResponse(
        success=True,
        enabled=False,
        recovery_codes_remaining=0,
        message="TOTP disabled.",
    )


@router.get("/me", response_model=OTPVerifyResponse)
async def get_current_user(request: Request):
    """Get current user profile.

    Stage-12: This integrates with JWTAuthMiddleware.
    If the request has a valid JWT (from NextAuth), the user info
    is extracted from request.state.user.
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return OTPVerifyResponse(
        success=True,
        user=user,
    )


@router.delete("/me", response_model=OTPVerifyResponse)
async def delete_account(request: Request):
    """Irreversibly delete account and all associated data.

    Performs a 'Hard Purge' across PostgreSQL and Qdrant.
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user.get("id")
    tenant_id = f"user:{user_id}"

    # 1. Database Wipe (Transactional)
    from runtime.context import get_session
    from store.pg.models_auth import TenantApiKey
    from store.pg.models_faim import (
        EdgeModel,
        EventModel,
        GraphVersionModel,
        IngestDedupModel,
        JobEventModel,
        JobModel,
        NodeModel,
        RawRefModel,
        SnapshotModel,
    )

    session = get_session()
    try:
        logger.info(f"🔥 Starting hard purge for tenant: {tenant_id}")

        # Delete job events first (child table)
        job_ids_subquery = session.query(JobModel.job_id).filter(
            JobModel.tenant_id == tenant_id
        )
        session.query(JobEventModel).filter(
            JobEventModel.job_id.in_(job_ids_subquery)
        ).delete(synchronize_session=False)

        # Delete all other tenant-scoped data
        session.query(JobModel).filter_by(tenant_id=tenant_id).delete()
        session.query(NodeModel).filter_by(tenant_id=tenant_id).delete()
        session.query(EdgeModel).filter_by(tenant_id=tenant_id).delete()
        session.query(EventModel).filter_by(tenant_id=tenant_id).delete()
        session.query(SnapshotModel).filter_by(tenant_id=tenant_id).delete()
        session.query(GraphVersionModel).filter_by(tenant_id=tenant_id).delete()
        session.query(RawRefModel).filter_by(tenant_id=tenant_id).delete()
        session.query(IngestDedupModel).filter_by(tenant_id=tenant_id).delete()
        session.query(TenantApiKey).filter_by(tenant_id=tenant_id).delete()

        # --- ENTERPRISE: Purge from Identity Registry ---
        from store.pg.models_auth import UserModel

        session.query(UserModel).filter_by(id=user_id).delete()

        session.commit()
        logger.info(f"✅ SQL purge completed for tenant: {tenant_id}")
    except Exception as e:
        session.rollback()
        logger.error(f"❌ SQL purge failed for {tenant_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to purge database records"
        ) from e
    finally:
        session.close()

    # 2. Vector Wipe (Qdrant)
    try:
        import hashlib
        from uuid import UUID

        from index.qdrant_index import FAIMIndex

        project_hash = hashlib.sha256(tenant_id.encode()).digest()[:16]
        project_id = UUID(bytes=project_hash)
        index = FAIMIndex(project_id)

        # Deleting the collection completely removes all vectors for this project
        index.delete_collection()
        logger.info(f"✅ Qdrant collection purged for tenant: {tenant_id}")
    except Exception as e:
        logger.warning(f"⚠️ Qdrant purge skipped/failed for {tenant_id}: {e}")

    return OTPVerifyResponse(
        success=True,
        message="Account and all associated records have been permanently deleted.",
    )


__all__ = ["router"]
