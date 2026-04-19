"""FAIM-Native API: Benchmark Router.

Real BM-1 to BM-9 benchmark execution and history.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context  # noqa: E402
from api.services.benchmark_collector import BenchmarkCollector  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


class BenchmarkSeriesPoint(BaseModel):
    timestamp: Optional[str] = None
    nodes: int = 0
    cr: float = 0.0
    redundancy: float = 0.0
    drift: float = 0.0
    latency: Dict[str, float] = Field(default_factory=dict)


class BenchmarkItemResponse(BaseModel):
    benchmark_id: str
    name: str
    passed: bool
    score: float
    status: str
    evidence_hash: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)


class BenchmarkSuiteResponse(BaseModel):
    run_id: str
    tenant_id: str
    graph_id: str
    graph_version: int
    graph_hash: str
    diagnostics_hash: str
    computed_at: str
    duration_ms: int
    node_count: int
    edge_count: int
    atom_count: int
    macro_count: int
    compression_ratio: float
    throughput_synapses_per_sec: float
    budget_profile: str
    benchmark_count: int
    passed_count: int
    failed_count: int
    overall_score: float
    summary: Dict[str, Any] = Field(default_factory=dict)
    benchmarks: List[BenchmarkItemResponse]


class BenchmarkSeriesResponse(BaseModel):
    graph_id: str
    limit: int
    count: int
    points: List[BenchmarkSeriesPoint]


class BenchmarkRunsResponse(BaseModel):
    graph_id: str
    limit: int
    count: int
    runs: List[BenchmarkSuiteResponse]


def _collector(ctx: FAIMContext) -> BenchmarkCollector:
    return BenchmarkCollector(ctx)


@router.post("/{graph_id}/run", response_model=BenchmarkSuiteResponse)
async def run_benchmarks(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> BenchmarkSuiteResponse:
    collector = _collector(ctx)
    try:
        run = collector.run_suite(graph_id)
        collector.persist_suite(graph_id, run)
        return BenchmarkSuiteResponse(**run.to_dict())
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("benchmark run failed graph=%s", graph_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{graph_id}/latest", response_model=Optional[BenchmarkSuiteResponse])
async def get_latest_benchmark(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> Optional[BenchmarkSuiteResponse]:
    collector = _collector(ctx)
    try:
        latest = collector.latest_suite(graph_id)
        if not latest:
            return None
        return BenchmarkSuiteResponse(**latest)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("benchmark latest lookup failed graph=%s", graph_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{graph_id}/series", response_model=BenchmarkSeriesResponse)
async def get_benchmark_series(
    graph_id: str,
    limit: int = Query(200, ge=1, le=500),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> BenchmarkSeriesResponse:
    collector = _collector(ctx)
    try:
        points = collector.series_points(graph_id, limit=limit)
        return BenchmarkSeriesResponse(
            graph_id=graph_id,
            limit=limit,
            count=len(points),
            points=[BenchmarkSeriesPoint(**point) for point in points],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("benchmark series lookup failed graph=%s", graph_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{graph_id}/runs", response_model=BenchmarkRunsResponse)
async def get_benchmark_runs(
    graph_id: str,
    limit: int = Query(50, ge=1, le=500),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> BenchmarkRunsResponse:
    collector = _collector(ctx)
    try:
        runs = collector.list_runs(graph_id, limit=limit)
        return BenchmarkRunsResponse(
            graph_id=graph_id,
            limit=limit,
            count=len(runs),
            runs=[BenchmarkSuiteResponse(**run) for run in runs],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("benchmark runs lookup failed graph=%s", graph_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{graph_id}/runs/{run_id}", response_model=BenchmarkSuiteResponse)
async def get_benchmark_run(
    graph_id: str,
    run_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> BenchmarkSuiteResponse:
    collector = _collector(ctx)
    try:
        run = collector.get_run(graph_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="benchmark_run_not_found")
        return BenchmarkSuiteResponse(**run)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("benchmark run lookup failed graph=%s run=%s", graph_id, run_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


__all__ = ["router"]