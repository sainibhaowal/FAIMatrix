"""API router for advanced reasoning operations.

Phase 1-4: Multi-hop traversal, decomposition, feedback, and cross-galaxy synthesis.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

# Auth and session imports
try:
    from faim.Faim_Native.api.deps import get_db, get_tenant_id
    from faim.Faim_Native.core.cortex.planner_enhanced import (
        plan_turn_enhanced,
    )
    from faim.Faim_Native.core.learning.feedback_store import FeedbackStore
    from faim.Faim_Native.core.reasoning.cross_galaxy import CrossGalaxySynthesizer
    from faim.Faim_Native.core.reasoning.traversal import (
        MultiHopTraverser,
    )
except (ImportError, RuntimeError, ModuleNotFoundError):
    from api.deps import get_db, get_tenant_id
    from core.cortex.planner_enhanced import plan_turn_enhanced
    from core.learning.feedback_store import FeedbackStore
    from core.reasoning.cross_galaxy import CrossGalaxySynthesizer
    from core.reasoning.traversal import MultiHopTraverser


router = APIRouter(prefix="/reasoning", tags=["reasoning"])


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------


class TraverseRequest(BaseModel):
    """Request for multi-hop graph traversal."""

    start_node_ids: List[str]
    goal: str
    max_hops: int = 3
    min_confidence: float = 0.1
    graph_id: Optional[str] = None


class TraverseResponse(BaseModel):
    """Response with reasoning paths."""

    paths: List[Dict[str, Any]]
    total_paths: int
    query_time_ms: float


class PlanRequest(BaseModel):
    """Request for query planning."""

    query_text: str
    answer_mode: str = "direct"
    confidence: float = 0.8
    enable_multi_hop: bool = True


class PlanResponse(BaseModel):
    """Response with execution plan."""

    task_type: str
    goal: str
    complexity: str
    enable_multi_hop: bool
    max_hops: int
    sub_queries: List[Dict[str, Any]]
    requires_synthesis: bool


class FeedbackRequest(BaseModel):
    """Request to submit feedback."""

    turn_id: str
    user_rating: float  # 0.0 to 1.0
    user_correction: Optional[str] = None
    correction_type: Optional[str] = (
        None  # factual, incomplete, wrong_inference, irrelevant
    )


class FeedbackResponse(BaseModel):
    """Response confirming feedback stored."""

    feedback_id: str
    pattern_hash: str
    message: str


class SynthesizeRequest(BaseModel):
    """Request for cross-galaxy synthesis."""

    galaxy_ids: List[str]
    topic: Optional[str] = None
    max_galaxies: int = 5


class SynthesizeResponse(BaseModel):
    """Response with synthesized insights."""

    insights: List[Dict[str, Any]]
    galaxy_count: int
    total_nodes_analyzed: int


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.post("/traverse", response_model=TraverseResponse)
async def traverse_graph(
    request: TraverseRequest,
    db=Depends(get_db),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),  # noqa: B008
):
    """
    Multi-hop graph traversal to find reasoning paths.

    Finds connections between nodes via graph edges.
    """
    import time

    start_time = time.perf_counter()

    try:
        traverser = MultiHopTraverser(
            session=db,
            tenant_id=tenant_id,
            graph_id=request.graph_id,
        )

        paths = traverser.traverse(
            start_node_ids=request.start_node_ids,
            goal=request.goal,
            max_hops=request.max_hops,
            min_confidence=request.min_confidence,
        )

        elapsed = (time.perf_counter() - start_time) * 1000

        return TraverseResponse(
            paths=[p.to_dict() for p in paths],
            total_paths=len(paths),
            query_time_ms=round(elapsed, 2),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Traversal failed: {str(e)}"
        ) from e


@router.post("/plan", response_model=PlanResponse)
async def plan_query(
    request: PlanRequest,
    db=Depends(get_db),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),  # noqa: B008
):
    """
    Create enhanced execution plan for a query.

    Analyzes complexity and determines if multi-hop or decomposition needed.
    """
    try:
        plan = plan_turn_enhanced(
            query_text=request.query_text,
            answer_mode=request.answer_mode,
            confidence=request.confidence,
            enable_multi_hop=request.enable_multi_hop,
        )

        return PlanResponse(
            task_type=plan.task_type.value,
            goal=plan.goal,
            complexity=plan.complexity.value,
            enable_multi_hop=plan.enable_multi_hop,
            max_hops=plan.max_hops,
            sub_queries=[
                {
                    "id": sq.id,
                    "text": sq.text,
                    "type": sq.query_type,
                    "priority": sq.priority,
                    "depends_on": sq.depends_on,
                }
                for sq in plan.sub_queries
            ],
            requires_synthesis=plan.requires_synthesis,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Planning failed: {str(e)}") from e


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    db=Depends(get_db),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),  # noqa: B008
):
    """
    Submit user feedback on reasoning quality.

    Used for reinforcement learning to improve future reasoning.
    """
    try:
        store = FeedbackStore(db)

        # Get turn details from database
        # For now, use placeholder values
        feedback = store.record_feedback(
            turn_id=request.turn_id,
            tenant_id=tenant_id,
            query_text="",  # Would fetch from turn record
            reasoning_path=[],  # Would fetch from turn record
            answer_given="",  # Would fetch from turn record
            user_rating=request.user_rating,
            user_correction=request.user_correction,
            correction_type=request.correction_type,
        )

        return FeedbackResponse(
            feedback_id=feedback.feedback_id,
            pattern_hash=feedback.pattern_hash,
            message="Feedback recorded for learning",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Feedback storage failed: {str(e)}"
        ) from e


@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize_galaxies(
    request: SynthesizeRequest,
    db=Depends(get_db),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),  # noqa: B008
):
    """
    Cross-galaxy synthesis: find insights across multiple documents.

    Analyzes correlations, trends, and contradictions between documents.
    """
    try:
        synthesizer = CrossGalaxySynthesizer(db, tenant_id)

        insights = synthesizer.synthesize(
            galaxy_ids=request.galaxy_ids,
            topic=request.topic,
            max_galaxies=request.max_galaxies,
        )

        # Count total nodes analyzed
        total_nodes = sum(len(insight.evidence_nodes) for insight in insights)

        return SynthesizeResponse(
            insights=[i.to_dict() for i in insights],
            galaxy_count=len(request.galaxy_ids),
            total_nodes_analyzed=total_nodes,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Synthesis failed: {str(e)}"
        ) from e


@router.get("/stats")
async def get_reasoning_stats(
    days: int = Query(default=30, ge=1, le=365),
    db=Depends(get_db),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),  # noqa: B008
):
    """
    Get reasoning quality statistics for monitoring.
    """
    try:
        store = FeedbackStore(db)
        stats = store.get_feedback_stats(tenant_id, days)

        return stats

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Stats retrieval failed: {str(e)}"
        ) from e
