"""Pytest configuration and fixtures for FAIM-Native store tests.

Uses sys.path manipulation to import Faim_Native modules directly
without triggering the main faim package initialization.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest

def _configure_isolated_test_database() -> None:
    """Give each pytest process a writable SQLite database when requested."""
    worker_id = os.environ.get("PYTEST_XDIST_WORKER")
    explicit_test_database = any(
        os.environ.get(name) for name in ("TEST_DATABASE_URL", "FAIM_DATABASE_URL")
    )
    isolation_requested = os.environ.get("FAIM_PYTEST_ISOLATE_DB") == "1"
    master_isolated_database = os.environ.get("FAIM_PYTEST_MASTER_DB") == "1"

    if explicit_test_database:
        return
    if worker_id and not (
        isolation_requested
        or master_isolated_database
        or not os.environ.get("DATABASE_URL")
    ):
        return
    if not worker_id and not isolation_requested and os.environ.get("DATABASE_URL"):
        return

    # Reusing checked-out Runtime files makes parallel runs inherit stale
    # ownership/mode bits from Docker (for example UID 1000), which can turn an
    # otherwise isolated test into a read-only SQLite failure.  This also
    # covers a clean checkout where the ignored Runtime directory does not
    # exist at all.
    suffix = worker_id or str(os.getpid())
    runtime_dir = Path(tempfile.gettempdir()) / f"faim_pytest_{os.getpid()}"
    runtime_dir.mkdir(mode=0o700, exist_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{runtime_dir}/faim_test_{suffix}.db"
    if not worker_id:
        # Mark this value so xdist workers replace the inherited master path.
        os.environ["FAIM_PYTEST_MASTER_DB"] = "1"


_configure_isolated_test_database()

# Setup path for isolated imports (avoid triggering faim.__init__)
_FAIM_NATIVE_ROOT = Path(__file__).parent.parent
if str(_FAIM_NATIVE_ROOT) not in sys.path:
    sys.path.insert(0, str(_FAIM_NATIVE_ROOT))

# Import from Faim_Native using local path
from core.contracts.types import compute_sha256  # noqa: E402
from store.pg.models_faim import create_all_tables, drop_all_tables  # noqa: E402
from store.pg.session import SessionFactory  # noqa: E402
from store.raw.raw_store import RawStore  # noqa: E402


@pytest.fixture
def tmp_blob_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for blob storage."""
    with tempfile.TemporaryDirectory(prefix="faim_blobs_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def raw_store(tmp_blob_dir: Path) -> RawStore:
    """Create a RawStore with temporary directory."""
    return RawStore(tmp_blob_dir)


@pytest.fixture
def session_factory() -> Generator[SessionFactory, None, None]:
    """Create a SessionFactory. Defaults to Postgres if URL is in environment, else SQLite."""
    import os

    # Use environment variable for native testing (e.g. PostgreSQL)
    # Default to in-memory SQLite for legacy unit tests if URL not provided
    url = (
        os.getenv("TEST_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or "sqlite:///:memory:"
    )

    factory = SessionFactory(url=url)

    # Ensure tables exist first
    try:
        drop_all_tables(factory.engine)
    except Exception:
        pass
    create_all_tables(factory.engine)

    # 100% Accuracy: Wipe everything before starting tests on a persistent DB
    if factory.engine.dialect.name in ("postgresql", "sqlite"):
        try:
            from store.pg.models_faim import Base

            with factory.engine.begin() as conn:
                for table in reversed(Base.metadata.sorted_tables):
                    conn.execute(table.delete())
        except Exception:
            pass

    yield factory


@pytest.fixture
def db_session(session_factory: SessionFactory):
    """Create a database session for tests with automatic cleanup."""
    # For PostgreSQL, we might want to ensure a clean slate even between tests
    # depending on the test type. For now, the factory wipe is enough for local runs.
    with session_factory.session() as session:
        yield session


@pytest.fixture
def sample_bytes() -> bytes:
    """Deterministic sample content for testing."""
    return b"FAIM Store Test Content - Deterministic Sample v1"


@pytest.fixture
def sample_bytes_sha256(sample_bytes: bytes) -> str:
    """SHA256 of sample_bytes for verification."""
    return compute_sha256(sample_bytes)


@pytest.fixture
def large_sample_bytes() -> bytes:
    """Larger sample content for stress testing."""
    return b"X" * 10000 + b"FAIM Large Sample" + b"Y" * 10000


# -----------------------------------------------------------------------------
# Markers
# -----------------------------------------------------------------------------


def pytest_configure(config):
    """Register custom markers."""
    # xdist sets PYTEST_XDIST_WORKER during worker configuration. Re-run the
    # database selection here so workers cannot inherit the master's path.
    _configure_isolated_test_database()
    config.addinivalue_line("markers", "acceptance: marks tests as acceptance tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
