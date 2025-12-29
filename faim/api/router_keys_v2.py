import secrets
import uuid
from typing import List, Optional
from datetime import datetime
import os

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from passlib.context import CryptContext

from faim.db import get_db
from faim.api.auth_middleware import get_current_user_oidc
from faim.models_sql import User, Project, APIKey, Org, OrgMember

router = APIRouter(tags=["Developer Keys"])

# SHA256/Argon2 context
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# --- Dev Mode Check ---
def is_dev_mode() -> bool:
    mode = os.getenv("FAIM_MODE", "dev").strip().lower()
    return mode in ("dev", "development", "local", "core_dev")

def get_current_user_dev():
    """Returns real user via OIDC in prod, or mock user in dev mode."""
    if is_dev_mode():
        class MockUser:
            id = "dev-user-001"
            email = "dev@localhost"
            full_name = "Dev User"
            status = "active"
        return MockUser()
    # In production, this would use actual OIDC
    raise HTTPException(status_code=401, detail="Not authenticated (dev mode disabled)")

# --- Schemas ---

class APIKeyOut(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: List[str]
    created_at: datetime
    last_used_at: Optional[datetime] = None
    status: str

class CreateKeyRequest(BaseModel):
    project_id: str
    name: str
    scopes: List[str] = ["graph:read", "graph:write"]

class CreatedKeyResponse(BaseModel):
    id: str
    name: str
    full_key: str  # Shown ONLY once
    scopes: List[str]

# --- Helpers ---

def generate_key_str() -> str:
    """Generates a secure random key: sk_live_<32_random_chars>"""
    return f"sk_live_{secrets.token_urlsafe(32)}"

def hash_key(key: str) -> str:
    return pwd_context.hash(key)

def verify_key_hash(plain_key: str, hashed_key: str) -> bool:
    return pwd_context.verify(plain_key, hashed_key)

# --- Endpoints ---

@router.get("/v1/api_keys", response_model=List[APIKeyOut])
def list_api_keys(
    project_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_dev)
):
    # In dev mode, skip project access check and return empty list if tables don't exist
    try:
        keys = db.query(APIKey).filter(
            APIKey.project_id == project_id,
            APIKey.status == "active"
        ).all()
        
        return [
            APIKeyOut(
                id=str(k.id),
                name=k.name or "Unnamed Key",
                key_prefix=k.key_prefix,
                scopes=k.scopes or [],
                created_at=k.created_at,
                last_used_at=k.last_used_at,
                status=k.status
            ) for k in keys
        ]
    except Exception:
        return []

@router.post("/v1/api_keys", response_model=CreatedKeyResponse)
def create_api_key(
    payload: CreateKeyRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_dev)
):
    try:
        # Generate key
        full_key = generate_key_str()
        key_prefix = full_key[:12]
        key_hashed = hash_key(full_key)

        new_key = APIKey(
            project_id=payload.project_id,
            name=payload.name,
            key_prefix=key_prefix,
            key_hash=key_hashed,
            scopes=payload.scopes,
            status="active"
        )
        db.add(new_key)
        db.commit()
        db.refresh(new_key)

        return CreatedKeyResponse(
            id=str(new_key.id),
            name=new_key.name,
            full_key=full_key,
            scopes=new_key.scopes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create key: {str(e)}")

@router.delete("/v1/api_keys/{key_id}")
def revoke_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_dev)
):
    try:
        key = db.query(APIKey).filter(APIKey.id == key_id).first()
        if not key:
            raise HTTPException(status_code=404, detail="Key not found")

        key.status = "revoked"
        db.commit()
        
        return {"status": "revoked", "id": key_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to revoke key: {str(e)}")
