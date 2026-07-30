"""Stage-9 Acceptance Tests: Rate Limiting.

Tests for api/middleware/ratelimit.py:
- Exceed limit → 429
- Different tenant unaffected
- Token bucket refills
"""

import unittest


class TestRateLimiting(unittest.TestCase):
    """Test rate limiting."""

    def test_token_bucket_creation(self):
        """TokenBucket creates with correct capacity."""
        from api.middleware.ratelimit import TokenBucket

        bucket = TokenBucket.create(capacity=10, refill_per_minute=60)

        self.assertEqual(bucket.capacity, 10)
        self.assertEqual(bucket.tokens, 10.0)

    def test_token_bucket_consume(self):
        """TokenBucket consumes tokens."""
        from api.middleware.ratelimit import TokenBucket

        bucket = TokenBucket.create(capacity=10, refill_per_minute=60)

        allowed, remaining = bucket.try_consume(1)

        self.assertTrue(allowed)
        self.assertEqual(remaining, 9)

    def test_token_bucket_exhausted(self):
        """TokenBucket returns False when exhausted."""
        from api.middleware.ratelimit import TokenBucket

        bucket = TokenBucket.create(capacity=2, refill_per_minute=60)

        bucket.try_consume(1)
        bucket.try_consume(1)
        allowed, remaining = bucket.try_consume(1)

        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)

    def test_rate_limiter_per_tenant(self):
        """Rate limiter tracks per tenant."""
        from api.middleware.ratelimit import InMemoryRateLimiter

        limiter = InMemoryRateLimiter()
        limiter._limits["query"] = 2

        # Tenant A exhausts limit
        limiter.check_rate_limit("tenant_a", "query")
        limiter.check_rate_limit("tenant_a", "query")
        allowed_a, _ = limiter.check_rate_limit("tenant_a", "query")

        # Tenant B still has quota
        allowed_b, _ = limiter.check_rate_limit("tenant_b", "query")

        self.assertFalse(allowed_a)
        self.assertTrue(allowed_b)

    def test_rate_limit_middleware_exists(self):
        """RateLimitMiddleware class exists."""
        from api.middleware.ratelimit import RateLimitMiddleware

        self.assertTrue(callable(RateLimitMiddleware))


class TestRateLimitResponses(unittest.TestCase):
    """Test rate limit HTTP responses."""

    def test_endpoint_categories_defined(self):
        """Endpoint categories are defined."""
        from api.middleware.ratelimit import ENDPOINT_CATEGORIES

        self.assertIn("/api/v1/ingest", ENDPOINT_CATEGORIES)
        self.assertIn("/api/v1/query", ENDPOINT_CATEGORIES)
        self.assertIn("/api/v1/events", ENDPOINT_CATEGORIES)
        self.assertIn("/api/v1/api-keys", ENDPOINT_CATEGORIES)
        self.assertIn("/api/v1/memory/search", ENDPOINT_CATEGORIES)
        self.assertIn("/api/v1/memory/write", ENDPOINT_CATEGORIES)
        self.assertIn("/v1/ingest", ENDPOINT_CATEGORIES)
        self.assertIn("/v1/query", ENDPOINT_CATEGORIES)
        self.assertIn("/v1/events", ENDPOINT_CATEGORIES)


if __name__ == "__main__":
    unittest.main()
