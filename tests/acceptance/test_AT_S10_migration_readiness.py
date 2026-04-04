"""Acceptance Test: Migration Idempotency and Status Checking."""

import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from store.pg.migrate import (
    get_latest_applied_version,
    get_latest_local_version,
    run_up,
)
from store.pg.session import get_session


class TestMigrationIdempotent(unittest.TestCase):
    def setUp(self):
        self._prev_test_database_url = os.getenv("TEST_DATABASE_URL")
        self._prev_database_url = os.getenv("DATABASE_URL")
        self._db_path = Path(tempfile.gettempdir()) / f"faim_s10_{uuid4().hex}.db"
        self._db_url = f"sqlite:///{self._db_path}"
        os.environ["TEST_DATABASE_URL"] = self._db_url
        os.environ["DATABASE_URL"] = self._db_url

        from runtime import context as runtime_context
        from store.pg import session as pg_session

        pg_session._SESSION_FACTORY_CACHE.clear()
        runtime_context._engine = None
        runtime_context._engine_db_url = None
        runtime_context._SessionLocal = None
        self.session = get_session()

    def tearDown(self):
        self.session.close()
        from runtime import context as runtime_context
        from store.pg import session as pg_session

        pg_session._SESSION_FACTORY_CACHE.clear()
        runtime_context._engine = None
        runtime_context._engine_db_url = None
        runtime_context._SessionLocal = None

        if self._prev_test_database_url is None:
            os.environ.pop("TEST_DATABASE_URL", None)
        else:
            os.environ["TEST_DATABASE_URL"] = self._prev_test_database_url

        if self._prev_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self._prev_database_url

        try:
            if self._db_path.exists():
                self._db_path.unlink()
        except OSError:
            pass

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
        from api.app import create_app
        from fastapi.testclient import TestClient

        run_up()
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
