"""
FAIM User Router - Simplified (User → Graph Direct)

Provides /api/v1/me endpoint for user info.
Auto-creates Graph on first access.
"""

import logging
import uuid
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from faim.api.auth.jwt_auth import get_current_user
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me", tags=["User"])

ph = PasswordHasher()


# --- Schemas ---


class UserInfo(BaseModel):
    """User information response."""

    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    graph_id: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None


class DeleteAccountRequest(BaseModel):
    """Request to delete account (requires password confirmation)."""

    password: str


# --- Helper ---


def ensure_user_has_graph(user: User, db: Session) -> str:
    """Ensure user has a default graph. Returns graph_id."""
    graph = db.query(GraphOwnership).filter(GraphOwnership.user_id == user.id).first()

    if not graph:
        graph_id = f"U:{uuid.uuid4().hex[:8]}"
        graph = GraphOwnership(graph_id=graph_id, user_id=user.id, name="My Universe")
        db.add(graph)
        db.commit()
        db.refresh(graph)
        logger.info(f"Created graph {graph_id} for user {user.id}")

    return graph.graph_id


# --- Endpoints ---


@router.get("")
async def get_current_user_info(
    db: Session = Depends(get_db),
    user_data: dict = Depends(get_current_user),
):
    """Get current user information."""
    email = user_data.get("email")
    sub = user_data.get("sub") or user_data.get("id")

    if not email:
        raise HTTPException(status_code=400, detail="Token missing email claim")

    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Auto-create user
        user = User(
            keycloak_sub=sub or str(uuid.uuid4()),
            email=email,
            full_name=user_data.get("name") or "New User",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    graph_id = ensure_user_has_graph(user, db)

    return UserInfo(
        user_id=str(user.id),
        email=user.email,
        name=user.full_name,
        graph_id=graph_id,
    )


@router.post("/setup")
async def setup_user_resources(
    db: Session = Depends(get_db),
    user_data: dict = Depends(get_current_user),
):
    """Explicitly set up user resources."""
    return await get_current_user_info(db, user_data)


@router.patch("")
async def update_user_profile(
    update_data: UserUpdate,
    db: Session = Depends(get_db),
    user_data: dict = Depends(get_current_user),
):
    """Update my profile (Name, Email)."""
    email = user_data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Token missing email claim")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if update_data.full_name is not None:
        user.full_name = update_data.full_name

    if update_data.email is not None:
        user.email = update_data.email

    db.commit()
    db.refresh(user)

    return {"status": "updated", "user": {"name": user.full_name, "email": user.email, "id": str(user.id)}}


@router.delete("")
async def delete_account(
    request: DeleteAccountRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(get_current_user),
):
    """
    Delete user account permanently.

    Requires password confirmation.
    Deletes ALL user data: graphs, nodes, payloads, documents, API keys, usage events.
    This action is IRREVERSIBLE.
    """
    email = user_data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Token missing email claim")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify password
    if not user.password_hash:
        raise HTTPException(status_code=400, detail="Account has no password set")

    try:
        ph.verify(user.password_hash, request.password)
    except VerifyMismatchError:
        raise HTTPException(status_code=401, detail="Invalid password")

    user_id = user.id
    logger.warning(f"ACCOUNT DELETION: Starting deletion for user {user.email} ({user_id})")

    try:
        # Get user's graphs
        graphs = db.query(GraphOwnership).filter(GraphOwnership.user_id == user_id).all()
        graph_ids = [g.graph_id for g in graphs]

        # Delete in order (respecting foreign keys):
        # 1. Nodes and payloads (reference graphs)
        for graph_id in graph_ids:
            db.query(NodeStorage).filter(NodeStorage.graph_id == graph_id).delete()
            db.query(PayloadStorage).filter(PayloadStorage.graph_id == graph_id).delete()
            db.query(EventJournalEntry).filter(EventJournalEntry.graph_id == graph_id).delete()

        # 2. Graphs
        db.query(GraphOwnership).filter(GraphOwnership.user_id == user_id).delete()

        # 3. Documents
        db.query(Document).filter(Document.user_id == user_id).delete()

        # 4. API Keys
        db.query(APIKey).filter(APIKey.user_id == user_id).delete()

        # 5. Usage Events
        db.query(UsageEvent).filter(UsageEvent.user_id == user_id).delete()

        # 6. Finally, delete the user
        db.query(User).filter(User.id == user_id).delete()

        db.commit()

        logger.warning(f"ACCOUNT DELETION: Completed for user {email}")

        return {
            "status": "deleted",
            "message": "Your account and all data have been permanently deleted.",
        }

    except Exception as e:
        db.rollback()
        logger.error(f"ACCOUNT DELETION FAILED: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete account. Please try again.")
