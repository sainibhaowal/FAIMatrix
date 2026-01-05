import os
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from faim.api.auth_middleware import get_current_user_oidc
from faim.db import get_db
from faim.models_sql import GraphOwnership, Org, OrgMember, Project, User

router = APIRouter(tags=["Control Plane"])


# --- Dev Mode Check ---
def is_dev_mode() -> bool:
    mode = os.getenv("FAIM_MODE", "dev").strip().lower()
    return mode in ("dev", "development", "local", "core_dev")


def get_current_user_dev(db: Session = Depends(get_db)):
    """Returns the actual dev user from DB in dev mode, raises 401 otherwise."""
    if is_dev_mode():
        # Use the same dev user that get_current_user_oidc creates
        user = db.query(User).filter(User.keycloak_sub == "dev_user_sub").first()
        if user:
            return user

        # Fallback: Try legacy dev@localhost email
        user = db.query(User).filter(User.email == "dev@localhost").first()
        if user:
            return user

        # Create the dev user if it doesn't exist (JIT provisioning)
        # This mimics get_current_user_oidc behavior
        user = User(
            keycloak_sub="dev_user_sub", email="dev@faim.ai", full_name="Dev User", status="active"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create default org for dev user
        org = Org(name="Dev User's Workspace", owner_user_id=user.id)
        db.add(org)
        db.commit()
        db.refresh(org)

        # Add org membership
        member = OrgMember(org_id=org.id, user_id=user.id, role="owner")
        db.add(member)
        db.commit()

        # Create default project
        project = Project(org_id=org.id, name="Dev User's Project")
        db.add(project)
        db.commit()
        db.refresh(project)

        # Create default graph
        graph = GraphOwnership(
            graph_id=f"U:{uuid.uuid4()}", project_id=project.id, name="My Universe"
        )
        db.add(graph)
        db.commit()

        return user
    raise HTTPException(status_code=401, detail="Not authenticated")


# --- Schemas ---


class OrgOut(BaseModel):
    id: str
    name: str
    role: str


class ProjectOut(BaseModel):
    id: str
    name: str
    plan: str


class GraphOut(BaseModel):
    graph_id: str
    name: str
    status: str


class CreateProjectSchema(BaseModel):
    org_id: str
    name: str


class CreateGraphSchema(BaseModel):
    project_id: str
    name: str
    graph_id: Optional[str] = None  # Optional manual ID mostly for migration/dev


# --- Endpoints ---


@router.get("/v1/me")
def get_me(current_user=Depends(get_current_user_dev)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.full_name,
        "status": current_user.status,
    }


@router.get("/v1/orgs", response_model=List[OrgOut])
def list_my_orgs(db: Session = Depends(get_db), current_user=Depends(get_current_user_dev)):
    try:
        # Join OrgMember to get role
        results = (
            db.query(Org, OrgMember.role)
            .join(OrgMember, Org.id == OrgMember.org_id)
            .filter(OrgMember.user_id == current_user.id)
            .all()
        )
        return [{"id": str(org.id), "name": org.name, "role": role} for org, role in results]
    except Exception:
        return []


@router.get("/v1/projects", response_model=List[ProjectOut])
def list_projects(
    org_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_dev),
):
    try:
        # Verify membership in org if provided
        query = db.query(Project).join(Org).join(OrgMember)
        query = query.filter(OrgMember.user_id == current_user.id)

        if org_id:
            query = query.filter(Project.org_id == org_id)

        projects = query.all()
        return [{"id": str(p.id), "name": p.name, "plan": p.plan} for p in projects]
    except Exception:
        return []


@router.post("/v1/projects", response_model=ProjectOut)
def create_project(
    payload: CreateProjectSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_oidc),
):
    # Verify User is Admin/Owner of Org
    member = (
        db.query(OrgMember)
        .filter(OrgMember.org_id == payload.org_id)
        .filter(OrgMember.user_id == current_user.id)
        .filter(OrgMember.role.in_(["owner", "admin"]))
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to create projects in this organization",
        )

    project = Project(org_id=payload.org_id, name=payload.name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"id": str(project.id), "name": project.name, "plan": project.plan}


@router.get("/v1/projects/{project_id}/graphs", response_model=List[GraphOut])
def list_graphs(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_oidc),
):
    # Verify access to project
    # Naive check: does user belong to org that owns project?
    # Better: Project -> Org -> Member(user)
    has_access = (
        db.query(Project)
        .join(Org)
        .join(OrgMember)
        .filter(Project.id == project_id)
        .filter(OrgMember.user_id == current_user.id)
        .count()
    )
    if not has_access:
        raise HTTPException(status_code=404, detail="Project not found or access denied")

    graphs = db.query(GraphOwnership).filter(GraphOwnership.project_id == project_id).all()
    return [{"graph_id": g.graph_id, "name": g.name or "", "status": g.status} for g in graphs]


@router.post("/v1/projects/{project_id}/graphs", response_model=GraphOut)
def create_graph(
    project_id: str,
    payload: CreateGraphSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_oidc),
):
    # Verify write access
    has_access = (
        db.query(Project)
        .join(Org)
        .join(OrgMember)
        .filter(Project.id == project_id)
        .filter(OrgMember.user_id == current_user.id)
        .count()
    )
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check Quota
    from faim.api.quotas import check_quota

    check_quota(db, str(project_id), "graphs")

    # Generate graph ID if not provided. Standard FAIM format: G:<uuid>
    graph_id = payload.graph_id or f"G:{uuid.uuid4().hex[:16]}"

    # Check if exists
    exists = db.query(GraphOwnership).filter(GraphOwnership.graph_id == graph_id).first()
    if exists:
        raise HTTPException(status_code=409, detail="Graph ID already exists")

    g = GraphOwnership(graph_id=graph_id, project_id=project_id, name=payload.name)
    db.add(g)
    db.commit()
    return {"graph_id": graph_id, "name": g.name, "status": g.status}
