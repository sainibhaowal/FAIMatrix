"""FAIM-Native API: Reranker Router.

Exposes the FAIM-native deterministic reranker (RerankerV2) as a provider:
- GET  /api/v1/reranker/status  -> availability + model info
- POST /api/v1/reranker/test    -> real scoring of a query against candidates
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context  # noqa: E402
from core.query.reranker_v2 import (  # noqa: E402
    RerankerV2Candidate,
    score_reranker_v2,
)
from encoding.representation_v2 import build_representation_v2  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reranker", tags=["reranker"])


# =============================================================================
# Contracts
# =============================================================================


class RerankerStatusResponse(BaseModel):
    available: bool
    name: str
    display_name: str
    provider_type: str
    version: str
    deterministic: bool
    source: str
    description: str


class RerankerTestRequest(BaseModel):
    query: str = Field(default="How does FAIM rank evidence relevance?")
    candidates: Optional[List[str]] = Field(
        default=None,
        description="Candidate texts to score. Defaults to a built-in self-test.",
    )


class RerankerTestResponse(BaseModel):
    success: bool
    message: str
    latency_ms: int
    model: str
    results: Optional[List[dict]] = None


_RERANKER_ACTIVE_STATE: dict[str, bool] = {}

_RERANKER_SETTING_KEY = "reranker_active"


def is_reranker_active(tenant_id: str = "default") -> bool:
    """Return persisted reranker activation (defaults to active)."""
    return _RERANKER_ACTIVE_STATE.get(tenant_id, True)


def set_reranker_active(active: bool, tenant_id: str = "default") -> None:
    """Update reranker activation in memory (persisted by callers with a ctx)."""
    _RERANKER_ACTIVE_STATE[tenant_id] = active


def _load_reranker_state(session, tenant_id: str) -> bool:
    """Load reranker activation from durable service_settings."""
    from store.pg.models_faim import ServiceSettingModel

    try:
        row = (
            session.query(ServiceSettingModel)
            .filter(
                ServiceSettingModel.tenant_id == tenant_id,
                ServiceSettingModel.key == _RERANKER_SETTING_KEY,
            )
            .first()
        )
        if row is not None:
            value = (row.value_json or {}).get("active", True)
            _RERANKER_ACTIVE_STATE[tenant_id] = bool(value)
    except Exception:  # pragma: no cover - defensive
        pass
    return is_reranker_active(tenant_id)


def _persist_reranker_state(session, tenant_id: str, active: bool) -> None:
    """Persist reranker activation to durable service_settings."""
    from store.pg.models_faim import ServiceSettingModel

    try:
        row = (
            session.query(ServiceSettingModel)
            .filter(
                ServiceSettingModel.tenant_id == tenant_id,
                ServiceSettingModel.key == _RERANKER_SETTING_KEY,
            )
            .first()
        )
        if row is None:
            row = ServiceSettingModel(
                tenant_id=tenant_id, key=_RERANKER_SETTING_KEY
            )
            session.add(row)
        row.value_json = {"active": active}
        session.commit()
    except Exception as e:  # pragma: no cover - defensive
        logger.warning(f"Failed to persist reranker state: {e}")
        try:
            session.rollback()
        except Exception:  # nosec B110
            pass


# =============================================================================
# Routes
# =============================================================================


@router.get("/status", response_model=RerankerStatusResponse)
async def reranker_status(
    ctx: FAIMContext = Depends(get_faim_context),
):
    """Report the FAIM-native reranker availability."""
    tenant_id = getattr(ctx, "tenant_id", "default") or "default"
    active = _load_reranker_state(ctx.session, tenant_id)
    return RerankerStatusResponse(
        available=active,
        name="faim-reranker-v2",
        display_name="FAIM Native Reranker V2",
        provider_type="local",
        version="v2",
        deterministic=True,
        source="faim_native.core.query.reranker_v2",
        description=(
            "Deterministic proposition/entity/time/evidence fusion reranker. Always available on managed runtime."
            if active
            else "Reranker is currently terminated / disconnected by user."
        ),
    )


@router.post("/activate")
async def activate_reranker(
    ctx: FAIMContext = Depends(get_faim_context),
):
    """Activate the FAIM-native reranker."""
    tenant_id = getattr(ctx, "tenant_id", "default") or "default"
    set_reranker_active(True, tenant_id)
    _persist_reranker_state(ctx.session, tenant_id, True)
    return {"success": True, "message": "ReRanker activated successfully.", "active": True}


@router.post("/deactivate")
async def deactivate_reranker(
    ctx: FAIMContext = Depends(get_faim_context),
):
    """Deactivate/terminate the FAIM-native reranker."""
    tenant_id = getattr(ctx, "tenant_id", "default") or "default"
    set_reranker_active(False, tenant_id)
    _persist_reranker_state(ctx.session, tenant_id, False)
    return {"success": True, "message": "ReRanker terminated successfully.", "active": False}


@router.post("/test", response_model=RerankerTestResponse)
async def reranker_test(
    req: RerankerTestRequest,
    ctx: FAIMContext = Depends(get_faim_context),
):
    """Score a query against candidates using the real RerankerV2 pipeline."""
    start = time.perf_counter()
    tenant_id = getattr(ctx, "tenant_id", "default") or "default"
    if not _load_reranker_state(ctx.session, tenant_id):
        return RerankerTestResponse(
            success=False,
            message="ReRanker is terminated / disconnected. Please connect ReRanker for scoring.",
            latency_ms=0,
            model="faim-reranker-v2",
            results=[],
        )

    try:
        query_text = (req.query or "").strip() or "How does FAIM rank evidence relevance?"
        query_repr = build_representation_v2(query_text)

        if req.candidates:
            doc_texts = [c for c in req.candidates if c and str(c).strip()]
        else:
            doc_texts = [
                "FAIM ranks evidence relevance using proposition overlap, entity match, and evidence span scoring.",
                "Unauthorized access to the cloud provider was denied by the firewall.",
                "The deterministic reranker fuses entity, time, proposition and evidence signals into a single score.",
                "Baking a cake requires flour, sugar, eggs and an oven set to 350 degrees.",
            ]
        if not doc_texts:
            return RerankerTestResponse(
                success=False,
                message="No candidate documents provided.",
                latency_ms=int((time.perf_counter() - start) * 1000),
                model="faim-reranker-v2",
                results=[],
            )

        candidates = []
        for i, doc in enumerate(doc_texts):
            doc_repr = build_representation_v2(doc)
            candidates.append(
                RerankerV2Candidate(
                    node_id=UUID(int=i + 1),
                    created_at=None,
                    representation=doc_repr,
                    base_score=0.5,
                )
            )

        scores = score_reranker_v2(
            query_text=query_text,
            query_repr=query_repr,
            candidates=candidates,
        )
        totals, components, _, suppressed = scores

        results = []
        for i, doc in enumerate(doc_texts):
            node_id = UUID(int=i + 1)
            results.append(
                {
                    "rank": i + 1,
                    "score": totals.get(node_id, 0.0),
                    "components": components.get(node_id, {}),
                    "suppressed": node_id in suppressed,
                    "text": doc[:120],
                }
            )
        results.sort(key=lambda r: (-r["score"], r["text"]))

        latency = int((time.perf_counter() - start) * 1000)
        return RerankerTestResponse(
            success=True,
            message=f"RerankerV2 healthy — scored {len(results)} candidates.",
            latency_ms=latency,
            model="faim-reranker-v2",
            results=results,
        )
    except Exception as e:  # pragma: no cover - defensive
        logger.error(f"Reranker test failed: {e}")
        return RerankerTestResponse(
            success=False,
            message=f"Reranker test failed: {e}",
            latency_ms=int((time.perf_counter() - start) * 1000),
            model="faim-reranker-v2",
            results=[],
        )


__all__ = ["router"]