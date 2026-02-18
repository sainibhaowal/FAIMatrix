"""FAIM-Native API: Health Router (Stage-9 Enhanced).

GET /health - OK (liveness)
GET /ready  - DB + tables check (readiness)
GET /version - Build info
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


# =============================================================================
# Health Check (Liveness)
# =============================================================================


@router.get("/health")
async def health_check():
    """Health check endpoint (liveness).

    Returns 200 OK if service is running.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# Readiness Check (Stage-9)
# =============================================================================

REQUIRED_TABLES = [
    "raw_refs",
    "events",
    "snapshots",
    "graph_version",
    "nodes",
    "edges",
    "ingest_dedup",
    "jobs",
    "job_events",
    "storage_files",
    "tenant_crypto_keys",
    "schema_migrations",
]


class ReadinessResponse(BaseModel):
    status: str
    db_connected: bool
    tables_ok: bool
    migrations_ok: bool
    latest_migration: int = 0
    applied_migration: int = 0


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check():
    """Readiness check endpoint (Stage-10 Hardened).

    Checks:
    - DB connection
    - Required tables exist
    - Latest migrations applied

    Returns 200 if ready, 503 if not.
    """
    from fastapi.responses import JSONResponse

    session = None
    close_session_fn = None
    try:
        # Try to get a session and check tables
        from sqlalchemy import text
        from runtime.context import close_session as close_session_fn, get_session
        from store.pg.migrate import (
            get_latest_applied_version,
            get_latest_local_version,
        )

        session = get_session()

        # Check DB connection
        result = session.execute(text("SELECT 1"))
        result.fetchone()
        db_connected = True

        # Check migrations status
        latest_local = get_latest_local_version()
        try:
            latest_applied = get_latest_applied_version(session)
        except Exception:
            latest_applied = 0

        migrations_ok = latest_applied >= latest_local

        # Check required tables exist (Dialect-aware)
        if session.bind.dialect.name == "sqlite":
            table_check = session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        else:
            table_check = session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )
            )

        existing_tables = {row[0] for row in table_check.fetchall()}

        missing = [t for t in REQUIRED_TABLES if t not in existing_tables]
        tables_ok = len(missing) == 0

        # Build common response data (No sensitive info)
        resp_data = {
            "db_connected": db_connected,
            "tables_ok": tables_ok,
            "migrations_ok": migrations_ok,
            "latest_migration": latest_local,
            "applied_migration": latest_applied,
        }

        if db_connected and tables_ok and migrations_ok:
            return ReadinessResponse(status="ready", **resp_data)
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", **resp_data},
            )

    except Exception as e:
        # Avoid leaking specifics in public health probe
        # But log it internally
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Readiness check failed: {e}")

        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "db_connected": False,
                "tables_ok": False,
                "migrations_ok": False,
                "latest_migration": 0,
                "applied_migration": 0,
            },
        )
    finally:
        if session is not None and close_session_fn is not None:
            try:
                close_session_fn(session)
            except Exception:  # nosec B110
                pass


# =============================================================================
# Version Info
# =============================================================================


@router.get("/version")
async def version_info():
    """Version and build info.

    Returns schema versions and build information.
    """
    return {
        "version": "0.10.0",
        "stage": "10",
        "faim_native": True,
        "schema": {
            "vector": "v1",
            "dimension": 256,
            "events": "v1",
            "snapshots": "v1",
            "migrations": True,
        },
        "features": {
            "multi_tenant": True,
            "sse_events": True,
            "strict_mode": True,
            "index_fallback": True,
            "rate_limiting": True,
            "idempotency": True,
            "durable_jobs": True,
        },
        "build_time": os.getenv("BUILD_TIME", "dev"),
    }
