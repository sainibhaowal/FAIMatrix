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


# Phase 4: Golden Signals + Infrastructure Telemetry
class GoldenSignalsResponse(BaseModel):
    """Google SRE Four Golden Signals."""
    latency: Dict[str, float] = Field(default_factory=dict)  # p50, p95, p99
    traffic: Dict[str, float] = Field(default_factory=dict)  # req/sec, nodes/sec
    errors: Dict[str, float] = Field(default_factory=dict)   # error_rate, failed_checks
    saturation: Dict[str, float] = Field(default_factory=dict)  # cpu%, mem%, db%, cache%


@router.get("/{graph_id}/golden-signals", response_model=GoldenSignalsResponse)
async def get_golden_signals(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> GoldenSignalsResponse:
    """Get Google SRE Golden Signals snapshot with REAL measured data from live system."""
    try:
        from api.services.infra_telemetry import InfraTelemetry
        from api.middleware.latency_collector import get_latency_collector

        session = ctx.session
        infra = InfraTelemetry.get_snapshot(session, redis_client=None)

        # REAL latency metrics from actual query measurements
        latency_collector = get_latency_collector()
        latency_samples = latency_collector.get_samples(graph_id=graph_id, limit=1000)

        if latency_samples:
            latencies = sorted([s["latency_ms"] for s in latency_samples])
            latency_metrics = {
                "p50_ms": round(latencies[int(len(latencies) * 0.50)], 2),
                "p95_ms": round(latencies[int(len(latencies) * 0.95)], 2),
                "p99_ms": round(latencies[int(len(latencies) * 0.99)], 2),
                "mean_ms": round(sum(latencies) / len(latencies), 2),
                "max_ms": round(max(latencies), 2),
                "sample_count": len(latencies),
            }
        else:
            latency_metrics = {
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "mean_ms": 0.0,
                "max_ms": 0.0,
                "sample_count": 0,
            }

        # REAL traffic from latency samples (requests per second)
        query_count = len(latency_samples)
        traffic_metrics = {
            "requests_per_sec": round(query_count / 60.0, 2) if query_count > 0 else 0.0,
            "total_queries_measured": query_count,
        }

        # REAL error rate from actual failures
        error_count = sum(1 for s in latency_samples if s.get("status", 200) >= 400)
        error_rate = round((error_count / len(latency_samples)), 4) if latency_samples else 0.0

        error_metrics = {
            "error_rate": error_rate,
            "error_count": error_count,
            "total_requests": len(latency_samples),
        }

        # REAL saturation from actual infrastructure usage
        saturation_metrics = {
            "cpu_percent": round(infra.docker.cpu_utilization_percent, 2),
            "memory_percent": round(infra.docker.memory_utilization_percent, 2),
            "db_connections_percent": round(
                (infra.postgres.active_connections / infra.postgres.max_connections * 100)
                if infra.postgres.max_connections > 0 else 0.0,
                2
            ),
            "db_size_mb": round(infra.postgres.db_size_mb, 2),
            "cache_utilization_percent": round(
                (infra.redis.keyspace_hit_rate * 100) if infra.redis else 0.0,
                2
            ) if infra.redis else 0.0,
        }

        return GoldenSignalsResponse(
            latency=latency_metrics,
            traffic=traffic_metrics,
            errors=error_metrics,
            saturation=saturation_metrics,
        )
    except Exception as exc:
        logger.exception("golden signals failed graph=%s", graph_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Phase 6: Stress Testing
class StressTestRequest(BaseModel):
    """Stress test configuration."""
    max_concurrency: int = 10
    document_count: int = 100
    test_doc_size: str = "small"


class StressTestResponse(BaseModel):
    """Stress test results."""
    job_id: str
    graph_id: str
    test_config: Dict[str, Any]
    duration_sec: float
    saturation_point: Optional[int]
    results: List[Dict[str, Any]]


@router.post("/{graph_id}/stress", response_model=StressTestResponse)
async def run_stress_test(
    graph_id: str,
    request: StressTestRequest,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StressTestResponse:
    """Run progressive load stress test."""
    try:
        from api.services.stress_runner import StressRunner

        runner = StressRunner(ctx)
        result = runner.run_stress_test(
            graph_id=graph_id,
            max_concurrency=request.max_concurrency,
            document_count=request.document_count,
            test_doc_size=request.test_doc_size,
        )
        result_dict = runner.to_dict(result)
        return StressTestResponse(**result_dict)
    except Exception as exc:
        logger.exception("stress test failed graph=%s", graph_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Phase 8: Anomaly Alerts + Export
class AlertsResponse(BaseModel):
    """Benchmark alerts."""
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    critical_count: int = 0
    warning_count: int = 0


@router.get("/{graph_id}/alerts", response_model=AlertsResponse)
async def get_alerts(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> AlertsResponse:
    """Get active alerts for graph."""
    try:
        from api.services.benchmark_alerts import BenchmarkAlerts
        from api.services.benchmark_collector import BenchmarkCollector

        collector = _collector(ctx)
        latest = collector.latest_suite(graph_id)

        if not latest:
            return AlertsResponse()

        alerts_list = BenchmarkAlerts.check_alerts(latest)
        alerts_dict = BenchmarkAlerts.alerts_to_dict(alerts_list)

        critical_count = sum(1 for a in alerts_list if a.severity == "critical")
        warning_count = sum(1 for a in alerts_list if a.severity == "warning")

        return AlertsResponse(
            alerts=alerts_dict,
            critical_count=critical_count,
            warning_count=warning_count,
        )
    except Exception as exc:
        logger.exception("alerts lookup failed graph=%s", graph_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class ExportReportResponse(BaseModel):
    """Exported benchmark report."""
    graph_id: str
    export_timestamp: str
    report_hash: str
    snapshot: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    infrastructure: Dict[str, Any]


@router.post("/{graph_id}/export", response_model=ExportReportResponse)
async def export_benchmark_report(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> ExportReportResponse:
    """Export complete benchmark report with SHA256 integrity hash."""
    try:
        import hashlib
        import json
        from datetime import datetime
        from api.services.benchmark_alerts import BenchmarkAlerts
        from api.services.infra_telemetry import InfraTelemetry
        from api.services.benchmark_collector import BenchmarkCollector

        collector = _collector(ctx)
        latest = collector.latest_suite(graph_id)

        if not latest:
            raise HTTPException(status_code=404, detail="no_benchmark_data")

        alerts_list = BenchmarkAlerts.check_alerts(latest)
        alerts_dict = BenchmarkAlerts.alerts_to_dict(alerts_list)

        infra = InfraTelemetry.get_snapshot(ctx.session)
        infra_dict = InfraTelemetry.to_dict(infra)

        timestamp = datetime.now().isoformat()

        # Compute integrity hash
        report_dict = {
            "graph_id": graph_id,
            "timestamp": timestamp,
            "snapshot": latest,
            "alerts": alerts_dict,
            "infrastructure": infra_dict,
        }
        report_json = json.dumps(report_dict, sort_keys=True, separators=(",", ":"))
        report_hash = hashlib.sha256(report_json.encode()).hexdigest()

        return ExportReportResponse(
            graph_id=graph_id,
            export_timestamp=timestamp,
            report_hash=report_hash,
            snapshot=latest,
            alerts=alerts_dict,
            infrastructure=infra_dict,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("export failed graph=%s", graph_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


__all__ = ["router"]