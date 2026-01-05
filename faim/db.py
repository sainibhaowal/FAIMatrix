"""FAIM Database Configuration.

Always uses PostgreSQL. No SQLite fallback.
Configure via environment variables:
  - FAIM_DB_URL or DATABASE_URL: Full connection string
  - Default: postgresql://faim:faim_dev_pass@localhost/faim_lab
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database URL from environment
# Priority: FAIM_DB_URL > DATABASE_URL > default
SQLALCHEMY_DATABASE_URL = (
    os.getenv("FAIM_DB_URL", "")
    or os.getenv("DATABASE_URL", "")
    or "postgresql://faim:faim_dev_pass@localhost/faim_lab"
)

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
    from faim.models_sql import Base as ModelsBase

    ModelsBase.metadata.create_all(bind=engine)
