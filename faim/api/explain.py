# =============================================================================
# FAIM — Explain API (Golden Edition, file-backed, deterministic)
# -----------------------------------------------------------------------------
# Purpose:
#   Provide strict evidence for "why the model remembered":
#     - used memories
#     - provenance/lineage refs
#     - ops summary (inherit/antisym/prune/evolution)
#     - memory packet/context used
#     - evolution signal (last_access_ts, use_count, etc.)
#
# Storage model:
#   /Runtime/Logs/Explain/<trace_id>.json  (atomic write, JSON schema-like)
# =============================================================================

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from faim.api.auth_middleware import _is_dev_mode, get_current_user_oidc, verify_db_api_key
from faim.config import FaimSettings
from faim.db import get_db
from faim.models_sql import APIKey, GraphOwnership, OrgMember, Project, User

router = APIRouter(prefix="/explain", tags=["explain"], dependencies=[])

_TRACE_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{8,128}$")


def _settings() -> FaimSettings:
    return FaimSettings.from_env()


def _trace_dir(s: FaimSettings) -> Path:
    d = Path(s.root) / "Runtime" / "Logs" / "Explain"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _trace_path(s: FaimSettings, trace_id: str) -> Path:
    if not _TRACE_ID_RE.match(trace_id):
        raise HTTPException(status_code=400, detail="Invalid trace_id")
    return _trace_dir(s) / f"{trace_id}.json"


class ExplainResponse(BaseModel):
    trace_id: str
    graph_id: str
    created_ts: float

    # Hard evidence surfaces (A-LIFE-1 requires these)
    used_memories: List[str] = Field(default_factory=list)
    provenance: Any = Field(default_factory=dict)  # can be dict or list or links
    ops: Dict[str, Any] = Field(default_factory=dict)

    memory_packet: str = ""
    user_message: str = ""
    assistant_answer: str = ""

    # Evolution signals (must change across repeated retrievals)
    last_access_ts: float = 0.0
    use_count: int = 0


@router.get("/{trace_id}", response_model=ExplainResponse)
def api_explain(
    trace_id: str,
    user: Optional[User] = Depends(get_current_user_oidc),
    api_key: Optional[APIKey] = Depends(verify_db_api_key),
    db: Session = Depends(get_db),
) -> ExplainResponse:
    # 1. Auth Check
    if not user and not api_key:
        # Check dev mode
        if not _is_dev_mode():
            raise HTTPException(status_code=401, detail="Authentication required")
    s = _settings()
    p = _trace_path(s, trace_id)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Trace not found")

    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trace corrupt: {e}") from e

    # Minimal schema normalization (defensive)
    raw.setdefault("trace_id", trace_id)
    raw.setdefault("last_access_ts", time.time())

    if "use_count" not in raw:
        raw["use_count"] = int(raw.get("ops", {}).get("evolution", {}).get("use_count", 0) or 0)

    # 2. Verify Access (Graph Ownership)
    graph_id = raw.get("graph_id")
    if graph_id and (user or api_key):
        has_access = False
        if user:
            # Check User -> Org -> Project -> Graph
            count = (
                db.query(GraphOwnership)
                .join(Project, GraphOwnership.project_id == Project.id)
                .join(OrgMember, Project.org_id == OrgMember.org_id)
                .filter(GraphOwnership.graph_id == graph_id)
                .filter(OrgMember.user_id == user.id)
                .count()
            )
            if count > 0:
                has_access = True

        if not has_access and api_key:
            # Check Key -> Project -> Graph
            count = (
                db.query(GraphOwnership)
                .filter(GraphOwnership.graph_id == graph_id)
                .filter(GraphOwnership.project_id == api_key.project_id)
                .count()
            )
            if count > 0:
                has_access = True

        if not has_access:
            # Strict: if you are authenticated but don't own it -> 403.
            raise HTTPException(status_code=403, detail="Access denied to this trace")

    return ExplainResponse(**raw)
