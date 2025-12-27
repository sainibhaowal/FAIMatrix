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
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from faim.config import FaimSettings
from faim.api.auth import require_api_key

router = APIRouter(prefix="/explain", tags=["explain"], dependencies=[Depends(require_api_key)])

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
def api_explain(trace_id: str) -> ExplainResponse:
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

    # If legacy traces missed use_count, derive one safely
    if "use_count" not in raw:
        raw["use_count"] = int(raw.get("ops", {}).get("evolution", {}).get("use_count", 0) or 0)

    return ExplainResponse(**raw)
