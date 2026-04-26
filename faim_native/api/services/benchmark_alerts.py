"""Anomaly detection and alerting for benchmarks.

Rule-based alerts on SpeedBudget violations, energy bounds, cache efficiency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from orchestration.perf.spec import get_speed_budget


@dataclass
class BenchmarkAlert:
    """Single alert triggered by anomaly detection."""

    id: str
    severity: str  # "info", "warning", "critical"
    title: str
    message: str
    metric: str
    current_value: float
    threshold: float
    triggered_at: str


class BenchmarkAlerts:
    """Detect anomalies in benchmark metrics."""

    @staticmethod
    def check_alerts(benchmark_snapshot: Dict[str, Any]) -> List[BenchmarkAlert]:
        """Detect all anomalies in a benchmark snapshot."""
        alerts: List[BenchmarkAlert] = []
        speed_budget = get_speed_budget()

        # Extract metrics from snapshot
        perf = benchmark_snapshot.get("performance", {})
        ingest_latency = perf.get("last_ingest_latency_ms", 0)
        cache = benchmark_snapshot.get("cache", {})
        cache_hit_rate = cache.get("hit_rate", 1.0)
        fractal = benchmark_snapshot.get("fractal_metrics", {})
        energy_E = fractal.get("energy_E", 1.0)
        redundancy_R = fractal.get("redundancy_R", 0.0)
        health = benchmark_snapshot.get("health", {})
        invariants = benchmark_snapshot.get("invariants", {})
        docker = benchmark_snapshot.get("infrastructure", {}).get("docker", {})

        # Alert 1: Ingest latency exceeds 2x SpeedBudget target
        target_latency = speed_budget.p95_insert_ms_strict
        if ingest_latency > target_latency * 2:
            alerts.append(
                BenchmarkAlert(
                    id="latency_2x",
                    severity="critical",
                    title="Ingest Latency Critical",
                    message=f"Ingest latency {ingest_latency:.0f}ms exceeds 2x target ({target_latency * 2:.0f}ms)",
                    metric="last_ingest_latency_ms",
                    current_value=ingest_latency,
                    threshold=target_latency * 2,
                    triggered_at="now",
                )
            )
        elif ingest_latency > target_latency * 1.5:
            alerts.append(
                BenchmarkAlert(
                    id="latency_1_5x",
                    severity="warning",
                    title="Ingest Latency Elevated",
                    message=f"Ingest latency {ingest_latency:.0f}ms exceeds 1.5x target ({target_latency * 1.5:.0f}ms)",
                    metric="last_ingest_latency_ms",
                    current_value=ingest_latency,
                    threshold=target_latency * 1.5,
                    triggered_at="now",
                )
            )

        # Alert 2: Cache hit rate too low
        if cache_hit_rate < 0.5:
            alerts.append(
                BenchmarkAlert(
                    id="cache_low",
                    severity="warning",
                    title="Cache Hit Rate Low",
                    message=f"Cache hit rate {cache_hit_rate * 100:.1f}% is below 50% threshold",
                    metric="hit_rate",
                    current_value=cache_hit_rate,
                    threshold=0.5,
                    triggered_at="now",
                )
            )

        # Alert 3: Energy approaching invariant bound
        if energy_E > 1.8:
            alerts.append(
                BenchmarkAlert(
                    id="energy_high",
                    severity="critical",
                    title="Energy Near Bound",
                    message=f"Energy E={energy_E:.2f} approaching invariant bound of 2.0",
                    metric="energy_E",
                    current_value=energy_E,
                    threshold=1.8,
                    triggered_at="now",
                )
            )

        # Alert 4: Redundancy too high (should evolve)
        if redundancy_R > 0.5:
            alerts.append(
                BenchmarkAlert(
                    id="redundancy_high",
                    severity="warning",
                    title="High Redundancy Detected",
                    message=f"Redundancy R={redundancy_R * 100:.1f}% exceeds 50% — consider running evolve",
                    metric="redundancy_R",
                    current_value=redundancy_R,
                    threshold=0.5,
                    triggered_at="now",
                )
            )

        # Alert 5: Database not connected
        if not health.get("db_connected", True):
            alerts.append(
                BenchmarkAlert(
                    id="db_down",
                    severity="critical",
                    title="Database Disconnected",
                    message="PostgreSQL connection failed",
                    metric="db_connected",
                    current_value=0.0,
                    threshold=1.0,
                    triggered_at="now",
                )
            )

        # Alert 6: Memory utilization high
        mem_util = docker.get("memory_utilization_percent", 0)
        if mem_util > 85:
            alerts.append(
                BenchmarkAlert(
                    id="memory_high",
                    severity="warning",
                    title="Memory Utilization High",
                    message=f"Memory utilization {mem_util:.1f}% exceeds 85% of container limit",
                    metric="memory_utilization_percent",
                    current_value=mem_util,
                    threshold=85.0,
                    triggered_at="now",
                )
            )

        # Alert 7: CPU utilization high
        cpu_util = docker.get("cpu_utilization_percent", 0)
        if cpu_util > 80:
            alerts.append(
                BenchmarkAlert(
                    id="cpu_high",
                    severity="info",
                    title="CPU Utilization High",
                    message=f"CPU utilization {cpu_util:.1f}% exceeds 80% of container limit",
                    metric="cpu_utilization_percent",
                    current_value=cpu_util,
                    threshold=80.0,
                    triggered_at="now",
                )
            )

        # Alert 8: Invariant violations
        if not invariants.get("all_passed", True):
            errors = invariants.get("errors", [])
            alerts.append(
                BenchmarkAlert(
                    id="invariant_failed",
                    severity="critical",
                    title="Invariant Violation",
                    message=f"{len(errors)} invariant check(s) failed: {'; '.join(errors[:2])}",
                    metric="invariants",
                    current_value=0.0,
                    threshold=1.0,
                    triggered_at="now",
                )
            )

        return alerts

    @staticmethod
    def alerts_to_dict(alerts: List[BenchmarkAlert]) -> List[Dict[str, Any]]:
        """Convert alerts to dictionary list."""
        return [
            {
                "id": a.id,
                "severity": a.severity,
                "title": a.title,
                "message": a.message,
                "metric": a.metric,
                "current_value": a.current_value,
                "threshold": a.threshold,
                "triggered_at": a.triggered_at,
            }
            for a in alerts
        ]
