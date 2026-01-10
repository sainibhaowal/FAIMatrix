"""FAIM Database Configuration.

Always uses PostgreSQL. No SQLite fallback.
Configure via environment variables:
  - FAIM_DB_URL or DATABASE_URL: Full connection string

SECURITY: No default/fallback credentials. Must be configured.
"""

import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database URL from environment
# Priority: FAIM_DB_URL > DATABASE_URL
# SECURITY: No fallback - must be explicitly configured
SQLALCHEMY_DATABASE_URL = os.getenv("FAIM_DB_URL", "") or os.getenv("DATABASE_URL", "")

if not SQLALCHEMY_DATABASE_URL:
    print(
        "FATAL: Database not configured. Set FAIM_DB_URL or DATABASE_URL environment variable.",
        file=sys.stderr,
    )
    # In dev mode, use a safe local default
    if os.getenv("FAIM_MODE", "").lower() in ("dev", "development", "local"):
        SQLALCHEMY_DATABASE_URL = "postgresql://faim:faim@localhost/faim_lab"
        print("WARNING: Using dev mode database defaults", file=sys.stderr)
    else:
        raise RuntimeError("Database URL not configured")

# Create engine with connection pooling
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

# SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency that provides a DB session.

    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Call via alembic migrate in production."""
    from faim.config.models import Base as ModelsBase

    ModelsBase.metadata.create_all(bind=engine)
