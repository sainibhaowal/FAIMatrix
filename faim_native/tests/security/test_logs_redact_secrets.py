"""Security Tests: Log Redaction (Stage-11).

Ensures:
- Logs never contain API keys
- Logs never contain database URLs with credentials
- Logs never contain authorization headers
- Redaction works on all log levels
"""

import logging
import unittest
from io import StringIO

from runtime.logging import (
    RedactingFilter,
    redact_sensitive,
    setup_logging,
)


class TestRedactSensitive(unittest.TestCase):
    """Tests for the redact_sensitive function."""
    
    def test_redact_api_key_header(self):
        """API key headers are redacted."""
        message = 'Request with X-Api-Key: secret123'
        result = redact_sensitive(message)
        
        self.assertNotIn("secret123", result)
        self.assertIn("[REDACTED]", result)
    
    def test_redact_authorization_header(self):
        """Authorization headers are redacted."""
        message = 'Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.signature'
        result = redact_sensitive(message)
        
        # The entire authorization line should be redacted
        self.assertIn("[REDACTED]", result)
        # At minimum the sensitive part should not appear as-is
        self.assertNotEqual(message, result)
    
    def test_redact_database_url(self):
        """Database URLs with credentials are redacted."""
        message = 'Connecting to postgresql://user:password123@localhost:5432/db'
        result = redact_sensitive(message)
        
        self.assertNotIn("password123", result)
        self.assertIn("[REDACTED]", result)
    
    def test_redact_redis_url(self):
        """Redis URLs with credentials are redacted."""
        message = 'Redis URL: redis://user:secret@redis:6379'
        result = redact_sensitive(message)
        
        self.assertNotIn("secret", result)
        self.assertIn("[REDACTED]", result)
    
    def test_redact_password_in_message(self):
        """Password values are redacted."""
        message = 'password=super_secret_123'
        result = redact_sensitive(message)
        
        self.assertNotIn("super_secret_123", result)
        self.assertIn("[REDACTED]", result)
    
    def test_redact_bearer_token(self):
        """Bearer tokens are redacted."""
        message = 'Bearer abc123xyz'
        result = redact_sensitive(message)
        
        # Bearer token pattern should be redacted
        self.assertIn("[REDACTED]", result)
        self.assertNotEqual(message, result)
    
    def test_redact_faim_api_key(self):
        """FAIM-generated API keys are redacted."""
        message = 'Key: faim_abc123_Ks8j2mN4pQrStUvWxYz'
        result = redact_sensitive(message)
        
        self.assertNotIn("Ks8j2mN4pQrStUvWxYz", result)
        self.assertIn("[REDACTED]", result)
    
    def test_redact_admin_key(self):
        """Admin API keys are redacted."""
        message = 'Admin key: admin_def456_secretadminkey'
        result = redact_sensitive(message)
        
        self.assertNotIn("secretadminkey", result)
        self.assertIn("[REDACTED]", result)
    
    def test_redact_json_api_key(self):
        """API keys in JSON format are redacted."""
        message = '{"api_key": "my_secret_key_123"}'
        result = redact_sensitive(message)
        
        self.assertNotIn("my_secret_key_123", result)
        self.assertIn("[REDACTED]", result)
    
    def test_preserves_safe_messages(self):
        """Non-sensitive messages are preserved."""
        message = 'User logged in successfully. Request ID: abc123'
        result = redact_sensitive(message)
        
        self.assertEqual(message, result)


class TestRedactingFilter(unittest.TestCase):
    """Tests for the RedactingFilter class."""
    
    def test_filter_redacts_log_message(self):
        """Filter redacts sensitive data in log messages."""
        filter_obj = RedactingFilter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="API key: X-Api-Key: secret123",
            args=(),
            exc_info=None,
        )
        
        filter_obj.filter(record)
        
        self.assertNotIn("secret123", record.msg)
        self.assertIn("[REDACTED]", record.msg)
    
    def test_filter_always_returns_true(self):
        """Filter should not block any log records."""
        filter_obj = RedactingFilter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Normal message",
            args=(),
            exc_info=None,
        )
        
        result = filter_obj.filter(record)
        self.assertTrue(result)


class TestLoggingIntegration(unittest.TestCase):
    """Integration tests for logging with redaction."""
    
    def test_setup_logging_adds_filter(self):
        """setup_logging should add RedactingFilter."""
        setup_logging(level="DEBUG", json_format=False)
        
        root_logger = logging.getLogger()
        handlers = root_logger.handlers
        
        # Check at least one handler has a RedactingFilter
        has_redacting_filter = False
        for handler in handlers:
            for f in handler.filters:
                if isinstance(f, RedactingFilter):
                    has_redacting_filter = True
                    break
        
        self.assertTrue(has_redacting_filter, "RedactingFilter not found in handlers")


class TestNoSensitiveInLogs(unittest.TestCase):
    """Ensures sensitive data never appears in logs."""
    
    def test_database_credentials_not_logged(self):
        """Database credentials should never appear in logs."""
        from runtime.logging import JSONFormatter
        
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="db",
            level=logging.INFO,
            pathname="db.py",
            lineno=1,
            msg="Connecting to postgresql://faim:password@db:5432/faim",
            args=(),
            exc_info=None,
        )
        
        # Note: JSONFormatter doesn't apply redaction, the filter does
        # This test verifies the message contains sensitive data before filtering
        # The RedactingFilter should be applied before formatting
        filter_obj = RedactingFilter()
        filter_obj.filter(record)
        
        output = formatter.format(record)
        
        self.assertNotIn("password", output)
    
    def test_api_key_not_logged(self):
        """API keys should never appear in logs."""
        from runtime.logging import JSONFormatter, RedactingFilter
        
        formatter = JSONFormatter()
        filter_obj = RedactingFilter()
        
        record = logging.LogRecord(
            name="auth",
            level=logging.DEBUG,
            pathname="auth.py",
            lineno=1,
            msg="Received X-Api-Key: sk_live_1234567890abcdef",
            args=(),
            exc_info=None,
        )
        
        filter_obj.filter(record)
        output = formatter.format(record)
        
        self.assertNotIn("sk_live_1234567890abcdef", output)


if __name__ == "__main__":
    unittest.main()
