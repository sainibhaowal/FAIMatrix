"""
FAIM Tenant Control Plane API

Provides endpoints for multi-tenant management:
- /me - Current user profile
- /orgs - Organization management
- /projects - Project management
- /projects/{id}/graphs - Graph ownership management
"""
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from faim.db import SessionLocal
from faim.models_sql import User, Org, OrgMember, Project, GraphOwnership
from faim.api.jwt_auth import get_current_user, get_user_sub
from faim.api.rate_limiter import user_rate_limit

router = APIRouter(prefix="/tenant", tags=["Tenant"])


# ============================================================================
# Pydantic Models
# ============================================================================

class UserProfile(BaseModel):
    id: str
    email: Optional[str]
    full_name: Optional[str]
    created_at: datetime
    status: str

    class Config:
        from_attributes = True


class OrgCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class OrgOut(BaseModel):
    id: str
    name: str
    owner_user_id: str
    created_at: datetime
    role: Optional[str] = None  # User's role in this org

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    org_id: str


class ProjectOut(BaseModel):
    id: str
    org_id: str
    name: str
    plan: str
    created_at: datetime

    class Config:
        from_attributes = True


class GraphCreate(BaseModel):
    name: Optional[str] = None


class GraphOut(BaseModel):
    graph_id: str
    project_id: str
    name: Optional[str]
    created_at: datetime
    status: str

    class Config:
        from_attributes = True


# ============================================================================
# Helper Functions
# ============================================================================

def get_or_create_user(db, keycloak_sub: str, email: str = None, name: str = None) -> User:
    """Get existing user or create new one from Keycloak info."""
    user = db.query(User).filter(User.keycloak_sub == keycloak_sub).first()
    if not user:
        user = User(
            keycloak_sub=keycloak_sub,
            email=email,
            full_name=name,
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def ensure_user_in_org(db, user_id: uuid.UUID, org_id: uuid.UUID) -> bool:
    """Check if user is a member of the organization."""
    member = db.query(OrgMember).filter(
        OrgMember.user_id == user_id,
        OrgMember.org_id == org_id,
    ).first()
    return member is not None


def ensure_project_access(db, user_id: uuid.UUID, project_id: uuid.UUID) -> Project:
    """Check if user has access to project (via org membership)."""
    project = (
        db.query(Project)
        .join(OrgMember, OrgMember.org_id == Project.org_id)
        .filter(Project.id == project_id)
        .filter(OrgMember.user_id == user_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=403, detail="Access denied to project")
    return project


# ============================================================================
# Endpoints: User Profile
# ============================================================================

@router.get("/me", response_model=UserProfile)
@user_rate_limit()
async def get_current_user_profile(
    request: Request,
    jwt_payload: dict = Depends(get_current_user),
):
    """Get the current authenticated user's profile."""
    sub = jwt_payload.get("sub")
    email = jwt_payload.get("email")
    name = jwt_payload.get("name") or jwt_payload.get("preferred_username")
    
    db = SessionLocal()
    try:
        user = get_or_create_user(db, sub, email, name)
        return UserProfile(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            created_at=user.created_at,
            status=user.status,
        )
    finally:
        db.close()


# ============================================================================
# Endpoints: Organizations
# ============================================================================

@router.get("/orgs", response_model=List[OrgOut])
@user_rate_limit()
async def list_orgs(
    request: Request,
    jwt_payload: dict = Depends(get_current_user),
):
    """List all organizations the current user belongs to."""
    sub = jwt_payload.get("sub")
    
    db = SessionLocal()
    try:
        user = get_or_create_user(db, sub)
        
        # Get all orgs where user is a member
        memberships = (
            db.query(OrgMember, Org)
            .join(Org, OrgMember.org_id == Org.id)
            .filter(OrgMember.user_id == user.id)
            .all()
        )
        
        return [
            OrgOut(
                id=str(org.id),
                name=org.name,
                owner_user_id=str(org.owner_user_id),
                created_at=org.created_at,
                role=member.role,
            )
            for member, org in memberships
        ]
    finally:
        db.close()


@router.post("/orgs", response_model=OrgOut, status_code=201)
@user_rate_limit()
async def create_org(
    request: Request,
    body: OrgCreate,
    jwt_payload: dict = Depends(get_current_user),
):
    """Create a new organization (user becomes owner)."""
    sub = jwt_payload.get("sub")
    
    db = SessionLocal()
    try:
        user = get_or_create_user(db, sub)
        
        # Create org
        org = Org(
            name=body.name,
            owner_user_id=user.id,
        )
        db.add(org)
        db.flush()
        
        # Add user as owner member
        member = OrgMember(
            org_id=org.id,
            user_id=user.id,
            role="owner",
        )
        db.add(member)
        db.commit()
        db.refresh(org)
        
        return OrgOut(
            id=str(org.id),
            name=org.name,
            owner_user_id=str(org.owner_user_id),
            created_at=org.created_at,
            role="owner",
        )
    finally:
        db.close()


# ============================================================================
# Endpoints: Projects
# ============================================================================

@router.get("/projects", response_model=List[ProjectOut])
@user_rate_limit()
async def list_projects(
    request: Request,
    org_id: Optional[str] = None,
    jwt_payload: dict = Depends(get_current_user),
):
    """List projects accessible to the current user."""
    sub = jwt_payload.get("sub")
    
    db = SessionLocal()
    try:
        user = get_or_create_user(db, sub)
        
        query = (
            db.query(Project)
            .join(OrgMember, OrgMember.org_id == Project.org_id)
            .filter(OrgMember.user_id == user.id)
        )
        
        if org_id:
            query = query.filter(Project.org_id == uuid.UUID(org_id))
        
        projects = query.all()
        
        return [
            ProjectOut(
                id=str(p.id),
                org_id=str(p.org_id),
                name=p.name,
                plan=p.plan,
                created_at=p.created_at,
            )
            for p in projects
        ]
    finally:
        db.close()


@router.post("/projects", response_model=ProjectOut, status_code=201)
@user_rate_limit()
async def create_project(
    request: Request,
    body: ProjectCreate,
    jwt_payload: dict = Depends(get_current_user),
):
    """Create a new project in an organization."""
    sub = jwt_payload.get("sub")
    
    db = SessionLocal()
    try:
        user = get_or_create_user(db, sub)
        org_id = uuid.UUID(body.org_id)
        
        # Verify user is in the org
        if not ensure_user_in_org(db, user.id, org_id):
            raise HTTPException(status_code=403, detail="Not a member of this organization")
        
        # Create project
        project = Project(
            org_id=org_id,
            name=body.name,
            plan="free",
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        
        return ProjectOut(
            id=str(project.id),
            org_id=str(project.org_id),
            name=project.name,
            plan=project.plan,
            created_at=project.created_at,
        )
    finally:
        db.close()


# ============================================================================
# Endpoints: Graphs
# ============================================================================

@router.get("/projects/{project_id}/graphs", response_model=List[GraphOut])
@user_rate_limit()
async def list_project_graphs(
    request: Request,
    project_id: str,
    jwt_payload: dict = Depends(get_current_user),
):
    """List graphs in a project."""
    sub = jwt_payload.get("sub")
    
    db = SessionLocal()
    try:
        user = get_or_create_user(db, sub)
        project = ensure_project_access(db, user.id, uuid.UUID(project_id))
        
        graphs = db.query(GraphOwnership).filter(
            GraphOwnership.project_id == project.id
        ).all()
        
        return [
            GraphOut(
                graph_id=g.graph_id,
                project_id=str(g.project_id),
                name=g.name,
                created_at=g.created_at,
                status=g.status,
            )
            for g in graphs
        ]
    finally:
        db.close()


@router.post("/projects/{project_id}/graphs", response_model=GraphOut, status_code=201)
@user_rate_limit()
async def create_graph(
    request: Request,
    project_id: str,
    body: GraphCreate,
    jwt_payload: dict = Depends(get_current_user),
):
    """Create a new graph in a project (registers ownership)."""
    sub = jwt_payload.get("sub")
    
    db = SessionLocal()
    try:
        user = get_or_create_user(db, sub)
        project = ensure_project_access(db, user.id, uuid.UUID(project_id))
        
        # Generate unique graph ID
        graph_id = f"U:{user.id}:{uuid.uuid4().hex[:8]}"
        
        # Register ownership in database
        graph = GraphOwnership(
            graph_id=graph_id,
            project_id=project.id,
            name=body.name or f"Graph {graph_id[:16]}",
            status="active",
        )
        db.add(graph)
        db.commit()
        db.refresh(graph)
        
        return GraphOut(
            graph_id=graph.graph_id,
            project_id=str(graph.project_id),
            name=graph.name,
            created_at=graph.created_at,
            status=graph.status,
        )
    finally:
        db.close()


@router.delete("/graphs/{graph_id}", status_code=204)
@user_rate_limit()
async def delete_graph(
    request: Request,
    graph_id: str,
    jwt_payload: dict = Depends(get_current_user),
):
    """Delete a graph (soft delete - marks as inactive)."""
    sub = jwt_payload.get("sub")
    
    db = SessionLocal()
    try:
        user = get_or_create_user(db, sub)
        
        # Find graph and verify ownership
        graph = db.query(GraphOwnership).filter(
            GraphOwnership.graph_id == graph_id
        ).first()
        
        if not graph:
            raise HTTPException(status_code=404, detail="Graph not found")
        
        # Verify user has access to the project
        ensure_project_access(db, user.id, graph.project_id)
        
        # Soft delete
        graph.status = "deleted"
        db.commit()
        
        return None
    finally:
        db.close()
