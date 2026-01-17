"""
FAIM-Native Envelope Encryption (Stage-11).

Provides AES-256-GCM envelope encryption for raw files.

Architecture:
- Master Key: Stored in environment (FAIM_MASTER_KEY) or derived
- Data Encryption Keys (DEKs): Per-tenant, wrapped by master key
- Raw files encrypted with tenant DEK

Security:
- AES-256-GCM for authenticated encryption
- Unique nonce per encryption
- DEKs wrapped with master key for key rotation
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from dataclasses import dataclass
from typing import Tuple, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# =============================================================================
# Constants
# =============================================================================

KEY_SIZE = 32  # 256 bits
NONCE_SIZE = 12  # 96 bits (GCM standard)
TAG_SIZE = 16  # 128 bits (GCM standard)

# Environment variable for master key
MASTER_KEY_ENV = "FAIM_MASTER_KEY"
MASTER_KEY_SALT_ENV = "FAIM_MASTER_SALT"


# =============================================================================
# Encrypted Blob Format
# =============================================================================

@dataclass
class EncryptedBlob:
    """
    Container for encrypted data.
    
    Format: version (1 byte) + nonce (12 bytes) + ciphertext + tag (16 bytes)
    
    Attributes:
        version: Encryption version (for future algorithm changes).
        nonce: Unique nonce for this encryption.
        ciphertext: Encrypted data (includes GCM tag at end).
    """
    version: int
    nonce: bytes
    ciphertext: bytes
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes for storage."""
        return bytes([self.version]) + self.nonce + self.ciphertext
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "EncryptedBlob":
        """Deserialize from bytes."""
        if len(data) < 1 + NONCE_SIZE + TAG_SIZE:
            raise ValueError("Invalid encrypted blob: too short")
        
        version = data[0]
        nonce = data[1:1 + NONCE_SIZE]
        ciphertext = data[1 + NONCE_SIZE:]
        
        return cls(version=version, nonce=nonce, ciphertext=ciphertext)


# =============================================================================
# Key Derivation
# =============================================================================

def derive_master_key(password: str, salt: bytes) -> bytes:
    """
    Derive master key from password using PBKDF2.
    
    Used when FAIM_MASTER_KEY is not provided directly.
    
    Args:
        password: The master password.
        salt: Random salt (store with the database).
        
    Returns:
        32-byte master key.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=100_000,
    )
    return kdf.derive(password.encode())


def get_master_key() -> bytes:
    """
    Get the master key from environment.
    
    Prefers FAIM_MASTER_KEY as hex-encoded key.
    Falls back to PBKDF2 derivation if salt is provided.
    
    Returns:
        32-byte master key.
        
    Raises:
        ValueError: If master key is not configured.
    """
    # Prefer direct key
    key_hex = os.getenv(MASTER_KEY_ENV)
    if key_hex:
        key = bytes.fromhex(key_hex)
        if len(key) == KEY_SIZE:
            return key
        raise ValueError(f"FAIM_MASTER_KEY must be {KEY_SIZE * 2} hex chars")
    
    # Fall back to derivation (for development)
    password = os.getenv("FAIM_MASTER_PASSWORD")
    salt_hex = os.getenv(MASTER_KEY_SALT_ENV)
    
    if password and salt_hex:
        salt = bytes.fromhex(salt_hex)
        return derive_master_key(password, salt)
    
    raise ValueError(
        f"Encryption requires {MASTER_KEY_ENV} or "
        f"FAIM_MASTER_PASSWORD + {MASTER_KEY_SALT_ENV}"
    )


# =============================================================================
# Data Encryption Key Management
# =============================================================================

def generate_dek() -> bytes:
    """Generate a new Data Encryption Key."""
    return secrets.token_bytes(KEY_SIZE)


def wrap_dek(dek: bytes, master_key: bytes) -> bytes:
    """
    Wrap (encrypt) a DEK with the master key.
    
    Args:
        dek: The data encryption key to wrap.
        master_key: The master key.
        
    Returns:
        Wrapped DEK (nonce + ciphertext).
    """
    aesgcm = AESGCM(master_key)
    nonce = secrets.token_bytes(NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, dek, None)
    return nonce + ciphertext


def unwrap_dek(wrapped_dek: bytes, master_key: bytes) -> bytes:
    """
    Unwrap (decrypt) a DEK with the master key.
    
    Args:
        wrapped_dek: The wrapped DEK (nonce + ciphertext).
        master_key: The master key.
        
    Returns:
        The unwrapped DEK.
    """
    if len(wrapped_dek) < NONCE_SIZE + TAG_SIZE:
        raise ValueError("Invalid wrapped DEK")
    
    nonce = wrapped_dek[:NONCE_SIZE]
    ciphertext = wrapped_dek[NONCE_SIZE:]
    
    aesgcm = AESGCM(master_key)
    return aesgcm.decrypt(nonce, ciphertext, None)


# =============================================================================
# Encryption/Decryption
# =============================================================================

def encrypt(plaintext: bytes, key: bytes) -> EncryptedBlob:
    """
    Encrypt data using AES-256-GCM.
    
    Args:
        plaintext: Data to encrypt.
        key: 32-byte encryption key.
        
    Returns:
        EncryptedBlob containing the encrypted data.
    """
    if len(key) != KEY_SIZE:
        raise ValueError(f"Key must be {KEY_SIZE} bytes")
    
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    
    return EncryptedBlob(version=1, nonce=nonce, ciphertext=ciphertext)


def decrypt(blob: EncryptedBlob, key: bytes) -> bytes:
    """
    Decrypt data using AES-256-GCM.
    
    Args:
        blob: EncryptedBlob to decrypt.
        key: 32-byte encryption key.
        
    Returns:
        Decrypted plaintext.
        
    Raises:
        InvalidTag: If authentication fails (tampered data).
    """
    if len(key) != KEY_SIZE:
        raise ValueError(f"Key must be {KEY_SIZE} bytes")
    
    if blob.version != 1:
        raise ValueError(f"Unsupported encryption version: {blob.version}")
    
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(blob.nonce, blob.ciphertext, None)


# =============================================================================
# Convenience Functions
# =============================================================================

def encrypt_for_storage(plaintext: bytes, key: bytes) -> bytes:
    """
    Encrypt and serialize for database storage.
    
    Args:
        plaintext: Data to encrypt.
        key: 32-byte encryption key.
        
    Returns:
        Serialized encrypted blob.
    """
    blob = encrypt(plaintext, key)
    return blob.to_bytes()


def decrypt_from_storage(data: bytes, key: bytes) -> bytes:
    """
    Deserialize and decrypt from database storage.
    
    Args:
        data: Serialized encrypted blob.
        key: 32-byte encryption key.
        
    Returns:
        Decrypted plaintext.
    """
    blob = EncryptedBlob.from_bytes(data)
    return decrypt(blob, key)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "EncryptedBlob",
    "generate_dek",
    "wrap_dek",
    "unwrap_dek",
    "encrypt",
    "decrypt",
    "encrypt_for_storage",
    "decrypt_from_storage",
    "get_master_key",
    "derive_master_key",
]
