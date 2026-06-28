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

worker_id = os.environ.get("PYTEST_XDIST_WORKER")
if worker_id:
    runtime_dir = Path(__file__).parent.parent / "Runtime"
    runtime_dir.mkdir(exist_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{runtime_dir}/faim_test_{worker_id}.db"

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
    config.addinivalue_line("markers", "acceptance: marks tests as acceptance tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
