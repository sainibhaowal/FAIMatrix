"""Unit test: Backup command safety.

Tests that:
- pg_dump uses --dbname= and --file= format
- No shell execution (list form)
- Backup timestamp never enters FAIM hashes
"""

from __future__ import annotations

import sys
from pathlib import Path

# Setup paths
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))


class TestBackupCommandSafety:
    """Verify backup command is built safely."""

    def test_build_backup_command_uses_dbname_flag(self):
        """Command should use --dbname= format."""
        from orchestration.jobs.backup import build_backup_command

        cmd = build_backup_command(
            db_url="postgresql://user:pass@host/db",
            backup_file=Path("/tmp/backup.sql"),
        )

        # Should be a list (no shell)
        assert isinstance(cmd, list)

        # Should contain --dbname=
        dbname_args = [arg for arg in cmd if arg.startswith("--dbname=")]
        assert len(dbname_args) == 1

    def test_build_backup_command_uses_file_flag(self):
        """Command should use --file= format."""
        from orchestration.jobs.backup import build_backup_command

        cmd = build_backup_command(
            db_url="postgresql://user:pass@host/db",
            backup_file=Path("/tmp/backup.sql"),
        )

        # Should contain --file=
        file_args = [arg for arg in cmd if arg.startswith("--file=")]
        assert len(file_args) == 1
        assert "/tmp/backup.sql" in file_args[0]

    def test_build_backup_command_is_list(self):
        """Command must be a list (not string) for subprocess safety."""
        from orchestration.jobs.backup import build_backup_command

        cmd = build_backup_command(
            db_url="postgresql://user:pass@host/db",
            backup_file=Path("/tmp/backup.sql"),
        )

        assert isinstance(cmd, list)
        assert all(isinstance(arg, str) for arg in cmd)

    def test_build_backup_command_starts_with_pg_dump(self):
        """Command should start with pg_dump."""
        from orchestration.jobs.backup import build_backup_command

        cmd = build_backup_command(
            db_url="postgresql://localhost/test",
            backup_file=Path("/tmp/test.sql"),
        )

        assert cmd[0] == "pg_dump"

    def test_backup_module_has_retention_function(self):
        """backup.py should have cleanup_old_backups function."""
        from orchestration.jobs.backup import cleanup_old_backups

        assert callable(cleanup_old_backups)

    def test_backup_module_has_compress_option(self):
        """perform_backup should accept compress parameter."""
        import inspect

        from orchestration.jobs.backup import perform_backup

        sig = inspect.signature(perform_backup)
        assert "compress" in sig.parameters

    def test_backup_timestamp_not_in_faim_hashes(self):
        """Backup timestamp should be operational only, not in FAIM hashes.

        This is a design verification - check that backup result doesn't
        have any hash fields that could include timestamp.
        """
        # The backup module should not produce any FAIM hashes
        backup_path = _faim_native / "orchestration" / "jobs" / "backup.py"
        content = backup_path.read_text()

        # Should not compute FAIM hashes
        assert "diagnostics_hash" not in content
        assert "graph_hash" not in content

        # The comment should indicate timestamp is operational only
        assert "never" in content.lower() or "operational" in content.lower()
