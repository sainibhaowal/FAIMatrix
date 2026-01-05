import os
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jose.exceptions import JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from faim.db import get_db
from faim.models_sql import APIKey, GraphOwnership, Org, OrgMember, Project, User

# Configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "faim-lab")
# In a real setup, you might fetch JWKS from:
# {KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs
# For now, we'll assume we can decode if we have the public key or just verify signature if we fetch certs dynamically.
# Simpler for this phase: verify audience and issuer if possible, or just decode loosely if behind a gateway.
# We will implementing a robust remote JWKS check or accept a fixed public key.
# For simplicity in this blueprint, we'll assume standard OIDC JWT validation.

security = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-FAIM-KEY", auto_error=False)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


async def verify_db_api_key(
    request: Request, key: str = Security(api_key_header), db: Session = Depends(get_db)
) -> APIKey:
    """
    Verifies a Database-backed API Key (sk_live_...).
    Returns the APIKey object if valid.
    """
    if not key:
        return None  # Allow falling back to User Auth if key missing

    # 1. Check format
    if not key.startswith("sk_live_"):
        return None  # Not a V2 key

    # 2. Extract prefix to optimize lookup
    prefix = key[:12]

    # 3. Lookup candidates
    candidates = db.query(APIKey).filter(APIKey.key_prefix == prefix, APIKey.status == "active").all()

    # 4. Verify Hash (Argon2)
    for candidate in candidates:
        if pwd_context.verify(key, candidate.key_hash):
            return candidate

    # If key was provided but invalid -> 401
    raise HTTPException(status_code=401, detail="Invalid API Key")


def _is_dev_mode() -> bool:
    """Always return False - production mode only."""
    return False


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Verifies the JWT token from Keycloak.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    token = credentials.credentials
    try:
        # 1. Fetch JWKS (Cached in production) - Mocked logic for now or "unverified" if no key provided yet
        # options={"verify_signature": False} used ONLY if we trust the gateway or for dev speed.
        # Ideally:
        # jwks = requests.get(f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs").json()
        # key = find_key(jwks, token_header)
        # payload = jwt.decode(token, key, algorithms=["RS256"], audience="account", issuer=...)

        # For this implementation phase, we will decode unverified to extract 'sub'
        # but in production you MUST verify signature.
        # TODO: Add signature verification.
        payload = jwt.get_unverified_claims(token)
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Could not validate credentials: {str(e)}")


async def get_current_user_oidc(token_payload: dict = Depends(verify_token), db: Session = Depends(get_db)) -> User:
    """
    Gets or creates the User based on Keycloak 'sub'.
    """
    sub = token_payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim")

    email = token_payload.get("email")
    name = token_payload.get("name") or token_payload.get("preferred_username")

    user = db.query(User).filter(User.keycloak_sub == sub).first()
    if not user:
        # JIT Provisioning
        user = User(keycloak_sub=sub, email=email, full_name=name)
        db.add(user)
        db.commit()
        db.refresh(user)

        # Auto-create personal Org
        org_name = f"{name}'s Workspace" if name else "Personal Workspace"
        org = Org(name=org_name, owner_user_id=user.id)
        db.add(org)
        db.commit()
        db.refresh(org)

        # Add to org members
        member = OrgMember(org_id=org.id, user_id=user.id, role="owner")
        db.add(member)
        db.commit()

        # Create Project
        project = Project(org_id=org.id, name=f"{name}'s Project")
        db.add(project)
        db.commit()
        db.refresh(project)

        # Create Graph
        graph_id = f"U:{uuid.uuid4()}"
        graph = GraphOwnership(graph_id=graph_id, project_id=project.id, name="My Universe")
        db.add(graph)
        db.commit()

    return user


async def verify_graph_access(
    request: Request,
    db: Session = Depends(get_db),
    # Both are optional dependencies now; at least one must pass
    current_key: Optional[APIKey] = Depends(verify_db_api_key),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> bool:
    """
    Ensures the caller has access to the requested graph_id.
    Caller can be:
      A) User (via Bearer Token)
      B) Machine (via API Key)
    """
    graph_id = request.path_params.get("graph_id")
    if not graph_id:
        return True

    # --- CASE A: API Key ---
    if current_key:
        # 1. Check Scope (simplistic check for now)
        # e.g. "graph:read" vs "graph:write"
        # We assume if key exists, it has basic access. Fine-grained checks happen inside endpoints if needed.

        # 2. Check Ownership: Key -> Project -> Graph
        # We need to verify if the graph belongs to the key's project.
        # Note: keys are bound to a PROJECT, not a specific graph (usually).
        # So we check if Graph.project_id == Key.project_id

        count = (
            db.query(GraphOwnership)
            .filter(GraphOwnership.graph_id == graph_id)
            .filter(GraphOwnership.project_id == current_key.project_id)
            .count()
        )
        if count == 0:
            raise HTTPException(status_code=403, detail="API Key does not have access to this graph")
        return True

    # --- CASE B: User Token ---
    # We manually call verify_token logic here because we made it optional/alternative to key
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required (Bearer or X-FAIM-KEY)")

    # Manually resolve user
    # Note: We duplicate get_current_user_oidc logic bits here or refactor.
    # Refactoring verify_graph_access to compose dependencies is cleaner.
    # But for "One OR The Other", manual verification is robust.

    try:
        token = credentials.credentials
        # In prod: verify signature. Dev: unverified claims to get sub.
        payload = jwt.get_unverified_claims(token)
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401)

        user = db.query(User).filter(User.keycloak_sub == sub).first()
        if not user:
            # JIT create logic duplicates...
            # For robustness, we assume user usually exists or we rely on the main middleware.
            # Let's rely on valid user check:
            raise HTTPException(status_code=401, detail="User not found")

        # Check User Ownership
        count = (
            db.query(GraphOwnership)
            .join(Project, GraphOwnership.project_id == Project.id)
            .join(Org, Project.org_id == Org.id)
            .join(OrgMember, Org.id == OrgMember.org_id)
            .filter(GraphOwnership.graph_id == graph_id)
            .filter(OrgMember.user_id == user.id)
            .count()
        )
        if count == 0:
            raise HTTPException(status_code=403, detail=f"Access denied to graph {graph_id}")
        return True

    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
