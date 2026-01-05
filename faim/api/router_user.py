"""
FAIM User Router - Current User Info and Auto-Setup

NEW MODULE - Provides /api/v1/me endpoint for user info.
Auto-creates Project and Graph on first access.

Usage:
    GET /api/v1/me  - Returns current user with project_id and graph_id
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from faim.db import get_db
from faim.models_sql import GraphOwnership, Org, OrgMember, Project, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me", tags=["User"])


# =============================================================================
# Schemas
# =============================================================================


class UserInfo(BaseModel):
    """User information response."""

    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    project_id: str
    graph_id: str
    org_id: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================


def ensure_user_has_project(user: User, db: Session) -> tuple[str, str]:
    """
    Ensure user has a default project and graph.

    Returns (project_id, graph_id).
    """
    # Find user's org
    membership = db.query(OrgMember).filter(OrgMember.user_id == user.id).first()

    if not membership:
        # Create personal org
        org = Org(
            name=f"{user.full_name or user.email or 'User'}'s Workspace",
            owner_user_id=user.id,
        )
        db.add(org)
        db.commit()
        db.refresh(org)

        membership = OrgMember(
            org_id=org.id,
            user_id=user.id,
            role="owner",
        )
        db.add(membership)
        db.commit()

    org_id = membership.org_id

    # Find or create project
    project = db.query(Project).filter(Project.org_id == org_id).first()

    if not project:
        project = Project(
            org_id=org_id,
            name="My FAIM Project",
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        logger.info(f"Created default project {project.id} for user {user.id}")

    # Find or create graph
    graph = db.query(GraphOwnership).filter(GraphOwnership.project_id == project.id).first()

    if not graph:
        # Generate U: ID
        short_id = str(uuid.uuid4())[:8]
        graph_id = f"U:{short_id}"

        graph = GraphOwnership(
            graph_id=graph_id,
            project_id=project.id,
            name="My Universe",
        )
        db.add(graph)
        db.commit()
        db.refresh(graph)
        logger.info(f"Created default graph {graph_id} for project {project.id}")

    return str(project.id), graph.graph_id


# =============================================================================
# API Endpoints
# =============================================================================


@router.get("")
async def get_current_user_info(db: Session = Depends(get_db)):
    """
    Get current user information.

    Returns user info with project_id and graph_id.
    In dev mode, returns a default user.

    Example:
        curl http://localhost:8000/api/v1/me -H "Authorization: Bearer <token>"
    """
    from faim.api.auth import _is_dev_mode

    if _is_dev_mode():
        # Dev mode: return default user info
        # Use the SAME dev user identity as auth_middleware.py and router_control.py
        dev_user = db.query(User).filter(User.keycloak_sub == "dev_user_sub").first()

        if not dev_user:
            dev_user = User(
                keycloak_sub="dev_user_sub",
                email="dev@faim.ai",
                full_name="Dev User",
            )
            db.add(dev_user)
            db.commit()
            db.refresh(dev_user)

        project_id, graph_id = ensure_user_has_project(dev_user, db)

        return UserInfo(
            user_id=str(dev_user.id),
            email=dev_user.email,
            name=dev_user.full_name,
            project_id=project_id,
            graph_id=graph_id,
        )

    # Production: get user from auth
    # This would be populated by auth middleware
    raise HTTPException(
        status_code=401, detail="Authentication required. Use bearer token or enable dev mode."
    )


@router.post("/setup")
async def setup_user_resources(db: Session = Depends(get_db)):
    """
    Explicitly set up user resources (project, graph).

    Called after first login to ensure resources exist.
    """
    from faim.api.auth import _is_dev_mode

    if _is_dev_mode():
        # Use the SAME dev user identity as /me endpoint
        dev_user = db.query(User).filter(User.keycloak_sub == "dev_user_sub").first()

        if not dev_user:
            dev_user = User(
                keycloak_sub="dev_user_sub",
                email="dev@faim.ai",
                full_name="Dev User",
            )
            db.add(dev_user)
            db.commit()
            db.refresh(dev_user)

        project_id, graph_id = ensure_user_has_project(dev_user, db)

        return {
            "success": True,
            "user_id": str(dev_user.id),
            "project_id": project_id,
            "graph_id": graph_id,
            "message": "User resources created/verified",
        }

    raise HTTPException(status_code=401, detail="Authentication required")
