from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
import os
from datetime import datetime

from faim.db import get_db
from faim.api.auth_middleware import get_current_user_oidc
from faim.models_sql import User, Project, Org, OrgMember, AuditLog, FeatureFlag
from faim.api.rate_limiter import get_redis
from faim.api.router_admin import verify_admin

router = APIRouter(prefix="/ops", tags=["Operations"])

# --- Schemas ---


class HealthStatus(BaseModel):
    db: str
    redis: str
    keycloak: str  # Mocked for now
    version: str = "1.0.0"


class FeatureFlagOut(BaseModel):
    name: str
    is_enabled: bool
    description: Optional[str]


class AuditLogOut(BaseModel):
    id: str
    ts: datetime
    action: str
    target_type: str
    actor_user_id: Optional[str]
    outcome: str


class ThrottleRequest(BaseModel):
    project_id: str
    limit_graphs: int
    limit_storage_mb: int


# --- Endpoints ---


@router.get("/health", response_model=HealthStatus)
def check_health(db: Session = Depends(get_db)):
    # 1. DB Check
    db_status = "unhealthy"
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        pass

    # 2. Redis Check
    redis_status = "unhealthy"
    r = get_redis()
    if r:
        redis_status = "healthy"
    else:
        redis_status = "offline"

    return HealthStatus(
        db=db_status,
        redis=redis_status,
        keycloak="healthy",  # Assumed if we verified token to get here? Actually this is public check usually
    )
    # Note: Health check is usually public, but we can protect it or have a public /healthz separately.
    # This is the "Admin Operator View" of health.


@router.get("/flags", response_model=List[FeatureFlagOut])
def list_flags(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    try:
        flags = db.query(FeatureFlag).all()
        # Ensure defaults exist if not in DB
        defaults = [
            ("maintenance_mode", "Refuse new requests"),
            ("signup_disabled", "Prevent new users"),
        ]

        db_map = {f.name: f for f in flags}

        for name, desc in defaults:
            if name not in db_map:
                new_f = FeatureFlag(name=name, description=desc, is_enabled=False)
                db.add(new_f)
                db_map[name] = new_f

        if defaults:
            db.commit()

        return [
            FeatureFlagOut(name=f.name, is_enabled=f.is_enabled, description=f.description)
            for f in db_map.values()
        ]
    except Exception:
        return []


@router.post("/flags/{name}")
def toggle_flag(
    name: str,
    enabled: bool = Body(..., embed=True),
    db: Session = Depends(get_db),
    admin=Depends(verify_admin),
):
    try:
        flag = db.query(FeatureFlag).get(name)
        if not flag:
            raise HTTPException(status_code=404, detail="Flag not found")
        flag.is_enabled = enabled
        db.commit()
        return {"status": "updated", "is_enabled": enabled}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/audit", response_model=List[AuditLogOut])
def get_audit_logs(limit: int = 100, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    try:
        logs = db.query(AuditLog).order_by(AuditLog.ts.desc()).limit(limit).all()
        return [
            AuditLogOut(
                id=str(l.id),
                ts=l.ts,
                action=l.action,
                target_type=l.target_type or "unknown",
                actor_user_id=str(l.actor_user_id) if l.actor_user_id else None,
                outcome=l.outcome,
            )
            for l in logs
        ]
    except Exception:
        return []


@router.post("/tenants/throttle")
def throttle_tenant(
    payload: ThrottleRequest, db: Session = Depends(get_db), admin: User = Depends(verify_admin)
):
    project = db.query(Project).get(payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Overwrite plan_limits
    # We must preserve existing struct or just overwrite.
    # Let's simple overwrite for throttle.
    project.plan_limits = {
        "graphs": payload.limit_graphs,
        "storage_mb": payload.limit_storage_mb,
        "throttled": True,
    }
    db.commit()

    # Audit
    log = AuditLog(
        actor_user_id=admin.id,
        action="throttle_project",
        target_type="project",
        target_id=str(project.id),
        outcome="success",
    )
    db.add(log)
    db.commit()

    return {"status": "throttled", "limits": project.plan_limits}


# --- Backup Operations ---


class BackupResponse(BaseModel):
    status: str
    message: str
    backup_file: Optional[str] = None


@router.post("/backup", response_model=BackupResponse)
def trigger_backup(
    db: Session = Depends(get_db),
    admin: User = Depends(verify_admin),
):
    """
    Trigger a manual database backup.

    Backups are saved locally to /tmp/faim/backups/.
    Requires admin privileges.
    """
    try:
        from faim.ops.backup import perform_backup

        # Run the backup
        result = perform_backup()

        # Audit log
        log = AuditLog(
            actor_user_id=admin.id,
            action="manual_backup",
            target_type="system",
            target_id="database",
            outcome="success",
        )
        db.add(log)
        db.commit()

        return BackupResponse(
            status="success",
            message="Backup completed successfully",
            backup_file=result.get("backup_file") if isinstance(result, dict) else None,
        )

    except ImportError as e:
        return BackupResponse(
            status="error",
            message=f"Backup module not available: {e}",
        )
    except Exception as e:
        # Audit failure
        try:
            log = AuditLog(
                actor_user_id=admin.id,
                action="manual_backup",
                target_type="system",
                target_id="database",
                outcome=f"failed: {str(e)[:100]}",
            )
            db.add(log)
            db.commit()
        except Exception:
            pass

        return BackupResponse(
            status="error",
            message=f"Backup failed: {str(e)}",
        )
