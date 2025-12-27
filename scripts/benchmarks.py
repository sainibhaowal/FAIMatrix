# ruff: noqa: E402
# ============================================================================
#  FAIM BENCHMARKS  –  GOLDEN EDITION (P3)
# ============================================================================

from __future__ import annotations

# --- FAIM repo root on sys.path when run as a script ------------------------
import sys
from pathlib import Path as _Path

_ROOT = _Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
# ---------------------------------------------------------------------------

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, cast

from faim.core import metrics as faim_metrics
from faim.core.engine import FAIMEngine
from faim.core.metrics import QAPair
from faim.core.types import GraphId
from faim.storage.sqlite_store import SqliteStore

# ---------------------------------------------------------------------------
#  Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkloadSpec:
    """
    Description of a benchmark workload.

    Attributes
    ----------
    name:
        Short symbolic name (e.g. "synthetic_repetitive").
    description:
        Human-readable explanation of the workload.
    kind:
        Category of workload ("synthetic", "real", "mixed", ...).
    """

    name: str
    description: str
    kind: str = "synthetic"


@dataclass(frozen=True)
class EngineInfo:
    """
    Static description of the engine configuration used for a benchmark.

    Attributes
    ----------
    engine_name:
        Name of the engine class (e.g. "FAIMEngine").
    profile:
        Speed/latency profile (e.g. "Default", "HyperSpeed").
    persist_mode:
        Persistence mode ("relaxed", "strict", etc.).
    """

    engine_name: str
    profile: str
    persist_mode: str


# ---------------------------------------------------------------------------
#  Internal helpers
# ---------------------------------------------------------------------------


def _load_lines(path: Path) -> List[str]:
    """Load non-empty, stripped lines from a text file."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]


def _make_synthetic(prefix: str, n: int) -> List[str]:
    """
    Deterministic synthetic queries; no RNG for reproducibility.
    """
    return [f"{prefix}-{i:05d}" for i in range(n)]


def _make_qa_from_queries(queries: Sequence[str], m: int) -> List[QAPair]:
    """
    Create a QA set by sub-sampling the query list.
    """
    if not queries:
        return [QAPair(query="hello", min_results=1)] * max(1, m)
    step = max(1, len(queries) // max(1, m))
    picks = [queries[i] for i in range(0, len(queries), step)][:m]
    return [QAPair(query=q, min_results=1) for q in picks]


def _latency_to_dict(obj: Any) -> Dict[str, Any]:
    """
    Convert a LatencyStats dataclass (or a similar mapping) into a plain dict.

    This keeps scripts and UI code simple while letting the metrics module
    expose a strong typed API.
    """
    if isinstance(obj, faim_metrics.LatencyStats):
        return {
            "p50_ms": float(obj.p50_ms),
            "p95_ms": float(obj.p95_ms),
            "max_ms": float(obj.max_ms),
            "count": int(obj.count),
        }
    if isinstance(obj, dict):
        # Best-effort: coerce keys we know about to built-in types.
        out: Dict[str, Any] = {}
        for key in ("p50_ms", "p95_ms", "max_ms", "count"):
            if key in obj:
                val = obj[key]
                if key == "count":
                    out[key] = int(val)
                else:
                    out[key] = float(val)
        return out
    # Unknown type: return an empty structure rather than failing.
    return {"p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0, "count": 0}


# ---------------------------------------------------------------------------
#  Public builder
# ---------------------------------------------------------------------------


def build_benchmark_record(
    *,
    graph_id: str,
    nodes: int,
    metrics: Mapping[str, Any],
    workload: WorkloadSpec,
    engine_info: EngineInfo,
) -> Dict[str, Any]:
    """
    Assemble a benchmark record suitable for JSON serialisation and UI use.

    Parameters
    ----------
    graph_id:
        Logical graph identifier (e.g. "RAVIN_MAIN").
    nodes:
        Number of live nodes in the graph at measurement time.
    metrics:
        Mapping with at least:
            - "cr": compression ratio
            - "redundancy": redundancy index
            - "drift": drift score
            - "latency": LatencyStats or compatible mapping
    workload:
        WorkloadSpec describing the benchmark scenario.
    engine_info:
        EngineInfo describing the engine configuration.

    Returns
    -------
    dict
        JSON-safe dictionary with the following top-level keys:

        - "graph_id", "timestamp", "nodes"
        - "workload" (dict)
        - "engine" (dict)
        - "metrics" (dict with cr/redundancy/drift/latency)
    """
    cr_raw = metrics.get("cr", 0.0)
    redundancy_raw = metrics.get("redundancy", 0.0)
    drift_raw = metrics.get("drift", 0.0)
    latency_raw = metrics.get("latency", {})

    record: Dict[str, Any] = {
        "graph_id": str(graph_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nodes": int(nodes),
        "workload": asdict(workload),
        "engine": asdict(engine_info),
        "metrics": {
            "cr": float(cr_raw),
            "redundancy": float(redundancy_raw),
            "drift": float(drift_raw),
            "latency": _latency_to_dict(latency_raw),
        },
    }
    return record


# ---------------------------------------------------------------------------
#  CLI wiring – run a real benchmark and write JSON
# ---------------------------------------------------------------------------


def _default_benchmarks_dir() -> Path:
    root = Path("Runtime/Benchmarks")
    root.mkdir(parents=True, exist_ok=True)
    return root


def run_benchmark(
    *,
    graph_id: str,
    k: int,
    synthetic_queries: int,
    queries_file: Optional[Path],
    qa_count: int,
    qa_file: Optional[Path],
    profile: str,
    region_mode: bool,
    output_dir: Path,
) -> Path:
    """
    Execute a small benchmark using the current FAIMEngine and SqliteStore.

    This is intended as a P3 "wiring test" that exercises:
      - compression_ratio
      - redundancy_index
      - drift_score
      - latency_stats
      - JSON emission via build_benchmark_record(...)
    """
    graph_id_typed = cast(GraphId, graph_id)
    store = SqliteStore.default()

    if region_mode:
        os.environ["FAIM_P3_REGION_MODE"] = "1"

    engine = FAIMEngine(profile=profile)

    # Build queries --------------------------------------------------------
    if queries_file is not None:
        queries = _load_lines(queries_file)
    else:
        queries = _make_synthetic("synthetic-query", max(1, synthetic_queries))

    # Build QA set ---------------------------------------------------------
    if qa_file is not None:
        qa_lines = _load_lines(qa_file)
        qa_pairs = [QAPair(query=q, min_results=1) for q in qa_lines]
    else:
        qa_pairs = _make_qa_from_queries(queries, max(1, qa_count))

    # Compute metrics ------------------------------------------------------
    cr = faim_metrics.compression_ratio(store, graph_id_typed)
    redundancy = faim_metrics.redundancy_index(store, graph_id_typed)
    drift = faim_metrics.drift_score(engine, graph_id_typed, qa_pairs, k=k)
    latency = faim_metrics.latency_stats(engine, graph_id_typed, queries, k=k)

    metrics_block: Dict[str, Any] = {
        "cr": cr,
        "redundancy": redundancy,
        "drift": drift,
        "latency": latency,
    }

    workload = WorkloadSpec(
        name="p3_cli",
        description="P3 benchmark via CLI (synthetic/real queries)",
        kind="synthetic" if queries_file is None else "real",
    )
    engine_info = EngineInfo(
        engine_name="FAIMEngine",
        profile=profile,
        persist_mode="relaxed",
    )

    # Best-effort count of live nodes (store may expose richer API later).
    # For now we just iterate; this is acceptable for P3 CLI runs.
    node_count = sum(1 for _ in store.iter_nodes(graph_id_typed))

    record = build_benchmark_record(
        graph_id=graph_id,
        nodes=node_count,
        metrics=metrics_block,
        workload=workload,
        engine_info=engine_info,
    )

    # File naming: graph + unix ts for easy sorting.
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time())
    out_path = output_dir / f"benchmark_{graph_id}_{ts}.json"

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, sort_keys=False)

    return out_path


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="FAIM P3 Benchmarks → JSON")
    parser.add_argument("--graph-id", default="default")
    parser.add_argument("--k", type=int, default=8)

    parser.add_argument(
        "--synthetic-queries",
        type=int,
        default=128,
        help="Number of synthetic queries if --queries is not supplied.",
    )
    parser.add_argument(
        "--queries",
        type=str,
        default="",
        help="Path to queries.txt (one query per line).",
    )

    parser.add_argument(
        "--qa",
        type=int,
        default=32,
        help="Number of QA queries (if --qa-file is not used).",
    )
    parser.add_argument(
        "--qa-file",
        type=str,
        default="",
        help="Path to qa.txt (one query per line).",
    )

    parser.add_argument(
        "--profile",
        type=str,
        default="Default",
        help="FAIMEngine profile name (for speed budgets).",
    )
    parser.add_argument(
        "--region-mode",
        action="store_true",
        help="Enable region-level evolution mode (FAIM_P3_REGION_MODE=1).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="Runtime/Benchmarks",
        help="Output directory for benchmark JSON.",
    )

    args = parser.parse_args(argv)

    queries_file = Path(args.queries) if args.queries else None
    qa_file = Path(args.qa_file) if args.qa_file else None
    output_dir = Path(args.output)

    path = run_benchmark(
        graph_id=args.graph_id,
        k=args.k,
        synthetic_queries=args.synthetic_queries,
        queries_file=queries_file,
        qa_count=args.qa,
        qa_file=qa_file,
        profile=args.profile,
        region_mode=args.region_mode,
        output_dir=output_dir,
    )
    print(f"Wrote {path}")


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
