"""Acceptance Test: Backup/Restore Drill Rowcounts."""

import os
import subprocess
import unittest

from sqlalchemy import text

from store.pg.session import get_session


class TestBackupRestoreDrill(unittest.TestCase):
    def test_backup_roundtrip_rowcounts_match(self):
        """Drill script should successfully backup and restore."""
        import os

        db_url = os.getenv("DATABASE_URL", "")
        if "sqlite" in db_url:
            self.skipTest(
                "Backup drill is mandatory for Postgres production but skipped on SQLite (logic-only mode)"
            )

        # Skip if running outside of CI context (no Docker dump available)
        # The drill script requires USE_DOCKER_DUMP=true in CI to avoid pg_dump version mismatch
        if os.getenv("USE_DOCKER_DUMP") != "true":
            self.skipTest(
                "Backup drill requires Docker context (USE_DOCKER_DUMP=true) to avoid pg_dump version mismatch"
            )

        if "drill" in db_url:
            self.skipTest("Skipping drill test when running against drill DB (prevention of recursion)")

        session = get_session()

        # 1. Get row counts from source
        tables = ["nodes", "edges", "events", "snapshots"]
        counts_source = {}
        for table in tables:
            result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            counts_source[table] = result.scalar()

        session.close()

        # 2. Run the drill script
        # Note: This requires DATABASE_URL to be set and pg_dump to be available.
        # We assume the environment is set up.
        try:
            subprocess.run(
                ["./scripts/drill_backup_restore.sh"], check=True, capture_output=True
            )
        except subprocess.CalledProcessError as e:
            self.fail(f"Drill script failed: {e.stdout.decode()}\n{e.stderr.decode()}")

        # 3. Get row counts from drill DB
        drill_url = os.getenv("DATABASE_URL").rsplit("/", 1)[0] + "/faim_drill"
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        drill_engine = create_engine(drill_url)
        drill_session = sessionmaker(bind=drill_engine)()

        counts_drill = {}
        for table in tables:
            result = drill_session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            counts_drill[table] = result.scalar()

        drill_session.close()

        # 4. Compare
        for table in tables:
            self.assertEqual(
                counts_source[table],
                counts_drill[table],
                f"Row count mismatch for {table}",
            )

    def test_drill_script_exists_and_is_executable(self):
        """Ensure the drill script is present and runnable."""
        path = "scripts/drill_backup_restore.sh"
        self.assertTrue(os.path.exists(path))
        self.assertTrue(os.access(path, os.X_OK))


if __name__ == "__main__":
    unittest.main()
