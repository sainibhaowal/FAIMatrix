from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from pydantic import BaseModel
import shutil

from faim.db import get_db
from faim.api.auth_middleware import get_current_user_oidc
from faim.api.auth import allow_dev_mode
from faim.models_sql import User, Project, Org, OrgMember, GraphOwnership, Document
import os

router = APIRouter(prefix="/admin", tags=["Admin & Ops"])

# --- Check if dev mode ---
def is_dev_mode() -> bool:
    """Check if running in development mode."""
    mode = os.getenv("FAIM_MODE", "dev").strip().lower()
    return mode in ("dev", "development", "local", "core_dev")

# --- Helper: Verify Super Admin ---
def verify_admin():
    """
    In dev mode: returns a mock admin user object.
    In prod mode: should require actual OIDC auth (not implemented).
    """
    if is_dev_mode():
        # Return a mock user object for dev mode
        class MockUser:
            id = "dev-admin"
            email = "dev@localhost"
            full_name = "Dev Admin"
            status = "active"
        return MockUser()
    # Production would require real auth - for now raise
    raise HTTPException(status_code=401, detail="Auth required (dev mode disabled)")

# --- Schemas ---
class SystemStats(BaseModel):
    total_users: int
    total_projects: int
    total_graphs: int
    total_docs: int
    active_users_24h: int

class UserView(BaseModel):
    id: str
    email: str
    full_name: str
    status: str
    created_at: str

# --- Endpoints ---

@router.get("/stats", response_model=SystemStats)
def get_system_stats(
    db: Session = Depends(get_db),
    admin = Depends(verify_admin)
):
    try:
        users = db.query(User).count()
    except Exception:
        users = 0
    try:
        projects = db.query(Project).count()
    except Exception:
        projects = 0
    try:
        graphs = db.query(GraphOwnership).count()
    except Exception:
        graphs = 0
    try:
        docs = db.query(Document).count()
    except Exception:
        docs = 0
    
    active = 0
    
    return SystemStats(
        total_users=users,
        total_projects=projects,
        total_graphs=graphs,
        total_docs=docs,
        active_users_24h=active
    )

@router.get("/users", response_model=List[UserView])
def list_users(
    skip: int = 0, 
    limit: int = 50,
    db: Session = Depends(get_db),
    admin = Depends(verify_admin)
):
    try:
        users = db.query(User).offset(skip).limit(limit).all()
        return [
            UserView(
                id=str(u.id),
                email=u.email or "",
                full_name=u.full_name or "",
                status=u.status,
                created_at=str(u.created_at)
            ) for u in users
        ]
    except Exception:
        return []

@router.post("/users/{user_id}/ban")
def ban_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(verify_admin)
):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.status = "suspended"
    db.commit()
    return {"status": "banned"}

@router.post("/users/{user_id}/unban")
def unban_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(verify_admin)
):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.status = "active"
    db.commit()
    return {"status": "active"}
