import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database URL from environment or default for dev
# In production, FAIM_DB_URL should be set in /etc/faim/*.env
_db_url = os.getenv("FAIM_DB_URL", "") or os.getenv("DATABASE_URL", "")

# Dev mode check
_mode = os.getenv("FAIM_MODE", "dev").strip().lower()
_is_dev = _mode in ("dev", "development", "local", "core_dev")

if _db_url:
    SQLALCHEMY_DATABASE_URL = _db_url
elif _is_dev:
    # In dev mode, use PostgreSQL with faim user (JSONB requires PostgreSQL)
    SQLALCHEMY_DATABASE_URL = "postgresql://faim:faim_dev_pass@localhost/faim_lab"
else:
    SQLALCHEMY_DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://faim:faim_dev_pass@localhost/faim_lab"
    )

# Create engine
# pool_pre_ping=True handles stale connections gracefully (not needed for SQLite)
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

# SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency that provides a DB session.
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
    """Create all tables - call this on app startup for dev mode."""
    from faim.models_sql import Base as ModelsBase
    ModelsBase.metadata.create_all(bind=engine)

# Auto-initialize in dev mode
if _is_dev:
    try:
        init_db()
    except Exception as e:
        print(f"[FAIM DB] Warning: Could not auto-create tables: {e}")
