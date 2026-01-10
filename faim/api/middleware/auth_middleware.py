"""
FAIM Auth Middleware - Simplified (User → Graph Direct)

Provides:
- verify_db_api_key: Validates sk_live_... API keys
- get_current_user_oidc: Gets/creates User from JWT token
- verify_graph_access: Ensures user has access to a graph
"""

import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from faim.api.auth.jwt_auth import get_current_user, verify_jwt
from faim.config.database import get_db
from faim.config.models import APIKey, GraphOwnership, User

security = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-FAIM-KEY", auto_error=False)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


async def verify_db_api_key(
    request: Request, key: str = Security(api_key_header), db: Session = Depends(get_db)
) -> Optional[APIKey]:
    """Verifies a Database-backed API Key (sk_live_...)."""
    if not key:
        return None

    if not key.startswith("sk_live_"):
        return None

    prefix = key[:12]
    candidates = db.query(APIKey).filter(APIKey.key_prefix == prefix, APIKey.status == "active").all()

    for candidate in candidates:
        if pwd_context.verify(key, candidate.key_hash):
            return candidate

    raise HTTPException(status_code=401, detail="Invalid API Key")


async def get_current_user_oidc(token_payload: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    """Gets or creates User from JWT claims. Simplified: no Org/Project provisioning."""
    email = token_payload.get("email")
    sub = token_payload.get("sub") or token_payload.get("id") or str(uuid.uuid4())
    name = token_payload.get("name") or (email.split("@")[0] if email else "User")

    if not email:
        if not sub:
            raise HTTPException(status_code=401, detail="Token missing identity claims")
        user = db.query(User).filter(User.keycloak_sub == sub).first()
    else:
        user = db.query(User).filter(User.email == email).first()

    if not user:
        # JIT Provisioning: Create user only (graph created on first /v1/me call)
        user = User(keycloak_sub=sub, email=email, full_name=name)
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


async def verify_graph_access(
    request: Request,
    db: Session = Depends(get_db),
    current_key: Optional[APIKey] = Depends(verify_db_api_key),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> bool:
    """Ensures caller has access to the requested graph_id."""
    graph_id = request.path_params.get("graph_id")
    if not graph_id:
        return True

    # Case A: API Key
    if current_key:
        # Check if key's user owns this graph
        count = (
            db.query(GraphOwnership)
            .filter(GraphOwnership.graph_id == graph_id)
            .filter(GraphOwnership.user_id == current_key.user_id)
            .count()
        )
        if count == 0:
            raise HTTPException(status_code=403, detail="API Key does not have access to this graph")
        return True

    # Case B: User Token
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        token = credentials.credentials
        payload = verify_jwt(token)
        sub = payload.get("sub") or payload.get("id")
        email = payload.get("email")

        if email:
            user = db.query(User).filter(User.email == email).first()
        elif sub:
            user = db.query(User).filter(User.keycloak_sub == sub).first()
        else:
            raise HTTPException(status_code=401, detail="Token missing identity")

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Check if user owns this graph
        count = (
            db.query(GraphOwnership)
            .filter(GraphOwnership.graph_id == graph_id)
            .filter(GraphOwnership.user_id == user.id)
            .count()
        )
        if count == 0:
            raise HTTPException(status_code=403, detail=f"Access denied to graph {graph_id}")
        return True

    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
