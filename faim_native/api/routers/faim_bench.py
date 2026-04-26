"""FAIM-Bench v1 API — Tracks A, B, C, D, E, F.

Track A downloads BEIR datasets from HuggingFace and runs in background (minutes).
Track B runs persistence tests on synthetic data (seconds).
Track C runs 10-session continuity tests on synthetic data (seconds).
Track D reads efficiency metrics from live telemetry (seconds).
Track E covers agent workflow and API key continuity.
Track F covers real-world tasks such as multi-document QA and grounded writing.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/faim-bench", tags=["faim-bench"])


# ── Response models ────────────────────────────────────────────────────────────


class TrackBResponse(BaseModel):
    run_id: str
    graph_id: str
    duration_sec: float
    retention: Dict[str, float] = Field(default_factory=dict)
    update_accuracy: float = 0.0
    deletion_completeness: float = 0.0
    provenance_accuracy: float = 0.0
    hallucination_rate: float = 0.0
    answer_consistency: float = 0.0
    contradiction_resolution: float = 0.0
    multidoc_qa_accuracy: float = 0.0
    citation_accuracy: float = 0.0
    notes: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class StorageMetrics(BaseModel):
    node_count: int = 0
    edge_count: int = 0
    compression_ratio: float = 0.0
    bytes_per_node_estimate: float = 0.0


class LatencyMetrics(BaseModel):
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0


class TrackDResponse(BaseModel):
    run_id: str
    graph_id: str
    duration_sec: float
    storage: StorageMetrics = Field(default_factory=StorageMetrics)
    ingest_latency_ms: LatencyMetrics = Field(default_factory=LatencyMetrics)
    ingest_throughput_docs_per_sec: float = 0.0
    retrieval_latency_ms: LatencyMetrics = Field(default_factory=LatencyMetrics)
    quality_per_gb: float = 0.0
    notes: List[str] = Field(default_factory=list)


class TrackAJobResponse(BaseModel):
    """Track A background job — start, poll status, get results."""

    run_id: str
    graph_id: str
    status: str  # "running" | "completed" | "failed"
    progress_message: str = ""
    total_duration_sec: float = 0.0
    datasets: List[Dict[str, Any]] = Field(default_factory=list)


class TrackAStartRequest(BaseModel):
    dataset_names: List[str] = Field(
        default=["scifact", "nq", "hotpotqa", "fever", "msmarco"]
    )
    max_corpus: Optional[int] = None  # None = full corpus
    max_queries: Optional[int] = None  # None = all queries


class TrackCResponse(BaseModel):
    run_id: str
    graph_id: str
    duration_sec: float
    session_retention: List[Dict[str, Any]] = Field(default_factory=list)
    cross_session_recall: float = 0.0
    update_accuracy: float = 0.0
    stale_suppression: float = 0.0
    multihop_accuracy: float = 0.0
    hallucination_rate: float = 0.0
    long_horizon_recall: float = 0.0
    continuity_score: float = 0.0
    notes: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class FaimBenchSummaryResponse(BaseModel):
    """Combined FAIM-Bench v1 summary — all available tracks."""

    graph_id: str
    track_b: Optional[TrackBResponse] = None
    track_c: Optional[TrackCResponse] = None
    track_d: Optional[TrackDResponse] = None
    track_e: Dict[str, Any] = Field(default_factory=dict)
    track_f: Dict[str, Any] = Field(default_factory=dict)
    system_comparison: List[Dict[str, Any]] = Field(default_factory=list)
    track_a_job_id: Optional[str] = None
    spec_url: str = "/docs#faim-bench-v1"


class PublicationRunRequest(BaseModel):
    dataset_names: List[str] = Field(
        default=["scifact", "nq", "hotpotqa", "fever", "msmarco"]
    )
    max_corpus: Optional[int] = None
    max_queries: Optional[int] = None


class PublicationRunResponse(BaseModel):
    run_id: str
    graph_id: str
    started_at: str
    total_duration_sec: float
    datasets: List[str] = Field(default_factory=list)
    faim_track_a: Dict[str, Any] = Field(default_factory=dict)
    track_e: Dict[str, Any] = Field(default_factory=dict)
    track_f: Dict[str, Any] = Field(default_factory=dict)
    baselines: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    mteb: Dict[str, Any] = Field(default_factory=dict)
    workflow_checks: Dict[str, Any] = Field(default_factory=dict)
    system_comparison: List[Dict[str, Any]] = Field(default_factory=list)
    leaderboard: List[Dict[str, Any]] = Field(default_factory=list)
    results_report: Dict[str, Any] = Field(default_factory=dict)
    reproducibility_kit: Dict[str, Any] = Field(default_factory=dict)
    benchmark_spec: Dict[str, Any] = Field(default_factory=dict)


class PublicationJobResponse(BaseModel):
    run_id: str
    graph_id: str
    status: str  # running | completed | failed
    progress_message: str = ""
    total_duration_sec: float = 0.0
    result: Optional[PublicationRunResponse] = None


class PublicationLeaderboardResponse(BaseModel):
    graph_id: str
    run_id: str
    leaderboard: List[Dict[str, Any]] = Field(default_factory=list)


_publication_jobs: Dict[str, Dict[str, Any]] = {}
_publication_jobs_lock = threading.Lock()


def _set_publication_job(run_id: str, payload: Dict[str, Any]) -> None:
    with _publication_jobs_lock:
        _publication_jobs[run_id] = payload


def _get_publication_job(run_id: str) -> Optional[Dict[str, Any]]:
    with _publication_jobs_lock:
        return _publication_jobs.get(run_id)


def _build_worker_context(tenant_id: str, request_id: str) -> FAIMContext:
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
        storage_file_repo=repos.get("storage_file_repo"),
        raw_store=repos.get("raw_store"),
        index=repos.get("index"),
        cache=repos.get("cache"),
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.post("/{graph_id}/track-b", response_model=TrackBResponse)
async def run_track_b(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> TrackBResponse:
    """Run Track B — Persistent Memory evaluation.

    Ingests 15 synthetic facts into an isolated sub-graph,
    then measures: retention Recall@k, nDCG@10, MRR, update accuracy,
    deletion completeness, hallucination rate, citation accuracy,
    answer consistency across sessions.
    """
    try:
        from benchmarks.track_b_persistence import TrackBEvaluator

        result = TrackBEvaluator(ctx).run(graph_id)
        return TrackBResponse(**result.to_dict())
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("track-b failed graph=%s", graph_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{graph_id}/track-d", response_model=TrackDResponse)
async def run_track_d(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> TrackDResponse:
    """Run Track D — Efficiency metrics.

    Reads live telemetry: ingest p50/p95/p99 latency from event log,
    retrieval latency from LatencyCollector, storage size from Postgres,
    compression ratio from graph state.
    """
    try:
        from benchmarks.track_d_efficiency import TrackDEvaluator

        result = TrackDEvaluator(ctx).run(graph_id)
        d = result.to_dict()
        return TrackDResponse(
            run_id=d["run_id"],
            graph_id=d["graph_id"],
            duration_sec=d["duration_sec"],
            storage=StorageMetrics(**d["storage"]),
            ingest_latency_ms=LatencyMetrics(**d["ingest_latency_ms"]),
            ingest_throughput_docs_per_sec=d["ingest_throughput_docs_per_sec"],
            retrieval_latency_ms=LatencyMetrics(**d["retrieval_latency_ms"]),
            quality_per_gb=d["quality_per_gb"],
            notes=d["notes"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("track-d failed graph=%s", graph_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{graph_id}/track-c", response_model=TrackCResponse)
async def run_track_c(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> TrackCResponse:
    """Run Track C — Long-Horizon Continuity evaluation.

    Ingests 8 simulated user sessions (40 documents) into an isolated sub-graph.
    Measures fact retention per session, cross-session multi-hop recall,
    update accuracy (new value ranks above stale), stale suppression,
    long-horizon recall (session-1 facts retrieved in session 10),
    hallucination rate, and composite continuity score.
    """
    try:
        from benchmarks.track_c_continuity import TrackCEvaluator

        result = TrackCEvaluator(ctx).run(graph_id)
        return TrackCResponse(**result.to_dict())
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("track-c failed graph=%s", graph_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{graph_id}/track-a/start", response_model=TrackAJobResponse)
async def start_track_a(
    graph_id: str,
    request: TrackAStartRequest,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> TrackAJobResponse:
    """Start Track A (BEIR retrieval) as a background job.

    Downloads datasets from HuggingFace, ingests each corpus into FAIM,
    runs all test queries, and computes Recall@k, nDCG@10, MRR, MAP.

    Returns a job_id immediately. Poll GET /track-a/status/{job_id} for progress.

    Default datasets: scifact (5,183 docs, 300 queries) + nfcorpus (3,633 docs, 323 queries).
    Add "fiqa" or "scidocs" for larger evaluation. Use max_corpus to limit for quick tests.
    """
    try:
        from benchmarks.track_a_retrieval import TrackAEvaluator

        evaluator = TrackAEvaluator(ctx)
        job_id = evaluator.start_background(
            graph_id=graph_id,
            dataset_names=request.dataset_names,
            max_corpus=request.max_corpus,
            max_queries=request.max_queries,
        )
        from benchmarks.track_a_retrieval import get_job

        job = get_job(job_id)
        return TrackAJobResponse(
            run_id=job.run_id,
            graph_id=job.graph_id,
            status=job.status,
            progress_message=job.progress_message,
            total_duration_sec=job.total_duration_sec,
            datasets=[d.to_dict() for d in job.datasets],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("track-a start failed graph=%s", graph_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{graph_id}/track-a/status/{job_id}", response_model=TrackAJobResponse)
async def get_track_a_status(
    graph_id: str,
    job_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> TrackAJobResponse:
    """Poll Track A job status and partial results."""
    from benchmarks.track_a_retrieval import get_job

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="track_a_job_not_found")
    return TrackAJobResponse(
        run_id=job.run_id,
        graph_id=job.graph_id,
        status=job.status,
        progress_message=job.progress_message,
        total_duration_sec=job.total_duration_sec,
        datasets=[d.to_dict() for d in job.datasets],
    )


@router.get("/{graph_id}/track-a/jobs", response_model=List[TrackAJobResponse])
async def list_track_a_jobs(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> List[TrackAJobResponse]:
    """List all Track A jobs for this graph."""
    from benchmarks.track_a_retrieval import list_jobs

    jobs = [j for j in list_jobs() if j.graph_id == graph_id]
    return [
        TrackAJobResponse(
            run_id=j.run_id,
            graph_id=j.graph_id,
            status=j.status,
            progress_message=j.progress_message,
            total_duration_sec=j.total_duration_sec,
            datasets=[d.to_dict() for d in j.datasets],
        )
        for j in jobs
    ]


@router.post("/{graph_id}/run-all", response_model=FaimBenchSummaryResponse)
async def run_all_tracks(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> FaimBenchSummaryResponse:
    """Run Tracks B, C, D synchronously + start Track A in background.

    Returns immediately with B/C/D results and a Track A job_id for polling.
    """
    track_b_result = None
    track_c_result = None
    track_d_result = None
    track_a_job_id = None

    try:
        from benchmarks.track_b_persistence import TrackBEvaluator

        b = TrackBEvaluator(ctx).run(graph_id)
        track_b_result = TrackBResponse(**b.to_dict())
    except Exception:
        logger.exception("track-b failed in run-all graph=%s", graph_id)

    try:
        from benchmarks.track_c_continuity import TrackCEvaluator

        c = TrackCEvaluator(ctx).run(graph_id)
        track_c_result = TrackCResponse(**c.to_dict())
    except Exception:
        logger.exception("track-c failed in run-all graph=%s", graph_id)

    try:
        from benchmarks.track_d_efficiency import TrackDEvaluator

        d_raw = TrackDEvaluator(ctx).run(graph_id)
        d = d_raw.to_dict()
        track_d_result = TrackDResponse(
            run_id=d["run_id"],
            graph_id=d["graph_id"],
            duration_sec=d["duration_sec"],
            storage=StorageMetrics(**d["storage"]),
            ingest_latency_ms=LatencyMetrics(**d["ingest_latency_ms"]),
            ingest_throughput_docs_per_sec=d["ingest_throughput_docs_per_sec"],
            retrieval_latency_ms=LatencyMetrics(**d["retrieval_latency_ms"]),
            quality_per_gb=d["quality_per_gb"],
            notes=d["notes"],
        )
    except Exception:
        logger.exception("track-d failed in run-all graph=%s", graph_id)

    try:
        from benchmarks.track_a_retrieval import TrackAEvaluator

        track_a_job_id = TrackAEvaluator(ctx).start_background(graph_id=graph_id)
    except Exception:
        logger.exception("track-a start failed in run-all graph=%s", graph_id)

    return FaimBenchSummaryResponse(
        graph_id=graph_id,
        track_b=track_b_result,
        track_c=track_c_result,
        track_d=track_d_result,
        track_a_job_id=track_a_job_id,
    )


def _publication_events(ctx: FAIMContext, graph_id: str, limit: int = 100) -> List[Any]:
    events = ctx.event_repo.get_by_seq(
        ctx.session, graph_id=graph_id, after_seq=0, limit=max(1, limit) + 1
    )
    return [
        e for e in events if getattr(e, "kind", None) == "FAIM_BENCH_PUBLICATION_RESULT"
    ]


def _latest_publication(ctx: FAIMContext, graph_id: str) -> Optional[Dict[str, Any]]:
    events = _publication_events(ctx, graph_id, limit=100)
    if not events:
        return None
    payload = getattr(events[-1], "payload", {}) or {}
    run = payload.get("run") if isinstance(payload, dict) else None
    return run if isinstance(run, dict) else None


@router.post("/{graph_id}/publication/run", response_model=PublicationRunResponse)
async def run_publication_suite(
    graph_id: str,
    request: PublicationRunRequest,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> PublicationRunResponse:
    try:
        from benchmarks.publication_suite import PublicationSuite

        suite = PublicationSuite(ctx)
        run = suite.run(
            graph_id=graph_id,
            dataset_names=request.dataset_names,
            max_corpus=request.max_corpus,
            max_queries=request.max_queries,
        )
        data = run.to_dict()

        ctx.event_repo.emit(
            ctx.session,
            graph_id,
            "FAIM_BENCH_PUBLICATION_RESULT",
            {
                "run": data,
                "run_id": data.get("run_id"),
                "datasets": data.get("datasets", []),
            },
        )
        ctx.session.commit()
        return PublicationRunResponse(**data)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("publication suite failed graph=%s", graph_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{graph_id}/publication/start", response_model=PublicationJobResponse)
async def start_publication_suite(
    graph_id: str,
    request: PublicationRunRequest,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> PublicationJobResponse:
    run_id = str(uuid.uuid4())
    started = time.monotonic()
    tenant_id = ctx.tenant_id

    job_state: Dict[str, Any] = {
        "run_id": run_id,
        "graph_id": graph_id,
        "status": "running",
        "progress_message": "Queued publication suite",
        "total_duration_sec": 0.0,
        "result": None,
        "error": None,
    }
    _set_publication_job(run_id, job_state)

    def _runner() -> None:
        worker_ctx: Optional[FAIMContext] = None
        try:
            from benchmarks.publication_suite import PublicationSuite
            from runtime.context import close_session

            worker_ctx = _build_worker_context(tenant_id, f"publication-{run_id}")
            suite = PublicationSuite(worker_ctx)

            def _progress(message: str) -> None:
                state = _get_publication_job(run_id)
                if state is None:
                    return
                state["progress_message"] = message
                _set_publication_job(run_id, state)

            run = suite.run(
                graph_id=graph_id,
                dataset_names=request.dataset_names,
                max_corpus=request.max_corpus,
                max_queries=request.max_queries,
                run_id=run_id,
                progress_callback=_progress,
            )
            data = run.to_dict()

            worker_ctx.event_repo.emit(
                worker_ctx.session,
                graph_id,
                "FAIM_BENCH_PUBLICATION_RESULT",
                {
                    "run": data,
                    "run_id": data.get("run_id"),
                    "datasets": data.get("datasets", []),
                },
            )
            worker_ctx.session.commit()

            state = _get_publication_job(run_id) or job_state
            state["status"] = "completed"
            state["progress_message"] = "Publication suite completed"
            state["total_duration_sec"] = time.monotonic() - started
            state["result"] = data
            _set_publication_job(run_id, state)
        except Exception as exc:
            try:
                if worker_ctx and worker_ctx.session is not None:
                    worker_ctx.session.rollback()
            except Exception:
                pass
            state = _get_publication_job(run_id) or job_state
            state["status"] = "failed"
            state["progress_message"] = f"Failed: {exc}"
            state["total_duration_sec"] = time.monotonic() - started
            state["error"] = str(exc)
            _set_publication_job(run_id, state)
        finally:
            try:
                if worker_ctx and worker_ctx.session is not None:
                    from runtime.context import close_session

                    close_session(worker_ctx.session)
            except Exception:
                pass

    t = threading.Thread(target=_runner, daemon=True, name=f"publication-{run_id[:8]}")
    t.start()

    return PublicationJobResponse(
        run_id=run_id,
        graph_id=graph_id,
        status="running",
        progress_message="Starting publication suite",
        total_duration_sec=0.0,
        result=None,
    )


@router.get(
    "/{graph_id}/publication/status/{run_id}", response_model=PublicationJobResponse
)
async def get_publication_status(
    graph_id: str,
    run_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> PublicationJobResponse:
    _ = ctx
    state = _get_publication_job(run_id)
    if not state or state.get("graph_id") != graph_id:
        raise HTTPException(status_code=404, detail="publication_job_not_found")

    result = state.get("result")
    parsed: Optional[PublicationRunResponse] = None
    if isinstance(result, dict):
        parsed = PublicationRunResponse(**result)

    return PublicationJobResponse(
        run_id=str(state.get("run_id", run_id)),
        graph_id=str(state.get("graph_id", graph_id)),
        status=str(state.get("status", "running")),
        progress_message=str(state.get("progress_message", "")),
        total_duration_sec=float(state.get("total_duration_sec", 0.0) or 0.0),
        result=parsed,
    )


@router.get(
    "/{graph_id}/publication/latest", response_model=Optional[PublicationRunResponse]
)
async def get_publication_latest(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> Optional[PublicationRunResponse]:
    try:
        run = _latest_publication(ctx, graph_id)
        if not run:
            return None
        return PublicationRunResponse(**run)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("publication latest failed graph=%s", graph_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/{graph_id}/publication/leaderboard", response_model=PublicationLeaderboardResponse
)
async def get_publication_leaderboard(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> PublicationLeaderboardResponse:
    try:
        run = _latest_publication(ctx, graph_id)
        if not run:
            return PublicationLeaderboardResponse(
                graph_id=graph_id, run_id="", leaderboard=[]
            )
        return PublicationLeaderboardResponse(
            graph_id=graph_id,
            run_id=str(run.get("run_id", "")),
            leaderboard=list(run.get("leaderboard", [])),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("publication leaderboard failed graph=%s", graph_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{graph_id}/publication/spec", response_model=Dict[str, Any])
async def get_publication_spec(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> Dict[str, Any]:
    try:
        run = _latest_publication(ctx, graph_id)
        if not run:
            return {}
        return dict(run.get("benchmark_spec", {}))
    except Exception as exc:
        logger.exception("publication spec failed graph=%s", graph_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{graph_id}/publication/repro", response_model=Dict[str, Any])
async def get_publication_repro(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> Dict[str, Any]:
    try:
        run = _latest_publication(ctx, graph_id)
        if not run:
            return {}
        return dict(run.get("reproducibility_kit", {}))
    except Exception as exc:
        logger.exception("publication repro failed graph=%s", graph_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


__all__ = ["router"]
