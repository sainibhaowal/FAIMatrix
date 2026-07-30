"""
FAIM-Native Secrets Management.

Stage-11: Security Hardening - API Key Hashing.

This module provides secure handling of API keys using Argon2id,
the winner of the Password Hashing Competition (PHC).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Tuple

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerifyMismatchError

# Argon2id configuration (OWASP recommended)
# https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
_hasher = PasswordHasher(
    time_cost=3,  # Iterations
    memory_cost=65536,  # 64 MB
    parallelism=4,  # Threads
    hash_len=32,  # Output length
    salt_len=16,  # Salt length
    type=Type.ID,  # Argon2id (hybrid)
)


def generate_api_key(prefix: str = "faim") -> Tuple[str, str]:
    """
    Generate a new API key with a prefix.

    Returns:
        Tuple of (key_id, full_key)
        - key_id: Short identifier for display/revocation (e.g., "faim_abc123")
        - full_key: Full key to give to user (e.g., "faim_abc123_Ks8j2mN...")

    Example:
        >>> key_id, full_key = generate_api_key("tenant")
        >>> print(key_id)  # "tenant_abc123"
        >>> print(full_key)  # "tenant_abc123_Ks8j2mN4p..."
    """
    # Generate random components
    short_id = secrets.token_hex(3)  # 6 chars
    secret_part = secrets.token_urlsafe(24)  # 32 chars

    key_id = f"{prefix}_{short_id}"
    full_key = f"{key_id}_{secret_part}"

    return key_id, full_key


def get_key_prefix(full_key: str) -> str:
    """
    Extract the displayable prefix from a full key.

    Used for UI display without exposing the secret part.

    Example:
        >>> get_key_prefix("faim_abc123_Ks8j2mN...")
        "faim_abc123"
    """
    parts = full_key.split("_")
    if len(parts) >= 2:
        return f"{parts[0]}_{parts[1]}"
    return full_key[:12]  # Fallback: first 12 chars


def hash_api_key(key: str) -> str:
    """
    Hash an API key using Argon2id.

    This is the primary method for storing API keys securely.
    The hash includes a random salt and can be verified later.

    Args:
        key: The plaintext API key to hash.

    Returns:
        Argon2id hash string (includes algorithm, params, salt, hash).

    Example:
        >>> h = hash_api_key("faim_abc123_secret")
        >>> h.startswith("$argon2id$")
        True
    """
    return _hasher.hash(key)


def verify_api_key(key: str, stored_hash: str) -> bool:
    """
    Verify an API key against a stored hash (constant-time).

    Args:
        key: The plaintext API key from the request.
        stored_hash: The Argon2id hash from the database.

    Returns:
        True if the key matches, False otherwise.

    Note:
        This function is designed to be constant-time to prevent
        timing attacks. Argon2id verification is inherently constant-time.
    """
    try:
        _hasher.verify(stored_hash, key)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    """
    Check if a hash needs to be rehashed (params changed).

    Useful for key rotation when security parameters are updated.

    Args:
        stored_hash: The existing Argon2id hash.

    Returns:
        True if the hash should be regenerated with new params.
    """
    return _hasher.check_needs_rehash(stored_hash)


# --- Legacy Support (for migration from TENANT_KEYS_JSON) ---


def constant_time_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison.

    Used for legacy plaintext key comparison during migration period.
    After migration, use verify_api_key() instead.

    Args:
        a: First string.
        b: Second string.

    Returns:
        True if strings are equal.
    """
    return hmac.compare_digest(a.encode(), b.encode())


def quick_hash(key: str) -> str:
    """
    Quick SHA256 hash for indexing/lookup (NOT for security).

    Used to find candidate rows in the database before Argon2 verification.
    This is NOT a substitute for proper password hashing.

    Args:
        key: The API key to hash.

    Returns:
        Hex digest of SHA256 hash.
    """
    return hashlib.sha256(key.encode()).hexdigest()
