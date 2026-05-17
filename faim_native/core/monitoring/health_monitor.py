"""Reasoning health monitoring system.

Tracks quality metrics and provides diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List


@dataclass
class HealthMetrics:
    """Comprehensive health metrics for reasoning system."""

    # Coverage metrics
    queries_analyzed: int
    avg_response_time_ms: float

    # Quality metrics
    avg_confidence: float
    high_confidence_rate: float  # % above 0.8
    low_confidence_rate: float  # % below 0.5

    # Success metrics (from feedback)
    user_satisfaction: float  # 0.0 to 1.0
    correction_rate: float

    # Reasoning depth
    avg_hops_used: float
    multi_hop_usage_rate: float

    # Error rates
    timeout_rate: float
    empty_result_rate: float
    contradiction_rate: float

    # Timestamp
    calculated_at: datetime = field(default_factory=datetime.utcnow)

    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        return (
            self.user_satisfaction >= 0.7
            and self.correction_rate <= 0.3
            and self.avg_confidence >= 0.6
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "queries_analyzed": self.queries_analyzed,
            "avg_response_time_ms": self.avg_response_time_ms,
            "avg_confidence": self.avg_confidence,
            "high_confidence_rate": self.high_confidence_rate,
            "low_confidence_rate": self.low_confidence_rate,
            "user_satisfaction": self.user_satisfaction,
            "correction_rate": self.correction_rate,
            "avg_hops_used": self.avg_hops_used,
            "multi_hop_usage_rate": self.multi_hop_usage_rate,
            "timeout_rate": self.timeout_rate,
            "empty_result_rate": self.empty_result_rate,
            "contradiction_rate": self.contradiction_rate,
            "is_healthy": self.is_healthy(),
            "calculated_at": self.calculated_at.isoformat(),
        }


class ReasoningHealthMonitor:
    """
    Monitors reasoning system health and provides diagnostics.

    Tracks:
    - Response times
    - Confidence distribution
    - User satisfaction trends
    - Error rates
    """

    def __init__(self, session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
        self._metrics_history: List[HealthMetrics] = []

    def calculate_metrics(self, days: int = 7) -> HealthMetrics:
        """Calculate current health metrics."""

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Query recent turns
        # Note: In real implementation, query cortex_turns table
        turns = self._fetch_recent_turns(cutoff)

        if not turns:
            return HealthMetrics(
                queries_analyzed=0,
                avg_response_time_ms=0.0,
                avg_confidence=0.0,
                high_confidence_rate=0.0,
                low_confidence_rate=0.0,
                user_satisfaction=0.0,
                correction_rate=0.0,
                avg_hops_used=0.0,
                multi_hop_usage_rate=0.0,
                timeout_rate=0.0,
                empty_result_rate=0.0,
                contradiction_rate=0.0,
            )

        # Calculate metrics
        response_times = [t.get("response_time_ms", 0) for t in turns]
        confidences = [t.get("confidence", 0) for t in turns]

        high_conf = sum(1 for c in confidences if c >= 0.8) / len(confidences)
        low_conf = sum(1 for c in confidences if c < 0.5) / len(confidences)

        # Get feedback stats
        from core.learning.feedback_store import FeedbackStore

        store = FeedbackStore(self.session)
        feedback_stats = store.get_feedback_stats(self.tenant_id, days)

        metrics = HealthMetrics(
            queries_analyzed=len(turns),
            avg_response_time_ms=sum(response_times) / len(response_times),
            avg_confidence=sum(confidences) / len(confidences),
            high_confidence_rate=high_conf,
            low_confidence_rate=low_conf,
            user_satisfaction=feedback_stats.get("average_rating", 0.0),
            correction_rate=feedback_stats.get("correction_rate", 0.0),
            avg_hops_used=sum(t.get("hops_used", 1) for t in turns) / len(turns),
            multi_hop_usage_rate=sum(1 for t in turns if t.get("hops_used", 1) > 1)
            / len(turns),
            timeout_rate=sum(1 for t in turns if t.get("timed_out", False))
            / len(turns),
            empty_result_rate=sum(1 for t in turns if not t.get("results"))
            / len(turns),
            contradiction_rate=sum(
                1 for t in turns if t.get("found_contradictions", False)
            )
            / len(turns),
        )

        self._metrics_history.append(metrics)

        return metrics

    def _fetch_recent_turns(self, cutoff: datetime) -> List[Dict]:
        """Fetch recent cortex turns."""
        # Placeholder - real implementation queries cortex_turns table
        return []

    def get_trend(self, metric_name: str, days: int = 14) -> Dict[str, Any]:
        """Get trend for a specific metric over time."""

        if not self._metrics_history:
            return {"trend": "insufficient_data"}

        values = [getattr(m, metric_name, 0) for m in self._metrics_history[-days:]]

        if len(values) < 2:
            return {"trend": "insufficient_data", "values": values}

        # Calculate trend
        first = values[0]
        last = values[-1]

        if last > first * 1.1:
            trend = "improving"
        elif last < first * 0.9:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "change_pct": round(((last - first) / first * 100), 1) if first else 0,
            "values": values,
        }

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report."""

        metrics = self.calculate_metrics(days=7)

        trends = {
            "user_satisfaction": self.get_trend("user_satisfaction"),
            "avg_confidence": self.get_trend("avg_confidence"),
            "correction_rate": self.get_trend("correction_rate"),
        }

        # Generate recommendations
        recommendations = []

        if metrics.user_satisfaction < 0.6:
            recommendations.append(
                {
                    "priority": "high",
                    "issue": "Low user satisfaction",
                    "action": "Review recent corrections and update pattern thresholds",
                }
            )

        if metrics.correction_rate > 0.3:
            recommendations.append(
                {
                    "priority": "high",
                    "issue": "High correction rate",
                    "action": "Enable multi-hop reasoning for all queries",
                }
            )

        if metrics.avg_confidence < 0.5:
            recommendations.append(
                {
                    "priority": "medium",
                    "issue": "Low average confidence",
                    "action": "Add more sources or lower confidence threshold",
                }
            )

        if metrics.timeout_rate > 0.1:
            recommendations.append(
                {
                    "priority": "medium",
                    "issue": "High timeout rate",
                    "action": "Reduce max hops or optimize queries",
                }
            )

        return {
            "metrics": metrics.to_dict(),
            "trends": trends,
            "recommendations": recommendations,
            "overall_health": "healthy" if metrics.is_healthy() else "degraded",
        }
