"""FAIM-Native API: Dependencies.

Dependency injection for FastAPI routes.
Provides FAIMContext, tenant_id, session, etc.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from fastapi import Depends, Header, HTTPException, Request

# Flexible imports
_parent = Path(__file__).parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))


# =============================================================================
# FAIM Context
# =============================================================================


@dataclass
class FAIMContext:
    """Context for FAIM operations.

    Contains tenant_id, graph_id, and all repositories.
    """

    tenant_id: str
    request_id: str

    # Repositories (injected lazily)
    session: Any = None
    node_repo: Any = None
    edge_repo: Any = None
    event_repo: Any = None
    gv_repo: Any = None
    snapshot_repo: Any = None
    raw_repo: Any = None
    storage_file_repo: Any = None

    # Optional index and cache
    index: Any = None
    cache: Any = None
    raw_store: Any = None


# =============================================================================
# Tenant Dependency
# =============================================================================


def get_tenant_id(request: Request) -> str:
    """Get tenant ID from request state (set by middleware).

    Raises HTTPException if not set.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant not authenticated")
    return tenant_id


def get_request_id(request: Request) -> str:
    """Get request ID from request state."""
    return getattr(request.state, "request_id", "unknown")


# =============================================================================
# Graph ID Header
# =============================================================================


def get_graph_id(
    graph_id: Optional[str] = Header(None, alias="X-Graph-Id"),
    graph_id_query: Optional[str] = None,  # Allow query param fallback
) -> str:
    """Get graph_id from header or query param.

    Raises HTTPException if missing.
    """
    gid = graph_id or graph_id_query
    if not gid:
        raise HTTPException(
            status_code=400,
            detail="Missing graph_id (use X-Graph-Id header or graph_id param)",
        )
    return gid


# =============================================================================
# FAIM Context Dependency
# =============================================================================


async def get_faim_context(
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    request_id: str = Depends(get_request_id),
) -> FAIMContext:
    """Get FAIM context with repos.

    This is the main dependency for all FAIM operations.
    """
    from runtime.context import close_session, get_repos

    repos = get_repos(tenant_id)
    session = repos.get("session")

    ctx = FAIMContext(
        tenant_id=tenant_id,
        request_id=request_id,
        session=session,
        node_repo=repos.get("node_repo"),
        edge_repo=repos.get("edge_repo"),
        event_repo=repos.get("event_repo"),
        gv_repo=repos.get("gv_repo"),
        snapshot_repo=repos.get("snapshot_repo"),
        raw_repo=repos.get("raw_repo"),
        storage_file_repo=repos.get("storage_file_repo"),
        raw_store=repos.get("raw_store"),
        index=repos.get("index"),
        cache=repos.get("cache"),
    )

    try:
        yield ctx
    finally:
        # Always release request-scoped DB resources to avoid stale
        # open transactions/locks across requests.
        if session is not None:
            try:
                session.rollback()
            except Exception:  # nosec B110
                pass
            close_session(session)


# =============================================================================
# Admin Dependency
# =============================================================================


def require_admin(
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
) -> str:
    """Require admin authentication.

    Raises HTTPException if not valid admin.
    """
    from api.middleware.auth import validate_admin_key

    if not x_admin_key:
        raise HTTPException(status_code=401, detail="Missing X-Admin-Key header")

    if not validate_admin_key(x_admin_key):
        raise HTTPException(status_code=403, detail="Invalid admin credentials")

    return "admin"


# =============================================================================
# Scope Dependency (K3)
# =============================================================================


def _scope_enforcement_enabled() -> bool:
    raw = os.getenv("FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return False


def _audit_scope_denied(request: Request, missing: Sequence[str]) -> None:
    """Emit key audit event for scope-denied decisions."""
    try:
        from api.middleware.auth import (
            AUDIT_ACTION_DENIED_SCOPE,
            append_key_audit_best_effort,
        )
    except Exception:  # nosec B110
        return

    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        return

    route_path = getattr(getattr(request, "url", None), "path", None) or "unknown"
    route_obj = getattr(getattr(request, "scope", {}), "get", lambda _k, _d=None: None)(
        "route"
    )
    if route_obj is not None:
        route_path = getattr(route_obj, "path", route_path)

    append_key_audit_best_effort(
        tenant_id=str(tenant_id),
        key_id=getattr(request.state, "auth_key_id", None) or "env-fallback",
        action=AUDIT_ACTION_DENIED_SCOPE,
        actor=f"{getattr(request.state, 'auth_method', 'unknown')}:scope_guard",
        request_id=(
            getattr(request.state, "request_id", None)
            or getattr(getattr(request, "headers", {}), "get", lambda _k, _d=None: None)(
                "X-Request-Id"
            )
        ),
        meta={
            "missing_scopes": sorted({str(scope) for scope in missing if str(scope)}),
            "route": route_path,
            "method": getattr(request, "method", "UNKNOWN"),
        },
    )


def require_scopes(required_scopes: Sequence[str]) -> Callable[..., Any]:
    """Require API key scopes for a route.

    Notes:
    - JWT-authenticated requests are currently allowed by compatibility policy.
    - Scope checks are active only when FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED=true.
    """
    required = [str(scope or "").strip() for scope in required_scopes]
    required = [scope for scope in required if scope]
    required = sorted(set(required))

    async def _require(request: Request) -> None:
        if not required:
            return

        # Compatibility path: JWT sessions remain allowed until dedicated JWT scopes are introduced.
        if getattr(request.state, "auth_method", None) == "jwt":
            return

        if not _scope_enforcement_enabled():
            return

        granted_raw = getattr(request.state, "auth_scopes", []) or []
        granted = {str(scope).strip() for scope in granted_raw if str(scope).strip()}
        missing = [scope for scope in required if scope not in granted]

        if missing:
            _audit_scope_denied(request, missing)
            raise HTTPException(
                status_code=403,
                detail=f"Missing required scopes: {', '.join(missing)}",
            )

    return _require


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "FAIMContext",
    "get_tenant_id",
    "get_request_id",
    "get_graph_id",
    "get_faim_context",
    "require_admin",
    "require_scopes",
]
