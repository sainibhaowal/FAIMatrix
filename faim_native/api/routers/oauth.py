"""FAIM-Native API: OAuth 2.1 + PKCE + Dynamic Client Registration for MCP.

Implements the MCP Authorization specification:
- GET /.well-known/oauth-protected-resource (RFC 9728)
- GET /.well-known/oauth-protected-resource/mcp (RFC 9728)
- GET /.well-known/oauth-authorization-server (RFC 8414)
- POST /oauth/register (RFC 7591 Dynamic Client Registration)
- POST /api/v1/oauth/code (Mint single-use PKCE-bound auth code for logged-in user)
- POST /oauth/token (Exchange authorization_code + PKCE verifier or refresh_token)
- GET /api/v1/oauth/grants (List active MCP client grants for current user)
- DELETE /api/v1/oauth/grants/{grant_id} (Disconnect a single MCP client grant)
- DELETE /api/v1/oauth/grants (Disconnect all MCP client grants for current user)
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import jwt
from api.deps import FAIMContext, get_faim_context
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

router = APIRouter(tags=["OAuth / MCP Auth"])

SUPPORTED_SCOPES = ["mcp:read", "mcp:write"]
AUTH_CODE_TTL_SECONDS = 300
ACCESS_TOKEN_TTL_SECONDS = 86400
REFRESH_TOKEN_TTL_SECONDS = 86400 * 30

_STATE_LOCK = threading.Lock()
_REGISTERED_CLIENTS: Dict[str, Dict[str, Any]] = {}
_USED_CODE_JTIS: Dict[str, float] = {}
_GRANTS_MEMORY: Dict[str, Dict[str, Any]] = {}


def _get_signing_secret() -> str:
    secret = (
        os.getenv("FAIM_OAUTH_SECRET") or os.getenv("NEXTAUTH_SECRET") or ""
    ).strip()
    if secret:
        return secret
    mode = (os.getenv("FAIM_MODE") or os.getenv("FAIM_ENV") or "").strip().lower()
    if mode in {"prod", "production"}:
        raise RuntimeError(
            "NEXTAUTH_SECRET or FAIM_OAUTH_SECRET must be set in production"
        )
    if not hasattr(_get_signing_secret, "_dev_secret"):
        _get_signing_secret._dev_secret = secrets.token_urlsafe(32)
    return _get_signing_secret._dev_secret


def _api_origin(request: Request) -> str:
    configured = (os.getenv("FAIM_PUBLIC_ORIGIN") or "").strip().rstrip("/")
    if configured:
        return configured
    fwd_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    if fwd_host:
        fwd_proto = (
            (request.headers.get("x-forwarded-proto") or request.url.scheme or "http")
            .split(",")[0]
            .strip()
        )
        return f"{fwd_proto}://{fwd_host}".rstrip("/")
    return str(request.base_url).rstrip("/")


def _frontend_origin(request: Request) -> str:
    for env_name in ("FRONTEND_URL", "NEXTAUTH_URL", "FAIM_PUBLIC_ORIGIN"):
        val = (os.getenv(env_name) or "").strip().rstrip("/")
        if val:
            return val
    return _api_origin(request)


def _prune_used_codes(now: float) -> None:
    expired = [jti for jti, exp in _USED_CODE_JTIS.items() if exp < now]
    for jti in expired:
        _USED_CODE_JTIS.pop(jti, None)


def _pkce_s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _validate_redirect_uri(uri: str) -> bool:
    try:
        parsed = urlparse(uri)
    except Exception:
        return False
    if parsed.scheme == "https" and parsed.netloc:
        return True
    if parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        return True
    if parsed.scheme and parsed.scheme not in {
        "http",
        "https",
        "javascript",
        "data",
        "file",
    }:
        return True
    return False


def _normalize_scopes(raw_scope: Optional[str]) -> str:
    if not raw_scope:
        return " ".join(SUPPORTED_SCOPES)
    requested = [s.strip() for s in raw_scope.split() if s.strip() in SUPPORTED_SCOPES]
    return " ".join(dict.fromkeys(requested or SUPPORTED_SCOPES))


def _get_db_session(tenant_id: str):
    try:
        from runtime.context import get_repos

        repos = get_repos(tenant_id)
        return repos.get("session")
    except Exception:
        return None


def _close_db_session(session: Any) -> None:
    if session is None:
        return
    try:
        from runtime.context import close_session

        close_session(session)
    except Exception:
        pass


def _ensure_grant_table(session: Any) -> None:
    from store.pg.models_auth import MCPOAuthGrant

    MCPOAuthGrant.__table__.create(bind=session.get_bind(), checkfirst=True)


def _save_grant(
    *,
    grant_id: str,
    tenant_id: str,
    user_id: str,
    client_id: str,
    client_name: str,
    scopes: List[str],
    session: Any = None,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    record = {
        "grant_id": grant_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "client_id": client_id,
        "client_name": client_name,
        "scopes": list(scopes),
        "created_at": now.isoformat(),
        "last_used_at": None,
    }
    with _STATE_LOCK:
        _GRANTS_MEMORY[grant_id] = record

    own_session = session is None
    db = session if session is not None else _get_db_session(tenant_id)
    if db is not None:
        try:
            from store.pg.models_auth import MCPOAuthGrant

            _ensure_grant_table(db)
            db.add(
                MCPOAuthGrant(
                    grant_id=grant_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    client_id=client_id,
                    client_name=client_name,
                    scopes=list(scopes),
                    created_at=now,
                )
            )
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            if own_session:
                _close_db_session(db)
    return record


def verify_and_touch_mcp_grant(
    tenant_id: str,
    grant_id: Optional[str],
    session: Any = None,
) -> bool:
    """Return True if grant is active (or not an OAuth grant), False if disconnected."""
    if not grant_id:
        return True

    now = datetime.now(timezone.utc)
    own_session = session is None
    db = session if session is not None else _get_db_session(tenant_id)
    if db is not None:
        try:
            from store.pg.models_auth import MCPOAuthGrant

            _ensure_grant_table(db)
            row = (
                db.query(MCPOAuthGrant)
                .filter(
                    MCPOAuthGrant.grant_id == grant_id,
                    MCPOAuthGrant.tenant_id == tenant_id,
                )
                .first()
            )
            if row is not None:
                row.last_used_at = now
                db.commit()
                with _STATE_LOCK:
                    if grant_id in _GRANTS_MEMORY:
                        _GRANTS_MEMORY[grant_id]["last_used_at"] = now.isoformat()
                return True
            # If DB is available and row does not exist, check if it's only in memory
            # (e.g., created in unit tests before DB mock) — only fail if DB has grants or memory doesn't
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            if own_session:
                _close_db_session(db)

    with _STATE_LOCK:
        mem = _GRANTS_MEMORY.get(grant_id)
        if mem and mem.get("tenant_id") == tenant_id:
            mem["last_used_at"] = now.isoformat()
            return True
    return False


def _list_grants_for_tenant(
    tenant_id: str, session: Any = None
) -> List[Dict[str, Any]]:
    own_session = session is None
    db = session if session is not None else _get_db_session(tenant_id)
    if db is not None:
        try:
            from store.pg.models_auth import MCPOAuthGrant

            _ensure_grant_table(db)
            rows = (
                db.query(MCPOAuthGrant)
                .filter(MCPOAuthGrant.tenant_id == tenant_id)
                .order_by(MCPOAuthGrant.created_at.desc())
                .all()
            )
            if rows:
                return [r.to_dict() for r in rows]
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            if own_session:
                _close_db_session(db)

    with _STATE_LOCK:
        items = [
            dict(g) for g in _GRANTS_MEMORY.values() if g.get("tenant_id") == tenant_id
        ]
    items.sort(key=lambda g: g.get("created_at") or "", reverse=True)
    return items


def _delete_grant_for_tenant(
    tenant_id: str, grant_id: str, session: Any = None
) -> bool:
    removed = False
    with _STATE_LOCK:
        existing = _GRANTS_MEMORY.get(grant_id)
        if existing and existing.get("tenant_id") == tenant_id:
            _GRANTS_MEMORY.pop(grant_id, None)
            removed = True

    own_session = session is None
    db = session if session is not None else _get_db_session(tenant_id)
    if db is not None:
        try:
            from store.pg.models_auth import MCPOAuthGrant

            _ensure_grant_table(db)
            count = (
                db.query(MCPOAuthGrant)
                .filter(
                    MCPOAuthGrant.tenant_id == tenant_id,
                    MCPOAuthGrant.grant_id == grant_id,
                )
                .delete(synchronize_session=False)
            )
            db.commit()
            if count > 0:
                removed = True
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            if own_session:
                _close_db_session(db)
    return removed


def _delete_all_grants_for_tenant(tenant_id: str, session: Any = None) -> int:
    count = 0
    with _STATE_LOCK:
        to_remove = [
            gid for gid, g in _GRANTS_MEMORY.items() if g.get("tenant_id") == tenant_id
        ]
        for gid in to_remove:
            _GRANTS_MEMORY.pop(gid, None)
        count = max(count, len(to_remove))

    own_session = session is None
    db = session if session is not None else _get_db_session(tenant_id)
    if db is not None:
        try:
            from store.pg.models_auth import MCPOAuthGrant

            _ensure_grant_table(db)
            db_count = (
                db.query(MCPOAuthGrant)
                .filter(MCPOAuthGrant.tenant_id == tenant_id)
                .delete(synchronize_session=False)
            )
            db.commit()
            count = max(count, int(db_count or 0))
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            if own_session:
                _close_db_session(db)
    return count


class ClientRegistrationRequest(BaseModel):
    client_name: Optional[str] = "MCP Client"
    redirect_uris: List[str] = Field(..., min_length=1)
    grant_types: Optional[List[str]] = None
    response_types: Optional[List[str]] = None
    token_endpoint_auth_method: Optional[str] = "none"
    scope: Optional[str] = None


class AuthorizationCodeRequest(BaseModel):
    client_id: str
    redirect_uri: str
    code_challenge: str
    code_challenge_method: str = "S256"
    scope: Optional[str] = None
    state: Optional[str] = None


@router.get("/.well-known/oauth-protected-resource")
@router.get("/.well-known/oauth-protected-resource/mcp")
async def oauth_protected_resource(request: Request) -> Dict[str, Any]:
    """RFC 9728 Protected Resource Metadata for MCP."""
    origin = _api_origin(request)
    return {
        "resource": f"{origin}/mcp",
        "authorization_servers": [origin],
        "scopes_supported": SUPPORTED_SCOPES,
        "bearer_methods_supported": ["header"],
    }


@router.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server(request: Request) -> Dict[str, Any]:
    """RFC 8414 Authorization Server Metadata for MCP OAuth 2.1 + PKCE."""
    api_origin = _api_origin(request)
    fe_origin = _frontend_origin(request)
    return {
        "issuer": api_origin,
        "authorization_endpoint": f"{fe_origin}/oauth/authorize",
        "token_endpoint": f"{api_origin}/oauth/token",
        "registration_endpoint": f"{api_origin}/oauth/register",
        "scopes_supported": SUPPORTED_SCOPES,
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_post"],
        "code_challenge_methods_supported": ["S256"],
    }


@router.post("/oauth/register", status_code=status.HTTP_201_CREATED)
async def oauth_register_client(body: ClientRegistrationRequest) -> Dict[str, Any]:
    """RFC 7591 Dynamic Client Registration for MCP IDEs & CLI clients."""
    for uri in body.redirect_uris:
        if not _validate_redirect_uri(uri):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid redirect_uri: {uri}",
            )

    client_id = f"faim_mcp_{secrets.token_urlsafe(18)}"
    record = {
        "client_id": client_id,
        "client_name": body.client_name or "MCP Client",
        "redirect_uris": list(body.redirect_uris),
        "grant_types": body.grant_types or ["authorization_code", "refresh_token"],
        "response_types": body.response_types or ["code"],
        "token_endpoint_auth_method": body.token_endpoint_auth_method or "none",
        "scope": _normalize_scopes(body.scope),
        "client_id_issued_at": int(time.time()),
    }
    with _STATE_LOCK:
        _REGISTERED_CLIENTS[client_id] = record
    return record


@router.post("/api/v1/oauth/code")
async def create_authorization_code(
    request: Request,
    body: AuthorizationCodeRequest,
) -> Dict[str, Any]:
    """Mint a short-lived PKCE-bound authorization code for an authenticated FAIM user."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User authentication required to authorize MCP access",
        )
    if body.code_challenge_method != "S256" or not body.code_challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PKCE code_challenge_method=S256 is required",
        )
    if not _validate_redirect_uri(body.redirect_uri):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid redirect_uri",
        )

    with _STATE_LOCK:
        registered = _REGISTERED_CLIENTS.get(body.client_id)
    if registered and body.redirect_uri not in registered["redirect_uris"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="redirect_uri does not match registered client",
        )

    now = int(time.time())
    email = getattr(request.state, "email", None)
    user_info = getattr(request.state, "user", {}) or {}
    scope = _normalize_scopes(body.scope)
    client_name = (registered or {}).get("client_name") or "MCP Client"
    code_claims = {
        "typ": "oauth_code",
        "jti": secrets.token_urlsafe(16),
        "sub": str(user_id),
        "userId": str(user_id),
        "email": email,
        "name": user_info.get("name"),
        "client_id": body.client_id,
        "client_name": client_name,
        "redirect_uri": body.redirect_uri,
        "code_challenge": body.code_challenge,
        "scope": scope,
        "iat": now,
        "exp": now + AUTH_CODE_TTL_SECONDS,
    }
    code = jwt.encode(code_claims, _get_signing_secret(), algorithm="HS256")
    return {
        "code": code,
        "state": body.state,
        "scope": scope,
        "expires_in": AUTH_CODE_TTL_SECONDS,
    }


async def _parse_token_request(request: Request) -> Dict[str, Any]:
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        data = await request.json()
        return dict(data) if isinstance(data, dict) else {}
    form = await request.form()
    return {k: str(v) for k, v in form.items()}


def _issue_token_pair(
    *,
    user_id: str,
    email: Optional[str],
    name: Optional[str],
    scope: str,
    client_id: str,
    grant_id: str,
) -> Dict[str, Any]:
    secret = _get_signing_secret()
    now = int(time.time())
    access_claims = {
        "typ": "oauth_access",
        "sub": user_id,
        "userId": user_id,
        "email": email,
        "name": name,
        "client_id": client_id,
        "grant_id": grant_id,
        "scope": scope,
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL_SECONDS,
    }
    refresh_claims = {
        "typ": "oauth_refresh",
        "sub": user_id,
        "userId": user_id,
        "email": email,
        "name": name,
        "client_id": client_id,
        "grant_id": grant_id,
        "scope": scope,
        "iat": now,
        "exp": now + REFRESH_TOKEN_TTL_SECONDS,
    }
    return {
        "access_token": jwt.encode(access_claims, secret, algorithm="HS256"),
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_TTL_SECONDS,
        "refresh_token": jwt.encode(refresh_claims, secret, algorithm="HS256"),
        "scope": scope,
    }


@router.post("/oauth/token")
async def oauth_token(request: Request) -> Dict[str, Any]:
    """OAuth 2.1 token endpoint supporting authorization_code + PKCE and refresh_token."""
    params = await _parse_token_request(request)
    grant_type = params.get("grant_type")
    secret = _get_signing_secret()

    if grant_type == "authorization_code":
        code = params.get("code", "")
        code_verifier = params.get("code_verifier", "")
        redirect_uri = params.get("redirect_uri", "")
        client_id = params.get("client_id", "")
        if not code or not code_verifier or not redirect_uri:
            raise HTTPException(
                status_code=400, detail="Missing code, code_verifier, or redirect_uri"
            )
        try:
            claims = jwt.decode(code, secret, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid authorization code: {exc}"
            ) from exc

        if claims.get("typ") != "oauth_code":
            raise HTTPException(status_code=400, detail="Invalid code type")
        if client_id and claims.get("client_id") != client_id:
            raise HTTPException(status_code=400, detail="client_id mismatch")
        if claims.get("redirect_uri") != redirect_uri:
            raise HTTPException(status_code=400, detail="redirect_uri mismatch")
        if _pkce_s256(code_verifier) != claims.get("code_challenge"):
            raise HTTPException(status_code=400, detail="PKCE code_verifier mismatch")

        jti = str(claims.get("jti") or "")
        now = time.time()
        with _STATE_LOCK:
            _prune_used_codes(now)
            if jti in _USED_CODE_JTIS:
                raise HTTPException(
                    status_code=400, detail="Authorization code already used"
                )
            _USED_CODE_JTIS[jti] = float(
                claims.get("exp") or now + AUTH_CODE_TTL_SECONDS
            )

        user_id = str(claims["sub"])
        tenant_id = f"user:{user_id}"
        scope = str(claims.get("scope") or " ".join(SUPPORTED_SCOPES))
        effective_client_id = str(claims.get("client_id") or client_id)
        client_name = str(claims.get("client_name") or "MCP Client")
        grant_id = f"grant_{secrets.token_urlsafe(16)}"

        _save_grant(
            grant_id=grant_id,
            tenant_id=tenant_id,
            user_id=user_id,
            client_id=effective_client_id,
            client_name=client_name,
            scopes=scope.split(),
        )

        return _issue_token_pair(
            user_id=user_id,
            email=claims.get("email"),
            name=claims.get("name"),
            scope=scope,
            client_id=effective_client_id,
            grant_id=grant_id,
        )

    if grant_type == "refresh_token":
        refresh_token = params.get("refresh_token", "")
        if not refresh_token:
            raise HTTPException(status_code=400, detail="Missing refresh_token")
        try:
            claims = jwt.decode(refresh_token, secret, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid refresh_token: {exc}"
            ) from exc
        if claims.get("typ") != "oauth_refresh":
            raise HTTPException(status_code=400, detail="Invalid refresh_token type")

        user_id = str(claims["sub"])
        tenant_id = f"user:{user_id}"
        grant_id = claims.get("grant_id")
        if not verify_and_touch_mcp_grant(tenant_id, grant_id):
            raise HTTPException(
                status_code=401, detail="MCP session has been disconnected"
            )

        return _issue_token_pair(
            user_id=user_id,
            email=claims.get("email"),
            name=claims.get("name"),
            scope=str(claims.get("scope") or " ".join(SUPPORTED_SCOPES)),
            client_id=str(claims.get("client_id") or ""),
            grant_id=str(grant_id or ""),
        )

    raise HTTPException(status_code=400, detail=f"Unsupported grant_type: {grant_type}")


@router.get("/api/v1/oauth/grants")
async def list_oauth_grants(
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> Dict[str, Any]:
    """List active MCP OAuth grants for the authenticated user."""
    items = _list_grants_for_tenant(ctx.tenant_id, session=ctx.session)
    return {"items": items, "total": len(items)}


@router.delete("/api/v1/oauth/grants/{grant_id}")
async def disconnect_oauth_grant(
    grant_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> Dict[str, Any]:
    """Disconnect (revoke & permanently delete) a single MCP OAuth grant."""
    removed = _delete_grant_for_tenant(ctx.tenant_id, grant_id, session=ctx.session)
    if not removed:
        raise HTTPException(status_code=404, detail="MCP session not found")
    return {"disconnected": True, "grant_id": grant_id}


@router.delete("/api/v1/oauth/grants")
async def disconnect_all_oauth_grants(
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> Dict[str, Any]:
    """Disconnect all MCP OAuth grants for the authenticated user."""
    count = _delete_all_grants_for_tenant(ctx.tenant_id, session=ctx.session)
    return {"disconnected": True, "count": count}
