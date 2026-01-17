"""FAIM-Native API: Query Router (Stage-8).

POST /v1/query - Query the FAIM graph with FAIM physics scoring.

Features:
- FAIM re-ranking (not just cosine similarity)
- Explain payload with parents/fractions/evidence
- SSE events (QUERY_START → QUERY_COMPLETE)
- Multi-tenant isolation
- STRICT mode determinism
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

# Flexible imports
_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context, get_tenant_id  # noqa: E402
from orchestration.ingest_flow import FAIMProfile  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["query"])


# =============================================================================
# Request/Response Models (Stage-8 Contract)
# =============================================================================


class QueryRequest(BaseModel):
    """Query request body."""

    graph_id: str = Field(..., description="Graph to query")
    query_text: str = Field(..., description="User query text")
    k: int = Field(10, ge=1, le=100, description="Number of results")
    profile: str = Field("STRICT", description="STRICT, BALANCED, or FAST")
    return_explain: bool = Field(False, description="Include explain payload")


class ScoreComponents(BaseModel):
    """Breakdown of FAIM score."""

    sim: float = Field(..., description="Cosine similarity")
    novel: float = Field(..., description="Novelty (residual)")
    opp: float = Field(..., description="Opposition penalty")
    red: float = Field(..., description="Redundancy penalty")
    rec: float = Field(..., description="Recency boost")
    use: float = Field(..., description="Usage boost")
    lvl: float = Field(..., description="Level penalty")


class EvidenceInfo(BaseModel):
    """Evidence anchor for a result."""

    raw_id: Optional[str] = None
    block_id: Optional[str] = None
    anchor: Optional[Dict[str, Any]] = None


class QueryResultItem(BaseModel):
    """A single query result."""

    node_id: str
    vector_hash: str
    score: float
    score_components: Dict[str, float]
    level: int
    touch_count: int
    evidence: Optional[EvidenceInfo] = None
    explain: Optional[Dict[str, Any]] = None


class QueryMetrics(BaseModel):
    """Graph metrics included in response."""

    node_count: int = 0
    avg_touch: float = 0.0
    CR: float = 0.0
    R: float = 0.0
    D_hat: float = 0.0
    H_hat: float = 0.0
    lambda_hat: float = 0.0
    novelty: float = 0.0
    energy: float = 0.0


class QueryResponse(BaseModel):
    """Full query response (Stage-8 contract)."""

    tenant_id: str
    graph_id: str
    graph_version: int
    graph_hash: str
    query_hash: str
    k: int
    profile: str
    results: List[QueryResultItem]
    metrics: QueryMetrics
    duration_ms: float


# =============================================================================
# Profile Mapping
# =============================================================================

PROFILE_MAP = {
    "STRICT": FAIMProfile.STRICT,
    "RELAXED": FAIMProfile.RELAXED,
    "FAST": FAIMProfile.FAST,
    "strict": FAIMProfile.STRICT,
    "relaxed": FAIMProfile.RELAXED,
    "fast": FAIMProfile.FAST,
}


# =============================================================================
# Query Endpoint (Stage-8)
# =============================================================================


@router.post("/query", response_model=QueryResponse)
async def query_graph(
    request: QueryRequest,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> QueryResponse:
    """Query the FAIM graph with physics-based scoring.

    Uses the FAIM scoring formula:
    - sim: cosine similarity to query
    - novel: residual (novelty)
    - opp: opposition penalty
    - red: redundancy penalty
    - rec: recency boost
    - use: usage boost (log1p touch_count)
    - lvl: level penalty

    STRICT mode:
    - Deterministic ordering
    - No index writes
    - Same query → same results

    Emits SSE events:
    - QUERY_START
    - QUERY_RERANKED
    - QUERY_TOUCH (for each result)
    - QUERY_COMPLETE
    """
    try:
        from orchestration.query_flow import run_query

        # Parse profile
        profile = PROFILE_MAP.get(request.profile, FAIMProfile.STRICT)

        # Execute query
        result = run_query(
            session=ctx.session,
            tenant_id=tenant_id,
            graph_id=request.graph_id,
            query_text=request.query_text,
            k=request.k,
            profile=profile,
            return_explain=request.return_explain,
            index=ctx.index if profile != FAIMProfile.STRICT else None,
        )

        # Build response
        results = []
        for r in result.results:
            evidence = None
            if r.get("evidence"):
                evidence = EvidenceInfo(
                    raw_id=r["evidence"].get("raw_id"),
                    block_id=r["evidence"].get("block_id"),
                    anchor=r["evidence"].get("anchor"),
                )

            results.append(
                QueryResultItem(
                    node_id=r["node_id"],
                    vector_hash=r["vector_hash"],
                    score=r["score"],
                    score_components=r["score_components"],
                    level=r["level"],
                    touch_count=r["touch_count"],
                    evidence=evidence,
                    explain=r.get("explain"),
                )
            )

        return QueryResponse(
            tenant_id=tenant_id,
            graph_id=request.graph_id,
            graph_version=result.graph_version,
            graph_hash=result.graph_hash,
            query_hash=result.query_hash,
            k=result.k,
            profile=request.profile,
            results=results,
            metrics=QueryMetrics(**result.metrics),
            duration_ms=result.duration_ms,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


# =============================================================================
# Exports
# =============================================================================

__all__ = ["router"]
