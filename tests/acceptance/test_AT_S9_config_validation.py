"""Stage-9 Acceptance Tests: Config Validation.

Tests for runtime/config.py:
- Rejects empty TENANT_KEYS_JSON
- Defaults to STRICT profile
- Validates tenant ID format
"""

import os
import unittest


class TestConfigValidation(unittest.TestCase):
    """Test config validation."""

    def setUp(self):
        """Reset config before each test."""
        from runtime.config import reset_config

        reset_config()

        # Clear env vars
        for key in list(os.environ.keys()):
            if key.startswith("FAIM_") or key in ("DATABASE_URL", "TENANT_KEYS_JSON"):
                os.environ.pop(key, None)

    def tearDown(self):
        """Reset config after each test."""
        from runtime.config import reset_config

        reset_config()

    def test_rejects_empty_tenant_keys(self):
        """Config rejects empty TENANT_KEYS_JSON."""
        from runtime.config import load_config

        os.environ["DATABASE_URL"] = "postgresql://localhost/test"
        os.environ["TENANT_KEYS_JSON"] = "{}"

        with self.assertRaises(ValueError) as ctx:
            load_config()

        self.assertIn("TENANT_KEYS_JSON", str(ctx.exception))

    def test_rejects_missing_database_url(self):
        """Config rejects missing DATABASE_URL."""
        from runtime.config import load_config

        os.environ["TENANT_KEYS_JSON"] = '{"tenant1": ["key1"]}'

        with self.assertRaises(ValueError) as ctx:
            load_config()

        self.assertIn("DATABASE_URL", str(ctx.exception))

    def test_defaults_to_strict_profile(self):
        """Profile defaults to STRICT."""
        from runtime.config import load_config

        os.environ["DATABASE_URL"] = "postgresql://localhost/test"
        os.environ["TENANT_KEYS_JSON"] = '{"tenant1": ["key1"]}'

        config = load_config()

        self.assertEqual(config.profile_default, "STRICT")

    def test_validates_tenant_id_format(self):
        """Invalid tenant ID format rejected."""
        from runtime.config import validate_tenant_id

        self.assertTrue(validate_tenant_id("tenant_1"))
        self.assertTrue(validate_tenant_id("tenant-abc"))
        self.assertFalse(validate_tenant_id(""))
        self.assertFalse(validate_tenant_id("tenant.with.dots"))
        self.assertFalse(validate_tenant_id("tenant with spaces"))

    def test_loads_valid_config(self):
        """Valid config loads successfully."""
        from runtime.config import load_config

        os.environ["DATABASE_URL"] = "postgresql://localhost/test"
        os.environ["TENANT_KEYS_JSON"] = '{"tenant1": ["key1", "key2"]}'
        os.environ["FAIM_PROFILE_DEFAULT"] = "FAST"
        os.environ["FAIM_ENABLE_INDEX"] = "true"

        config = load_config()

        self.assertEqual(config.database_url, "postgresql://localhost/test")
        self.assertEqual(config.tenant_keys, {"tenant1": ["key1", "key2"]})
        self.assertEqual(config.profile_default, "FAST")
        self.assertTrue(config.enable_index)


class TestTenantKeyValidation(unittest.TestCase):
    """Test tenant key validation."""

    def setUp(self):
        from runtime.config import reset_config

        reset_config()

    def tearDown(self):
        from runtime.config import reset_config

        reset_config()
        for key in list(os.environ.keys()):
            if key.startswith("FAIM_") or key in ("DATABASE_URL", "TENANT_KEYS_JSON"):
                os.environ.pop(key, None)

    def test_rejects_tenant_with_empty_keys(self):
        """Tenant with empty key list rejected."""
        from runtime.config import load_config

        os.environ["DATABASE_URL"] = "postgresql://localhost/test"
        os.environ["TENANT_KEYS_JSON"] = '{"tenant1": []}'

        with self.assertRaises(ValueError) as ctx:
            load_config()

        self.assertIn("no valid keys", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
