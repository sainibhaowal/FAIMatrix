from fastapi import HTTPException
from sqlalchemy.orm import Session
from faim.models_sql import Project, GraphOwnership, Document

# Default Limits
LIMITS = {
    "free": {"graphs": 1, "storage_mb": 100},
    "pro": {"graphs": 10, "storage_mb": 10240},
    "enterprise": {"graphs": 9999, "storage_mb": 9999999},
}

def check_quota(db: Session, project_id: str, resource: str):
    """
    Checks if a project has remaining quota for a resource.
    Resource: 'graphs' | 'storage_mb'
    Raises 402 Payment Required if exceeded.
    """
    project = db.query(Project).get(project_id)
    if not project:
        # Should not happen if auth checked
        raise HTTPException(status_code=404, detail="Project not found")
    
    # 1. Determine Limits (DB Override > Plan Default)
    plan = project.plan or "free"
    defaults = LIMITS.get(plan, LIMITS["free"])
    
    # Merge db-stored limits if any
    custom_limits = project.plan_limits or {}
    limit = custom_limits.get(resource, defaults.get(resource, 0))
    
    # 2. Measure Usage
    usage = 0
    if resource == "graphs":
        usage = db.query(GraphOwnership).filter(
            GraphOwnership.project_id == project_id, 
            GraphOwnership.status == "active"
        ).count()
    elif resource == "storage_mb":
        # Sum file sizes
        # SQL Sum would be better but keeping simple
        docs = db.query(Document).filter(Document.project_id == project_id).all()
        total_bytes = sum(d.file_size_bytes for d in docs)
        usage = total_bytes / (1024 * 1024)
    
    if usage >= limit:
        raise HTTPException(
            status_code=402, # Payment Required
            detail=f"Quota exceeded for {resource}. Current: {int(usage)}, Limit: {limit}. Upgrade plan."
        )
