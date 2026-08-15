"""API router for advanced reasoning operations.

Phase 1-4: Multi-hop traversal, decomposition, feedback, and cross-galaxy synthesis.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

# Auth and session imports
from api.deps import FAIMContext, get_faim_context, get_tenant_id
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
    learned: Dict[str, Any] = Field(default_factory=dict)


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
# Helpers
# -----------------------------------------------------------------------------


def _resolve_graph_id(request_graph_id: Optional[str]) -> Optional[str]:
    """Return the explicit graph_id if given, else let the engine default."""
    return request_graph_id or None


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.post("/traverse", response_model=TraverseResponse)
async def traverse_graph(
    request: TraverseRequest,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
):
    """
    Multi-hop graph traversal to find reasoning paths.

    Finds connections between nodes via graph edges.
    """
    import time

    start_time = time.perf_counter()

    try:
        traverser = MultiHopTraverser(
            session=ctx.session,
            tenant_id=ctx.tenant_id,
            graph_id=_resolve_graph_id(request.graph_id),
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
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
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
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
):
    """
    Submit user feedback on reasoning quality.

    Used for reinforcement learning to improve future reasoning. Pulls the
    real turn context (query text, reasoning steps, answer) from the durable
    cortex_turns table so feedback is never written with placeholder values.
    """
    try:
        store = FeedbackStore(ctx.session)

        # Reconstruct real turn context from durable cortex_turns + reasoning nodes.
        query_text, reasoning_path, answer_given = _load_turn_context(
            ctx.session, ctx.tenant_id, request.turn_id
        )
        if not query_text and not reasoning_path:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Turn {request.turn_id} not found: feedback must reference "
                    "a real cortex turn"
                ),
            )

        feedback = store.record_feedback(
            turn_id=request.turn_id,
            tenant_id=ctx.tenant_id,
            query_text=query_text,
            reasoning_path=reasoning_path,
            answer_given=answer_given,
            user_rating=request.user_rating,
            user_correction=request.user_correction,
            correction_type=request.correction_type,
        )
        ctx.session.commit()

        # Best-effort reinforcement learning pass: recompute per-pattern stats
        # and persist them durably so the feedback → policy loop closes.
        try:
            from core.learning.reinforcement import ReinforcementLearner
            from store.pg.repos.reinforcement_learning_repo import (
                ReinforcementLearningRepo,
            )

            learner = ReinforcementLearner(
                store,
                learning_repo=ReinforcementLearningRepo(
                    ctx.session, ctx.tenant_id
                ),
            )
            learned = learner.learn_from_feedback(ctx.tenant_id)
            ctx.session.commit()
        except Exception:
            # Learning is best effort; feedback durability is already committed.
            learned = {}

        return FeedbackResponse(
            feedback_id=feedback.feedback_id,
            pattern_hash=feedback.pattern_hash,
            message="Feedback recorded for learning",
            learned=learned,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Feedback storage failed: {str(e)}"
        ) from e


@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize_galaxies(
    request: SynthesizeRequest,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
):
    """
    Cross-galaxy synthesis: find insights across multiple documents.

    Analyzes correlations, trends, and contradictions between documents.
    """
    try:
        synthesizer = CrossGalaxySynthesizer(ctx.session, ctx.tenant_id)

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
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
):
    """
    Get reasoning quality statistics for monitoring.
    """
    try:
        store = FeedbackStore(ctx.session)
        stats = store.get_feedback_stats(ctx.tenant_id, days)

        return stats

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Stats retrieval failed: {str(e)}"
        ) from e


@router.get("/learning/state")
async def get_learning_state(
    limit: int = Query(default=50, ge=1, le=500),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
):
    """
    Get the durable reinforcement learning state for this tenant.

    Returns learned pattern statistics (reliability, usage, threshold
    adjustments) plus high-level adaptive strategy recommendations produced
    by the ReinforcementLearner.
    """
    try:
        from core.learning.reinforcement import ReinforcementLearner
        from store.pg.repos.reinforcement_learning_repo import (
            ReinforcementLearningRepo,
        )

        repo = ReinforcementLearningRepo(ctx.session, ctx.tenant_id)
        patterns = repo.list_pattern_stats(limit=limit)

        learner = ReinforcementLearner(
            FeedbackStore(ctx.session),
            learning_repo=repo,
        )
        strategy = learner.adapt_strategy(ctx.tenant_id)

        return {
            "tenant_id": ctx.tenant_id,
            "patterns": patterns,
            "total_patterns": len(patterns),
            "adaptive_strategy": strategy,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Learning state retrieval failed: {str(e)}"
        ) from e


def _load_turn_context(session, tenant_id: str, turn_id: str):
    """Load real query/reasoning/answer context for a turn.

    Returns (query_text, reasoning_path, answer_given). Falls back to the raw
    turn_id on missing turns so feedback is never dropped, but records real
    context whenever the durable turn snapshot exists.
    """
    from store.pg.models_faim import CortexReasoningNodeModel, CortexTurnModel

    turn = (
        session.query(CortexTurnModel)
        .filter(
            CortexTurnModel.tenant_id == tenant_id,
            CortexTurnModel.turn_id == turn_id,
        )
        .first()
    )

    if turn is None:
        return "", [], ""

    reasoning_nodes = (
        session.query(CortexReasoningNodeModel)
        .filter(
            CortexReasoningNodeModel.tenant_id == tenant_id,
            CortexReasoningNodeModel.turn_id == turn_id,
        )
        .order_by(CortexReasoningNodeModel.created_at.asc())
        .all()
    )

    reasoning_path = [
        f"{node.title} :: {node.summary}" for node in reasoning_nodes
    ]
    if not reasoning_path:
        reasoning_path = [turn.task_type]

    answer_given = turn.narrative or ""
    if not answer_given and turn.answer_json:
        answer_given = str(turn.answer_json)

    return turn.query_text, reasoning_path, answer_given


__all__ = ["router"]
