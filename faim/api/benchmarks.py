# faim/api/benchmarks.py
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from faim.api.models import BenchmarkPoint, GraphMetrics, LatencyPoint
from faim.config import FaimSettings
from faim.api.auth import allow_dev_mode
from faim.engine import interface as engine

# =============================================================================
# BENCHMARKS API (REAL PRODUCT METRICS, FILE-SAFE)
#
# Storage format:
#   - JSON Lines (JSONL), one BenchmarkPoint per line, per graph_id.
#
# File safety:
#   - advisory lock (fcntl.flock) on the same file
#   - atomic append via os.open(..., O_APPEND) + os.write() under lock
#   - schema validation on write and on read
#   - read never crashes (skips malformed lines, counts them)
#
# Prod principle:
#   - Benchmarks are telemetry, never a source of truth for graph state.
# =============================================================================

router = APIRouter(prefix="/benchmarks", tags=["Benchmarks"], dependencies=[Depends(allow_dev_mode)])
settings = FaimSettings.from_env()


# -----------------------------------------------------------------------------
# Response models (kept local to avoid touching shared models)
# -----------------------------------------------------------------------------
class BenchWriteResult(BaseModel):
    ok: bool = True
    graph_id: str
    file: str
    bytes_written: int
    ts: str


class BenchSeriesResponse(BaseModel):
    graph_id: str
    points: List[BenchmarkPoint]
    skipped_lines: int = 0


class BenchAggregateResponse(BaseModel):
    graph_id: str

    # latency across window (percentiles over samples)
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0

    # node growth stats (window)
    nodes_first: int = 0
    nodes_last: int = 0
    node_growth: int = 0
    node_growth_per_min: float = 0.0

    # pruning (best-effort)
    # If prune events are recorded explicitly (optional), we use them.
    # Otherwise we estimate via negative node deltas.
    prune_events: int = 0
    prune_rate_per_min: float = 0.0

    # diagnostics
    points_used: int = 0
    skipped_lines: int = 0
    window_seconds: int = 0


# -----------------------------------------------------------------------------
# Small helpers (deterministic + safe)
# -----------------------------------------------------------------------------
def _clamp_int(v: int, lo: int, hi: int, default: int) -> int:
    try:
        iv = int(v)
    except Exception:
        return default
    if iv < lo:
        return lo
    if iv > hi:
        return hi
    return iv


def _as_int(val: Any, default: int = 0) -> int:
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        try:
            return int(val)
        except ValueError:
            try:
                return int(float(val))
            except ValueError:
                return default
    return default


def _as_float(val: Any, default: float = 0.0) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val)
        except ValueError:
            return default
    return default


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso_utc(s: str) -> Optional[datetime]:
    try:
        ss = (s or "").strip()
        if not ss:
            return None
        if ss.endswith("Z"):
            ss = ss[:-1] + "+00:00"
        dt = datetime.fromisoformat(ss)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _bench_file(graph_id: str) -> Path:
    return settings.benchmarks_dir / f"{graph_id}.jsonl"


# -----------------------------------------------------------------------------
# File-safe JSONL append (Linux: flock)
# -----------------------------------------------------------------------------
def _write_all(fd: int, data: bytes) -> int:
    total = 0
    mv = memoryview(data)
    while total < len(data):
        n = os.write(fd, mv[total:])
        if n <= 0:
            raise OSError("os.write returned 0")
        total += n
    return total


def _atomic_append_jsonl(path: Path, line: str) -> int:
    """
    Append a single line to JSONL file safely.
    - Creates parent dir
    - Uses lock + O_APPEND to avoid interleaving writes
    - Best-effort fsync for durability
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure exactly one newline at end (JSONL invariant)
    if not line.endswith("\n"):
        line = line + "\n"

    data = line.encode("utf-8", errors="strict")

    # Open with O_APPEND so each write goes to end atomically (with lock to serialize)
    fd = os.open(str(path), os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o644)
    try:
        # Advisory lock (Linux). If fcntl not available, we still append but without lock.
        try:
            import fcntl  # type: ignore

            fcntl.flock(fd, fcntl.LOCK_EX)
            locked = True
        except Exception:
            locked = False

        written = _write_all(fd, data)

        # Best-effort durability: flush to disk
        try:
            os.fsync(fd)
        except Exception:
            pass

        if locked:
            try:
                import fcntl  # type: ignore

                fcntl.flock(fd, fcntl.LOCK_UN)
            except Exception:
                pass

        return written
    finally:
        os.close(fd)


# -----------------------------------------------------------------------------
# Engine normalization (same intent as your current code, but strict + safe)
# -----------------------------------------------------------------------------
def _normalize_metrics(raw: Any) -> GraphMetrics:
    if raw is None:
        raise HTTPException(status_code=404, detail="Metrics not found")

    def g(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, Mapping):
            return obj.get(key, default)
        return getattr(obj, key, default)

    latency_raw_any = g(raw, "latency", {"p50": 0.0, "p95": 0.0})
    if isinstance(latency_raw_any, Mapping):
        latency_raw: Dict[str, Any] = dict(latency_raw_any)
    else:
        latency_raw = getattr(latency_raw_any, "__dict__", {"p50": 0.0, "p95": 0.0})

    node_count = _as_int(g(raw, "node_count", 0))
    edge_count = _as_int(g(raw, "edge_count", 0))
    compression_ratio = _as_float(g(raw, "compression_ratio", 0.0))
    redundancy = _as_float(g(raw, "redundancy", 0.0))
    drift = _as_float(g(raw, "drift", 0.0))

    retrieve_p50_ms = _as_float(latency_raw.get("p50", 0.0))
    retrieve_p95_ms = _as_float(latency_raw.get("p95", 0.0))

    return GraphMetrics(
        node_count=node_count,
        edge_count=edge_count,
        compression_ratio=compression_ratio,
        redundancy=redundancy,
        drift=drift,
        retrieve_p50_ms=retrieve_p50_ms,
        retrieve_p95_ms=retrieve_p95_ms,
    )


def _metrics_to_point(ts: datetime, gm: GraphMetrics) -> BenchmarkPoint:
    return BenchmarkPoint(
        timestamp=ts.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        nodes=gm.node_count,
        cr=gm.compression_ratio,
        redundancy=gm.redundancy,
        drift=gm.drift,
        latency=LatencyPoint(
            retrieve_p50_ms=gm.retrieve_p50_ms,
            retrieve_p95_ms=gm.retrieve_p95_ms,
        ),
    )


# -----------------------------------------------------------------------------
# JSONL reader (schema-validated, crash-proof)
# -----------------------------------------------------------------------------
def _iter_points(path: Path) -> Tuple[Iterable[BenchmarkPoint], int]:
    """
    Return (iterable, skipped_lines).
    NOTE: iterable is a generator; consumption happens in callers.
    """
    skipped = 0

    def gen() -> Iterable[BenchmarkPoint]:
        nonlocal skipped
        if not path.exists():
            return
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    try:
                        obj = json.loads(s)
                        # schema validation
                        yield BenchmarkPoint(**obj)
                    except Exception:
                        skipped += 1
                        continue
        except Exception:
            # can't read file -> treat as empty but do not crash API
            skipped += 1
            return

    return gen(), skipped


def _load_points_window(
    path: Path,
    *,
    since: Optional[datetime],
    limit: int,
) -> Tuple[List[BenchmarkPoint], int]:
    points_iter, skipped_early = _iter_points(path)
    out: List[BenchmarkPoint] = []
    skipped = skipped_early

    for p in points_iter:
        if since is not None:
            dt = _parse_iso_utc(p.timestamp)
            if dt is None or dt < since:
                continue
        out.append(p)
        if len(out) >= limit:
            break

    return out, skipped


# -----------------------------------------------------------------------------
# Percentiles + aggregates
# -----------------------------------------------------------------------------
def _percentile(sorted_vals: List[float], q: float) -> float:
    """
    Deterministic percentile for q in [0,1], using linear interpolation.
    """
    if not sorted_vals:
        return 0.0
    if q <= 0.0:
        return float(sorted_vals[0])
    if q >= 1.0:
        return float(sorted_vals[-1])

    n = len(sorted_vals)
    pos = (n - 1) * q
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return float(sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac)


def _compute_aggregate(points: List[BenchmarkPoint], skipped_lines: int) -> BenchAggregateResponse:
    if not points:
        return BenchAggregateResponse(
            graph_id="",
            points_used=0,
            skipped_lines=skipped_lines,
            window_seconds=0,
        )

    # sort by timestamp (defensive)
    pts = []
    for p in points:
        dt = _parse_iso_utc(p.timestamp)
        if dt is None:
            continue
        pts.append((dt, p))
    pts.sort(key=lambda x: x[0])

    if not pts:
        return BenchAggregateResponse(
            graph_id="",
            points_used=0,
            skipped_lines=skipped_lines,
            window_seconds=0,
        )

    dts = [x[0] for x in pts]
    ps = [x[1] for x in pts]

    graph_id = ""  # filled by caller
    window_seconds = int((dts[-1] - dts[0]).total_seconds())
    window_minutes = max(window_seconds / 60.0, 1e-9)

    # latency samples (use retrieve_p50_ms as representative; also could use p95)
    latency_samples = sorted([float(p.latency.retrieve_p50_ms) for p in ps])
    latency_p50 = _percentile(latency_samples, 0.50)
    latency_p95 = _percentile(latency_samples, 0.95)

    nodes_first = int(ps[0].nodes)
    nodes_last = int(ps[-1].nodes)
    node_growth = nodes_last - nodes_first
    node_growth_per_min = float(node_growth) / window_minutes

    # prune detection:
    # If nodes decrease across adjacent points, treat that as pruning events (best-effort).
    prune_events = 0
    pruned_nodes = 0
    for i in range(1, len(ps)):
        dn = int(ps[i].nodes) - int(ps[i - 1].nodes)
        if dn < 0:
            prune_events += 1
            pruned_nodes += -dn

    prune_rate_per_min = float(pruned_nodes) / window_minutes

    return BenchAggregateResponse(
        graph_id=graph_id,
        latency_p50_ms=float(latency_p50),
        latency_p95_ms=float(latency_p95),
        nodes_first=nodes_first,
        nodes_last=nodes_last,
        node_growth=node_growth,
        node_growth_per_min=float(node_growth_per_min),
        prune_events=int(prune_events),
        prune_rate_per_min=float(prune_rate_per_min),
        points_used=len(ps),
        skipped_lines=int(skipped_lines),
        window_seconds=int(window_seconds),
    )


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@router.post("/{graph_id}/snapshot", response_model=BenchmarkPoint)
def snapshot(graph_id: str) -> BenchmarkPoint:
    """
    Record one benchmark point by querying the engine metrics.
    """
    raw_metrics = engine.get_metrics(graph_id)
    gm = _normalize_metrics(raw_metrics)
    ts = datetime.now(timezone.utc)
    point = _metrics_to_point(ts, gm)

    # schema validation is already ensured by model construction
    file_path = _bench_file(graph_id)
    _atomic_append_jsonl(file_path, point.model_dump_json())

    return point


@router.post("/{graph_id}/record", response_model=BenchWriteResult)
def record_point(graph_id: str, point: BenchmarkPoint) -> BenchWriteResult:
    """
    Record a client-provided benchmark point (validated by Pydantic).
    Useful if UI measures something extra and wants to log it.
    """
    # Ensure timestamp is parseable; if not, force server timestamp
    dt = _parse_iso_utc(point.timestamp)
    if dt is None:
        point.timestamp = _iso_utc_now()

    file_path = _bench_file(graph_id)
    written = _atomic_append_jsonl(file_path, point.model_dump_json())

    return BenchWriteResult(
        graph_id=graph_id,
        file=str(file_path),
        bytes_written=int(written),
        ts=_iso_utc_now(),
    )


@router.get("/{graph_id}/series", response_model=BenchSeriesResponse)
def series(
    graph_id: str,
    limit: int = Query(500, ge=1, le=20000),
    since: Optional[str] = Query(None, description="ISO8601 UTC (e.g., 2025-12-19T10:00:00Z)"),
) -> BenchSeriesResponse:
    """
    Fetch time series points for plotting.
    Crash-proof: malformed lines are skipped.
    """
    file_path = _bench_file(graph_id)
    since_dt = _parse_iso_utc(since) if since else None

    pts, skipped = _load_points_window(file_path, since=since_dt, limit=int(limit))
    return BenchSeriesResponse(graph_id=graph_id, points=pts, skipped_lines=int(skipped))


@router.get("/{graph_id}/aggregate", response_model=BenchAggregateResponse)
def aggregate(
    graph_id: str,
    window_points: int = Query(500, ge=5, le=20000),
) -> BenchAggregateResponse:
    """
    Aggregated metrics for dashboards:
      - latency p50/p95 (over retrieve_p50_ms samples)
      - node growth and growth rate
      - prune rate (best-effort from negative node deltas)
    """
    file_path = _bench_file(graph_id)
    pts, skipped = _load_points_window(file_path, since=None, limit=int(window_points))

    agg = _compute_aggregate(pts, skipped_lines=int(skipped))
    agg.graph_id = graph_id
    return agg
