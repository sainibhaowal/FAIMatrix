"""Acceptance Test: Migration Idempotency and Status Checking."""

import unittest

from sqlalchemy import text

from store.pg.migrate import (
    get_latest_applied_version,
    get_latest_local_version,
    run_up,
)
from store.pg.session import get_session


class TestMigrationIdempotent(unittest.TestCase):
    def setUp(self):
        self.session = get_session()

    def tearDown(self):
        self.session.close()

    def test_migration_apply_idempotent(self):
        """Applying migrations twice should be safe."""
        # 1. First apply
        run_up()
        v1 = get_latest_applied_version(self.session)
        latest = get_latest_local_version()
        self.assertGreaterEqual(v1, latest)

        # 2. Second apply
        run_up()
        v2 = get_latest_applied_version(self.session)
        self.assertEqual(v1, v2, "Version should not change on second run")

    def test_ready_fails_if_migrations_missing(self):
        """/ready should return 503 if latest migration is missing."""
        from fastapi.testclient import TestClient

        from api.app import create_app

        client = TestClient(create_app())

        # Manually "un-apply" a migration (for testing purposes)
        latest = get_latest_local_version()
        self.session.execute(
            text("DELETE FROM schema_migrations WHERE version = :v"), {"v": latest}
        )
        self.session.commit()

        # Check /ready
        response = client.get("/ready")
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertFalse(data["migrations_ok"])
        self.assertEqual(data["latest_migration"], latest)
        self.assertEqual(data["applied_migration"], latest - 1)

        # Restore for other tests
        run_up()
        response = client.get("/ready")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
