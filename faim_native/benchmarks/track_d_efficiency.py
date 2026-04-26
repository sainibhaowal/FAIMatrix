"""Track D — Efficiency: storage, ingest speed, retrieval latency, compression.

All metrics sourced from live system telemetry — no synthetic workload needed.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class TrackDResult:
    run_id: str
    graph_id: str
    duration_sec: float

    # Storage
    node_count: int = 0
    edge_count: int = 0
    compression_ratio: float = 0.0
    bytes_per_node_estimate: float = 0.0

    # Ingest speed
    ingest_p50_ms: float = 0.0
    ingest_p95_ms: float = 0.0
    ingest_p99_ms: float = 0.0
    ingest_throughput_docs_per_sec: float = 0.0

    # Retrieval latency (from LatencyCollector)
    retrieval_p50_ms: float = 0.0
    retrieval_p95_ms: float = 0.0
    retrieval_p99_ms: float = 0.0

    # Quality-per-storage (retention score / compression_ratio)
    quality_per_gb: float = 0.0

    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "graph_id": self.graph_id,
            "duration_sec": round(self.duration_sec, 3),
            "storage": {
                "node_count": self.node_count,
                "edge_count": self.edge_count,
                "compression_ratio": round(self.compression_ratio, 4),
                "bytes_per_node_estimate": round(self.bytes_per_node_estimate, 1),
            },
            "ingest_latency_ms": {
                "p50": round(self.ingest_p50_ms, 2),
                "p95": round(self.ingest_p95_ms, 2),
                "p99": round(self.ingest_p99_ms, 2),
            },
            "ingest_throughput_docs_per_sec": round(
                self.ingest_throughput_docs_per_sec, 3
            ),
            "retrieval_latency_ms": {
                "p50": round(self.retrieval_p50_ms, 2),
                "p95": round(self.retrieval_p95_ms, 2),
                "p99": round(self.retrieval_p99_ms, 2),
            },
            "quality_per_gb": round(self.quality_per_gb, 4),
            "notes": self.notes,
        }


class TrackDEvaluator:
    """Collect efficiency metrics from live FAIM graph state."""

    def __init__(self, ctx: Any):
        self.ctx = ctx

    def run(self, graph_id: str) -> TrackDResult:
        from api.middleware.latency_collector import get_latency_collector
        from core.dynamics.nativegraph import compute_compression_ratio
        from orchestration.perf.telemetry import global_throughput
        from sqlalchemy import text

        run_id = str(uuid.uuid4())
        start = time.monotonic()
        result = TrackDResult(run_id=run_id, graph_id=graph_id, duration_sec=0.0)

        try:
            # ── Node and edge counts ───────────────────────────────────────
            nodes = self.ctx.node_repo.list_nodes(graph_id, limit=100000)
            edges = self.ctx.edge_repo.list_all_edges(graph_id, limit=200000)
            atom_count = sum(1 for n in nodes if int(getattr(n, "level", 0) or 0) == 0)
            macro_count = sum(1 for n in nodes if int(getattr(n, "level", 0) or 0) > 0)
            result.node_count = len(nodes)
            result.edge_count = len(edges)
            result.compression_ratio = compute_compression_ratio(
                atom_count, macro_count
            )

            # ── Estimate bytes per node from DB ────────────────────────────
            try:
                row = self.ctx.session.execute(
                    text("SELECT pg_total_relation_size('nodes') AS sz")
                ).fetchone()
                if row and row.sz and len(nodes) > 0:
                    result.bytes_per_node_estimate = float(row.sz) / len(nodes)
            except Exception:
                result.notes.append("could not read pg_total_relation_size")

            # ── Ingest latency from event log ──────────────────────────────
            events = self.ctx.event_repo.get_by_seq(
                self.ctx.session, graph_id=graph_id, after_seq=0, limit=5000
            )
            latency_events = [
                e for e in events if getattr(e, "kind", None) == "INGEST_PHASE_LATENCY"
            ]
            if latency_events:
                latencies_ms = []
                for e in latency_events:
                    payload = getattr(e, "payload", {}) or {}
                    lms = payload.get("latency_ms")
                    if lms is not None:
                        try:
                            latencies_ms.append(float(lms))
                        except (TypeError, ValueError):
                            pass
                if latencies_ms:
                    latencies_ms.sort()
                    n = len(latencies_ms)
                    result.ingest_p50_ms = latencies_ms[int(n * 0.50)]
                    result.ingest_p95_ms = latencies_ms[min(int(n * 0.95), n - 1)]
                    result.ingest_p99_ms = latencies_ms[min(int(n * 0.99), n - 1)]

            result.ingest_throughput_docs_per_sec = float(
                global_throughput.get_throughput()
            )

            # ── Retrieval latency from LatencyCollector ────────────────────
            lc = get_latency_collector()
            samples = lc.get_samples(graph_id=graph_id, limit=5000)
            query_samples = [s for s in samples if "query" in s.get("endpoint", "")]
            if query_samples:
                rlat = sorted(s["latency_ms"] for s in query_samples)
                n = len(rlat)
                result.retrieval_p50_ms = rlat[int(n * 0.50)]
                result.retrieval_p95_ms = rlat[min(int(n * 0.95), n - 1)]
                result.retrieval_p99_ms = rlat[min(int(n * 0.99), n - 1)]
            else:
                result.notes.append("no query latency samples yet — run queries first")

            # ── Quality-per-storage proxy ──────────────────────────────────
            # Compression ratio measures how much FAIM compacted raw atoms into macros.
            # Higher CR with same node count → more efficient storage.
            if result.compression_ratio > 0 and result.bytes_per_node_estimate > 0:
                gb_used = (result.bytes_per_node_estimate * result.node_count) / (
                    1024**3
                )
                result.quality_per_gb = result.compression_ratio / max(gb_used, 1e-9)

        except Exception as exc:
            result.notes.append(f"error: {exc}")
        finally:
            result.duration_sec = time.monotonic() - start

        return result
