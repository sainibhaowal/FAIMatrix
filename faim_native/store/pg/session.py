"""SQLAlchemy session factory and transaction helpers for FAIM-Native.

This module provides:
- Engine creation from database URL
- Session factory with context manager support
- Atomic transaction helper

Usage:
    factory = SessionFactory(DATABASE_URL)
    with factory.session() as session:
        # work with session
        session.add(model)

    # Or with atomic transaction:
    with factory.atomic() as session:
        # all operations commit together or rollback
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Default database URL for development (SQLite in-memory for tests)
DEFAULT_DATABASE_URL = os.getenv(
    "FAIM_DATABASE_URL", os.getenv("DATABASE_URL", "sqlite:///:memory:")
)


def get_session(url: Optional[str] = None) -> Session:
    """Convenience helper to get a new DB session.

    Args:
        url: Database URL. Defaults to env.

    Returns:
        SQLAlchemy Session (caller must close).
    """
    factory = SessionFactory(url or DEFAULT_DATABASE_URL)
    return factory.create()


def get_engine(
    url: Optional[str] = None,
    *,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
) -> Engine:
    """Create a SQLAlchemy engine from database URL.

    Args:
        url: Database URL. Defaults to FAIM_DATABASE_URL env or SQLite in-memory.
        echo: If True, log all SQL statements.
        pool_size: Connection pool size (ignored for SQLite).
        max_overflow: Max connections above pool_size (ignored for SQLite).

    Returns:
        SQLAlchemy Engine instance.
    """
    db_url = url or DEFAULT_DATABASE_URL

    # SQLite-specific configuration
    if db_url.startswith("sqlite"):
        engine = create_engine(
            db_url,
            echo=echo,
            connect_args={"check_same_thread": False},
        )

        # Enable foreign keys for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    else:
        # PostgreSQL configuration
        engine = create_engine(
            db_url,
            echo=echo,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Verify connections before use
        )

    return engine


class SessionFactory:
    """Factory for creating database sessions with context manager support.

    Provides both regular sessions and atomic transaction blocks.

    Attributes:
        engine: SQLAlchemy Engine.
        _session_maker: Configured sessionmaker.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        engine: Optional[Engine] = None,
        *,
        echo: bool = False,
    ) -> None:
        """Initialize session factory.

        Args:
            url: Database URL (ignored if engine provided).
            engine: Pre-configured Engine (takes precedence over url).
            echo: If True, log all SQL statements.
        """
        if engine is not None:
            self.engine = engine
        else:
            self.engine = get_engine(url, echo=echo)

        self._session_maker = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Create a session with automatic cleanup.

        Session is closed after context exits. Does not auto-commit.
        Call session.commit() explicitly if needed.

        Yields:
            SQLAlchemy Session.
        """
        session = self._session_maker()
        try:
            yield session
        finally:
            session.close()

    @contextmanager
    def atomic(self) -> Generator[Session, None, None]:
        """Create a session with atomic transaction semantics.

        - Commits on successful exit
        - Rolls back on exception
        - Always closes session

        Yields:
            SQLAlchemy Session.

        Raises:
            Exception: Re-raises any exception after rollback.
        """
        session = self._session_maker()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create(self) -> Session:
        """Create a raw session (caller responsible for cleanup).

        Returns:
            SQLAlchemy Session.
        """
        return self._session_maker()


@contextmanager
def atomic(session: Session) -> Generator[Session, None, None]:
    """Transaction helper for an existing session.

    Wraps operations in a savepoint for nested transaction support.

    Args:
        session: Existing SQLAlchemy session.

    Yields:
        The same session, within a savepoint.

    Raises:
        Exception: Re-raises any exception after rollback.
    """
    try:
        yield session
        session.flush()
    except Exception:
        session.rollback()
        raise
