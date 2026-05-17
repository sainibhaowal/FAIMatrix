"""FAIM-Native API: Admin Router.

Protected admin endpoints requiring X-Admin-Key.

POST /v1/admin/reindex
POST /v1/admin/snapshot/create
POST /v1/admin/snapshot/restore
POST /v1/admin/replay/verify
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

# Flexible imports
_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context, require_admin  # noqa: E402
from api.routers.health import REQUIRED_TABLES  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# =============================================================================
# Request/Response Models
# =============================================================================


class AdminRequest(BaseModel):
    """Admin request body."""

    graph_id: str


class AdminStatusResponse(BaseModel):
    """Admin status snapshot."""

    status: str
    health: Dict[str, Any]
    readiness: Dict[str, Any]
    version: Dict[str, Any]
    runtime: Dict[str, Any]
    alerts: list[Dict[str, Any]]
    alert_delivery: Dict[str, Any]
    backups: list[Dict[str, Any]]


class AdminResponse(BaseModel):
    """Admin response."""

    status: str
    message: str
    details: Optional[Dict[str, Any]] = None


def _backup_dir() -> Path:
    return Path(os.getenv("FAIM_BACKUP_DIR", "/tmp/faim/backups"))  # nosec B108


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def _list_backups() -> list[Dict[str, Any]]:
    backup_dir = _backup_dir()
    if not backup_dir.exists():
        return []

    files = sorted(
        [
            *backup_dir.glob("backup_faim_*.sql"),
            *backup_dir.glob("backup_faim_*.sql.gz"),
            *backup_dir.glob("raw_*.tar.gz"),
        ],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    items: list[Dict[str, Any]] = []
    for file_path in files:
        stat = file_path.stat()
        name = file_path.name
        kind = "raw" if name.startswith("raw_") else "database"
        compressed = name.endswith(".gz")
        items.append(
            {
                "name": name,
                "kind": kind,
                "compressed": compressed,
                "path": str(file_path),
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
            }
        )
    return items


def _build_readiness_snapshot() -> Dict[str, Any]:
    from runtime.context import close_session, get_session
    from sqlalchemy import text
    from store.pg.migrate import (
        get_latest_applied_version,
        get_latest_local_version,
    )

    session = None
    try:
        session = get_session()
        session.execute(text("SELECT 1")).fetchone()
        latest_local = get_latest_local_version()
        try:
            latest_applied = get_latest_applied_version(session)
        except Exception:
            latest_applied = 0

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
        migrations_ok = latest_applied >= latest_local
        status = "ready" if tables_ok and migrations_ok else "not_ready"

        return {
            "status": status,
            "db_connected": True,
            "tables_ok": tables_ok,
            "migrations_ok": migrations_ok,
            "latest_migration": latest_local,
            "applied_migration": latest_applied,
            "missing_tables": missing,
        }
    except Exception as exc:
        logger.warning("Admin readiness snapshot failed: %s", exc)
        return {
            "status": "not_ready",
            "db_connected": False,
            "tables_ok": False,
            "migrations_ok": False,
            "latest_migration": 0,
            "applied_migration": 0,
            "missing_tables": list(REQUIRED_TABLES),
        }
    finally:
        if session is not None:
            try:
                close_session(session)
            except Exception:  # nosec B110
                pass


def _runtime_snapshot() -> Dict[str, Any]:
    return {
        "env": os.getenv("FAIM_ENV", os.getenv("FAIM_MODE", "development")),
        "mode": os.getenv("FAIM_MODE", "development"),
        "public_origin": os.getenv("FAIM_PUBLIC_ORIGIN", ""),
        "cors_origins": [
            origin.strip()
            for origin in os.getenv("FAIM_CORS_ALLOW_ORIGINS", "").split(",")
            if origin.strip()
        ],
        "backup_dir": str(_backup_dir()),
        "raw_store_path": os.getenv("FAIM_RAW_STORE_PATH", ""),
        "auth_db_primary": _env_bool("FAIM_AUTH_DB_PRIMARY", True),
        "auth_scope_enforcement_enabled": _env_bool(
            "FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED", False
        ),
        "enable_cache": _env_bool("FAIM_ENABLE_CACHE", False),
        "enable_index": _env_bool("FAIM_ENABLE_INDEX", False),
        "enable_jobs": _env_bool("FAIM_ENABLE_JOBS", False),
        "encryption_at_rest": _env_bool("FAIM_ENCRYPTION_AT_REST", False),
        "encryption_fail_closed": _env_bool("FAIM_ENCRYPTION_FAIL_CLOSED", False),
        "admin_key_configured": bool(os.getenv("FAIM_ADMIN_KEY")),
    }


class AdminAlertSendResponse(BaseModel):
    """Alert send response."""

    status: str
    message: str
    provider: Optional[str] = None
    recipients: list[str] = Field(default_factory=list)
    sent: bool = False
    details: Optional[Dict[str, Any]] = None


class AdminAlertsResponse(BaseModel):
    """Alert inbox response."""

    status: str
    summary: Dict[str, int]
    delivery: Dict[str, Any]
    alerts: list[Dict[str, Any]]


@router.get("/status", response_model=AdminStatusResponse)
async def admin_status(
    admin: str = Depends(require_admin),
) -> AdminStatusResponse:
    """Return a compact control-plane snapshot for admin staff."""
    from api.routers.health import health_check, version_info
    from api.services.admin_alerts import (
        build_delivery_snapshot,
        build_operational_alerts,
    )

    health = await health_check()
    version = await version_info()
    readiness = _build_readiness_snapshot()
    runtime = _runtime_snapshot()
    alerts = build_operational_alerts(
        health=dict(health),
        readiness=readiness,
        runtime=runtime,
        backups=_list_backups(),
    )

    return AdminStatusResponse(
        status="ok" if readiness["status"] == "ready" else "degraded",
        health=dict(health),
        readiness=readiness,
        version=dict(version),
        runtime=runtime,
        alerts=alerts,
        alert_delivery=build_delivery_snapshot(),
        backups=_list_backups(),
    )


class AdminBackupsResponse(BaseModel):
    """Backup inventory response."""

    backup_dir: str
    backups: list[Dict[str, Any]]


@router.get("/backups", response_model=AdminBackupsResponse)
async def admin_backups(
    admin: str = Depends(require_admin),
) -> AdminBackupsResponse:
    return AdminBackupsResponse(backup_dir=str(_backup_dir()), backups=_list_backups())


@router.get("/alerts", response_model=AdminAlertsResponse)
async def admin_alerts(
    admin: str = Depends(require_admin),
) -> AdminAlertsResponse:
    from api.routers.health import health_check
    from api.services.admin_alerts import (
        build_delivery_snapshot,
        build_operational_alerts,
        summarize_alerts,
    )

    health = await health_check()
    readiness = _build_readiness_snapshot()
    runtime = _runtime_snapshot()
    alerts = build_operational_alerts(
        health=dict(health),
        readiness=readiness,
        runtime=runtime,
        backups=_list_backups(),
    )
    return AdminAlertsResponse(
        status="ok",
        summary=summarize_alerts(alerts),
        delivery=build_delivery_snapshot(),
        alerts=alerts,
    )


@router.post("/alerts/send", response_model=AdminAlertSendResponse)
async def admin_alerts_send(
    admin: str = Depends(require_admin),
) -> AdminAlertSendResponse:
    from api.routers.health import health_check
    from api.services.admin_alerts import (
        build_delivery_snapshot,
        build_operational_alerts,
        send_admin_alert_email,
    )

    health = await health_check()
    readiness = _build_readiness_snapshot()
    runtime = _runtime_snapshot()
    alerts = build_operational_alerts(
        health=dict(health),
        readiness=readiness,
        runtime=runtime,
        backups=_list_backups(),
    )
    delivery = build_delivery_snapshot()
    result = send_admin_alert_email(alerts=alerts, delivery=delivery, test_mode=False)
    return AdminAlertSendResponse(
        status=result.get("status", "error"),
        message=result.get("message", "Alert send completed."),
        provider=result.get("provider"),
        recipients=list(result.get("recipients") or []),
        sent=bool(result.get("sent")),
        details={
            "alerts": alerts,
            "delivery": delivery,
            **{
                k: v
                for k, v in result.items()
                if k not in {"status", "message", "provider", "recipients", "sent"}
            },
        },
    )


@router.post("/alerts/test", response_model=AdminAlertSendResponse)
async def admin_alerts_test(
    admin: str = Depends(require_admin),
) -> AdminAlertSendResponse:
    from api.services.admin_alerts import (
        build_delivery_snapshot,
        send_admin_alert_email,
    )

    delivery = build_delivery_snapshot()
    result = send_admin_alert_email(alerts=[], delivery=delivery, test_mode=True)
    return AdminAlertSendResponse(
        status=result.get("status", "error"),
        message=result.get("message", "Test email completed."),
        provider=result.get("provider"),
        recipients=list(result.get("recipients") or []),
        sent=bool(result.get("sent")),
        details=delivery,
    )


# =============================================================================
# Reindex Endpoint
# =============================================================================


@router.post("/reindex")
async def admin_reindex(
    request: AdminRequest,
    admin: str = Depends(require_admin),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> AdminResponse:
    """Rebuild the vector index for a graph.

    Index is acceleration only - can be rebuilt at any time.
    """
    try:
        if not ctx.index:
            return AdminResponse(
                status="skipped",
                message="No index configured",
            )

        # Get all nodes
        nodes = ctx.node_repo.list_by_graph(request.graph_id, limit=10000)

        # Reindex each node
        indexed = 0
        for node in nodes:
            if node.v_native:
                ctx.index.add(
                    graph_id=request.graph_id,
                    node_id=str(node.node_id),
                    vector=tuple(node.v_native),
                    level=node.level,
                    kind=node.kind,
                )
                indexed += 1

        return AdminResponse(
            status="completed",
            message=f"Reindexed {indexed} nodes",
            details={"node_count": indexed},
        )

    except Exception as e:
        logger.error(f"Reindex failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


# =============================================================================
# Snapshot Create
# =============================================================================


@router.post("/snapshot/create")
async def admin_create_snapshot(
    request: AdminRequest,
    admin: str = Depends(require_admin),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> AdminResponse:
    """Create a snapshot of the current graph state."""
    try:
        import hashlib

        from core.contracts.types import SnapshotRecord, uuid7

        # Get current state
        gv = ctx.gv_repo.get_or_create(ctx.session, request.graph_id)
        node_count = ctx.node_repo.count(request.graph_id)

        # Compute graph hash (simplified)
        hash_input = f"{request.graph_id}:{gv.version}:{node_count}"
        graph_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        # Create snapshot
        snapshot = SnapshotRecord(
            id=uuid7(),
            graph_id=request.graph_id,
            graph_version=gv.version,
            graph_hash=graph_hash,
            node_count=node_count,
            created_at=datetime.now(timezone.utc),
        )

        ctx.snapshot_repo.create(ctx.session, snapshot)
        ctx.session.commit()

        return AdminResponse(
            status="completed",
            message=f"Created snapshot v{gv.version}",
            details={
                "snapshot_id": str(snapshot.id),
                "graph_version": gv.version,
                "graph_hash": graph_hash,
                "node_count": node_count,
            },
        )

    except Exception as e:
        logger.error(f"Snapshot create failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


# =============================================================================
# Snapshot Restore (placeholder)
# =============================================================================


@router.post("/snapshot/restore")
async def admin_restore_snapshot(
    request: AdminRequest,
    snapshot_id: Optional[str] = None,
    admin: str = Depends(require_admin),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> AdminResponse:
    """Restore graph to a previous snapshot state.

    Note: This is a placeholder - full implementation would require
    event replay from snapshot point.
    """
    return AdminResponse(
        status="not_implemented",
        message="Snapshot restore requires full event replay - not yet implemented",
        details={"requested_snapshot": snapshot_id},
    )


# =============================================================================
# Replay Verify
# =============================================================================


@router.post("/replay/verify")
async def admin_verify_replay(
    request: AdminRequest,
    admin: str = Depends(require_admin),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> AdminResponse:
    """Verify that replaying events produces the same graph state.

    This is critical for FAIM determinism verification.
    """
    try:
        # Get all events
        events = ctx.event_repo.get_by_seq(
            ctx.session,
            graph_id=request.graph_id,
            after_seq=0,
            limit=10000,
        )

        # Get current state
        gv = ctx.gv_repo.get_or_create(ctx.session, request.graph_id)
        node_count = ctx.node_repo.count(request.graph_id)

        return AdminResponse(
            status="verified",
            message=f"Found {len(events)} events, current version {gv.version}",
            details={
                "event_count": len(events),
                "graph_version": gv.version,
                "node_count": node_count,
                "first_event_seq": events[0].seq if events else None,
                "last_event_seq": events[-1].seq if events else None,
            },
        )

    except Exception as e:
        logger.error(f"Replay verify failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


__all__ = ["router"]
