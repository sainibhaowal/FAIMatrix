"""Acceptance Test: Durable Jobs."""

import os
import tempfile
import time
import unittest
from pathlib import Path
from uuid import uuid4

from orchestration.jobs.job_store import JobStore
from store.pg.session import get_session


class TestJobDurability(unittest.TestCase):
    def setUp(self):
        self._prev_test_database_url = os.getenv("TEST_DATABASE_URL")
        self._prev_database_url = os.getenv("DATABASE_URL")
        self._db_path = Path(tempfile.gettempdir()) / f"faim_s10_jobs_{uuid4().hex}.db"
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
        self.tenant_id = "test_tenant_s10"
        self.graph_id = "test_graph_s10"

        # Ensure migrations applied
        from store.pg.migrate import run_up

        run_up()

    def tearDown(self):
        # Cleanup jobs
        self.session.rollback()
        self.session.execute(text("DELETE FROM job_events"))
        self.session.execute(
            text("DELETE FROM jobs WHERE tenant_id = :t"), {"t": self.tenant_id}
        )
        self.session.commit()
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

    def test_job_claim_order_deterministic(self):
        """Jobs should be claimed in order of creation."""
        j1 = JobStore.enqueue(
            self.session, self.tenant_id, self.graph_id, "evolve", {"id": 1}
        )
        time.sleep(0.1)
        j2 = JobStore.enqueue(
            self.session, self.tenant_id, self.graph_id, "evolve", {"id": 2}
        )

        c1 = JobStore.claim_next(self.session)
        c2 = JobStore.claim_next(self.session)

        self.assertEqual(c1.job_id, j1)
        self.assertEqual(c2.job_id, j2)

    def test_job_durability_resume_after_stale(self):
        """A 'running' job that timed out should be claimable again."""
        job_id = JobStore.enqueue(
            self.session, self.tenant_id, self.graph_id, "evolve", {"id": "stale"}
        )

        # 1. Claim it
        job = JobStore.claim_next(self.session)
        self.assertEqual(job.status, "running")

        # 2. Manually make it stale (backdate updated_at)
        from datetime import datetime, timedelta, timezone

        job.updated_at = datetime.now(timezone.utc) - timedelta(seconds=600)
        self.session.commit()

        # 3. Claim again - should succeed
        job_retry = JobStore.claim_next(self.session, timeout_seconds=300)
        self.assertIsNotNone(job_retry)
        self.assertEqual(job_retry.job_id, job_id)

    def test_job_single_writer_lock_evolve(self):
        """Two workers should not be able to evolve the same graph simultaneously."""
        from cache.locks import evolve_lock

        # 1. Acquire lock manually
        with evolve_lock(self.graph_id) as acquired:
            self.assertTrue(acquired)

            # 2. Enqueue and try to run evolve via worker logic
            JobStore.enqueue(self.session, self.tenant_id, self.graph_id, "evolve", {})

            # Worker execution should fail to acquire lock
            from orchestration.evolve_flow import run_evolve

            result = run_evolve(
                graph_id=self.graph_id, tenant_id=self.tenant_id, session=self.session
            )

            self.assertEqual(result.status, "error")
            self.assertIn("Could not acquire evolution lock", result.error)


from sqlalchemy import text  # noqa: E402

if __name__ == "__main__":
    unittest.main()
