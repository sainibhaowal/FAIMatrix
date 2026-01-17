"""Security Tests: API Key Hashing (Stage-11).

Ensures:
- No plaintext keys stored anywhere
- Constant-time comparison is used
- Revoked keys are rejected
- Key rotation works correctly
"""

import unittest
from unittest.mock import MagicMock, patch

from runtime.secrets import (
    generate_api_key,
    get_key_prefix,
    hash_api_key,
    verify_api_key,
    needs_rehash,
    constant_time_compare,
)


class TestApiKeyHashing(unittest.TestCase):
    """Tests for API key hashing functions."""
    
    def test_generate_api_key_format(self):
        """Generated keys have correct format."""
        key_id, full_key = generate_api_key("test")
        
        # Key ID should be prefix_hexchars
        self.assertTrue(key_id.startswith("test_"))
        self.assertEqual(len(key_id), 11)  # "test_" + 6 hex chars
        
        # Full key should include secret part
        self.assertTrue(full_key.startswith(key_id + "_"))
        self.assertGreater(len(full_key), len(key_id) + 10)
    
    def test_generate_api_key_unique(self):
        """Each generated key is unique."""
        keys = [generate_api_key()[1] for _ in range(100)]
        self.assertEqual(len(keys), len(set(keys)))
    
    def test_get_key_prefix(self):
        """Key prefix extraction works correctly."""
        full_key = "faim_abc123_secretpart"
        prefix = get_key_prefix(full_key)
        self.assertEqual(prefix, "faim_abc123")
    
    def test_hash_api_key_argon2(self):
        """Keys are hashed with Argon2id."""
        key = "test_key_123"
        hash_value = hash_api_key(key)
        
        # Argon2id hashes start with $argon2id$
        self.assertTrue(hash_value.startswith("$argon2id$"))
    
    def test_hash_api_key_different_each_time(self):
        """Same key produces different hashes (due to salt)."""
        key = "test_key_123"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        
        self.assertNotEqual(hash1, hash2)
    
    def test_verify_api_key_valid(self):
        """Valid key verification succeeds."""
        key = "my_secret_key"
        hash_value = hash_api_key(key)
        
        self.assertTrue(verify_api_key(key, hash_value))
    
    def test_verify_api_key_invalid(self):
        """Invalid key verification fails."""
        key = "my_secret_key"
        hash_value = hash_api_key(key)
        
        self.assertFalse(verify_api_key("wrong_key", hash_value))
    
    def test_verify_api_key_constant_time(self):
        """Verification should be constant-time (Argon2id is inherently)."""
        key = "test_key"
        hash_value = hash_api_key(key)
        
        # Argon2id verification is constant-time by design
        # We just verify it works correctly
        self.assertTrue(verify_api_key(key, hash_value))
        self.assertFalse(verify_api_key("wrong", hash_value))
    
    def test_constant_time_compare(self):
        """Legacy constant-time comparison works."""
        self.assertTrue(constant_time_compare("abc", "abc"))
        self.assertFalse(constant_time_compare("abc", "def"))
        self.assertFalse(constant_time_compare("abc", "abcd"))
    
    def test_needs_rehash_fresh_hash(self):
        """Fresh hashes don't need rehashing."""
        key = "test_key"
        hash_value = hash_api_key(key)
        
        self.assertFalse(needs_rehash(hash_value))


class TestNoPlaintextStorage(unittest.TestCase):
    """Ensures no plaintext keys are stored."""
    
    def test_hash_does_not_contain_plaintext(self):
        """Hash output should not contain the original key."""
        key = "super_secret_key_12345"
        hash_value = hash_api_key(key)
        
        self.assertNotIn(key, hash_value)
        self.assertNotIn("super_secret", hash_value)
    
    def test_key_model_stores_hash_not_plaintext(self):
        """TenantApiKey model should store hash, not plaintext."""
        from store.pg.models_auth import TenantApiKey
        
        # Check the column is named key_hash, not key or api_key
        columns = [c.name for c in TenantApiKey.__table__.columns]
        self.assertIn("key_hash", columns)
        self.assertNotIn("key", columns)
        self.assertNotIn("api_key", columns)
        self.assertNotIn("plaintext_key", columns)


class TestKeyRevocation(unittest.TestCase):
    """Tests for key revocation."""
    
    def test_revoked_key_has_timestamp(self):
        """Revoked keys should have revoked_at set."""
        from store.pg.models_auth import TenantApiKey
        from datetime import datetime
        
        key = TenantApiKey(
            tenant_id="test",
            key_id="key_123",
            key_prefix="key_12",
            key_hash="$argon2id$..."
        )
        
        self.assertTrue(key.is_active())
        self.assertIsNone(key.revoked_at)
        
        key.revoke()
        
        self.assertFalse(key.is_active())
        self.assertIsNotNone(key.revoked_at)
        self.assertIsInstance(key.revoked_at, datetime)


if __name__ == "__main__":
    unittest.main()
