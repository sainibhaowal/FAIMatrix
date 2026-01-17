"""FAIM-Native API: Dependencies.

Dependency injection for FastAPI routes.
Provides FAIMContext, tenant_id, session, etc.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

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

    # Optional index and cache
    index: Any = None
    cache: Any = None


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
    from runtime.context import get_repos

    repos = get_repos(tenant_id)

    return FAIMContext(
        tenant_id=tenant_id,
        request_id=request_id,
        session=repos.get("session"),
        node_repo=repos.get("node_repo"),
        edge_repo=repos.get("edge_repo"),
        event_repo=repos.get("event_repo"),
        gv_repo=repos.get("gv_repo"),
        snapshot_repo=repos.get("snapshot_repo"),
        raw_repo=repos.get("raw_repo"),
        index=repos.get("index"),
        cache=repos.get("cache"),
    )


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
# Exports
# =============================================================================

__all__ = [
    "FAIMContext",
    "get_tenant_id",
    "get_request_id",
    "get_graph_id",
    "get_faim_context",
    "require_admin",
]
