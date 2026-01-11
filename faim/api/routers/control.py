"""
FAIM Control Plane Router - Complete Profile Features

Provides:
- /v1/me (GET) - User info with graph, avatar, verification status, created_at
- /v1/me (PATCH) - Update profile
- /v1/me (DELETE) - Delete account permanently
- /v1/me/password - Change password
- /v1/me/resend-verification - Resend email verification
- /v1/graphs - List/create graphs
"""

import datetime
import hashlib
import logging
import uuid
from typing import List, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from faim.api.middleware.auth_middleware import get_current_user_oidc
from faim.config.database import get_db
from faim.config.models import (
    APIKey,
    Document,
    EventJournalEntry,
    GraphOwnership,
    NodeStorage,
    PayloadStorage,
    UsageEvent,
    User,
)
from faim.api.auth.email import generate_verification_token, send_verification_email

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Control Plane"])
ph = PasswordHasher()


# --- Schemas ---


class GraphOut(BaseModel):
    graph_id: str
    name: str
    status: str


class CreateGraphSchema(BaseModel):
    name: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_id: Optional[str] = None  # e.g., "avatar_01", "avatar_02", etc.
    # Email is NOT editable - it's the primary identity


class DeleteAccountRequest(BaseModel):
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


# --- Helper Functions ---


def generate_avatar_url(email: str, name: str) -> str:
    """Generate avatar URL using Gravatar or initials fallback."""
    # Try Gravatar first
    email_hash = hashlib.md5(email.lower().strip().encode()).hexdigest()

    # Generate initials for fallback
    initials = "".join([part[0].upper() for part in (name or email.split("@")[0]).split()[:2]])
    if len(initials) == 0:
        initials = email[0].upper() if email else "U"

    # Use ui-avatars.com as fallback (generates nice initials avatars)
    fallback_url = f"https://ui-avatars.com/api/?name={initials}&background=0ea5e9&color=fff&size=128&bold=true"

    # Gravatar with fallback
    return f"https://www.gravatar.com/avatar/{email_hash}?d={fallback_url}&s=128"


# --- Endpoints ---


@router.get("/v1/me")
def get_me(current_user: User = Depends(get_current_user_oidc), db: Session = Depends(get_db)):
    """Get current user info with all profile details."""
    graph = db.query(GraphOwnership).filter(GraphOwnership.user_id == current_user.id).first()

    if not graph:
        graph_id = f"U:{uuid.uuid4().hex[:8]}"
        graph = GraphOwnership(graph_id=graph_id, user_id=current_user.id, name="My Universe")
        db.add(graph)
        db.commit()
        db.refresh(graph)

    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.full_name,
        "status": current_user.status,
        "graph_id": graph.graph_id,
        # Profile fields
        "avatar_id": current_user.avatar_id or "avatar_01",
        "avatar_url": generate_avatar_url(current_user.email or "", current_user.full_name or ""),
        "email_verified": current_user.email_verified or False,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }


@router.patch("/v1/me")
def update_me(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """Update current user's profile (name and avatar - email is not editable)."""
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name

    if update_data.avatar_id is not None:
        # Validate avatar_id format
        valid_avatars = [f"avatar_{str(i).zfill(2)}" for i in range(1, 25)]
        if update_data.avatar_id in valid_avatars:
            current_user.avatar_id = update_data.avatar_id

    db.commit()
    db.refresh(current_user)

    return {
        "status": "updated",
        "user": {
            "name": current_user.full_name,
            "email": current_user.email,
            "id": str(current_user.id),
            "avatar_id": current_user.avatar_id,
        },
    }


@router.post("/v1/me/password")
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """Change user's password."""
    # Check current password
    if not current_user.password_hash:
        raise HTTPException(status_code=400, detail="Account has no password set")

    try:
        ph.verify(current_user.password_hash, request.current_password)
    except VerifyMismatchError:
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    # Check new password matches confirm
    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")

    # Check new password is different from current
    if request.new_password == request.current_password:
        raise HTTPException(status_code=400, detail="New password must be different from current password")

    # Update password
    current_user.password_hash = ph.hash(request.new_password)
    db.commit()

    logger.info(f"Password changed for user {current_user.email}")

    return {"status": "success", "message": "Password changed successfully"}


@router.post("/v1/me/resend-verification")
async def resend_verification_email(
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """Resend email verification link."""
    if current_user.email_verified:
        return {"status": "already_verified", "message": "Email is already verified"}

    # Generate new token
    token = generate_verification_token()
    expires = datetime.datetime.utcnow() + datetime.timedelta(hours=24)

    current_user.email_verification_token = token
    current_user.email_verification_expires = expires
    db.commit()

    # Send email
    try:
        await send_verification_email(current_user.email, token, current_user.full_name)
        return {"status": "sent", "message": "Verification email sent"}
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send verification email")


@router.delete("/v1/me")
def delete_me(
    request: DeleteAccountRequest,
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """Delete user account permanently."""
    if not current_user.password_hash:
        raise HTTPException(status_code=400, detail="Account has no password set")

    try:
        ph.verify(current_user.password_hash, request.password)
    except VerifyMismatchError:
        raise HTTPException(status_code=401, detail="Invalid password")

    user_id = current_user.id
    user_email = current_user.email
    logger.warning(f"ACCOUNT DELETION: Starting deletion for user {user_email} ({user_id})")

    try:
        graphs = db.query(GraphOwnership).filter(GraphOwnership.user_id == user_id).all()
        graph_ids = [g.graph_id for g in graphs]

        for graph_id in graph_ids:
            db.query(NodeStorage).filter(NodeStorage.graph_id == graph_id).delete()
            db.query(PayloadStorage).filter(PayloadStorage.graph_id == graph_id).delete()
            db.query(EventJournalEntry).filter(EventJournalEntry.graph_id == graph_id).delete()

        db.query(GraphOwnership).filter(GraphOwnership.user_id == user_id).delete()
        db.query(Document).filter(Document.user_id == user_id).delete()
        db.query(APIKey).filter(APIKey.user_id == user_id).delete()
        db.query(UsageEvent).filter(UsageEvent.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()

        db.commit()
        logger.warning(f"ACCOUNT DELETION: Completed for user {user_email}")

        return {"status": "deleted", "message": "Your account and all data have been permanently deleted."}

    except Exception as e:
        db.rollback()
        logger.error(f"ACCOUNT DELETION FAILED: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete account. Please try again.")


@router.get("/v1/graphs", response_model=List[GraphOut])
def list_my_graphs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_oidc)):
    """List all graphs owned by current user."""
    graphs = db.query(GraphOwnership).filter(GraphOwnership.user_id == current_user.id).all()
    return [{"graph_id": g.graph_id, "name": g.name or "Unnamed", "status": g.status} for g in graphs]


@router.post("/v1/graphs", response_model=GraphOut)
def create_graph(
    data: CreateGraphSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_oidc),
):
    """Create a new graph for current user."""
    graph_id = f"U:{uuid.uuid4().hex[:8]}"
    graph = GraphOwnership(graph_id=graph_id, user_id=current_user.id, name=data.name)
    db.add(graph)
    db.commit()
    db.refresh(graph)

    return {"graph_id": graph.graph_id, "name": graph.name, "status": graph.status}
