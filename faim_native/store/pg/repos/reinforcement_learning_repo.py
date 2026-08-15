"""Durable persistence for learned reasoning-pattern statistics.

The ReinforcementLearner reads accumulated ``reasoning_feedback`` rows and
writes compact per-pattern statistics here so that learned reliability and
threshold adjustments survive process restarts and can drive future reasoning.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from store.pg.models_feedback import ReinforcementPatternStatsModel
except (ImportError, RuntimeError, ModuleNotFoundError):  # pragma: no cover
    ReinforcementPatternStatsModel = Any


class ReinforcementLearningRepo:
    """Read/write access to durable reinforcement pattern statistics."""

    def __init__(self, session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def list_pattern_stats(
        self,
        limit: int = 100,
        min_samples: int = 1,
    ) -> List[Dict[str, Any]]:
        """Return learned pattern stats for the tenant, best first."""
        rows = (
            self.session.query(ReinforcementPatternStatsModel)
            .filter(ReinforcementPatternStatsModel.tenant_id == self.tenant_id)
            .filter(ReinforcementPatternStatsModel.total_uses >= min_samples)
            .order_by(
                ReinforcementPatternStatsModel.reliability_score.desc(),
                ReinforcementPatternStatsModel.total_uses.desc(),
            )
            .limit(max(1, min(500, int(limit))))
            .all()
        )
        return [row.to_dict() for row in rows]

    def get_pattern_stats(self, pattern_hash: str) -> Optional[Dict[str, Any]]:
        """Return a single pattern's learned stats, if any."""
        row = (
            self.session.query(ReinforcementPatternStatsModel)
            .filter(
                ReinforcementPatternStatsModel.tenant_id == self.tenant_id,
                ReinforcementPatternStatsModel.pattern_hash == pattern_hash,
            )
            .first()
        )
        return row.to_dict() if row is not None else None

    def upsert(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update a pattern's learned statistics."""
        pattern_hash = stats["pattern_hash"]
        row = (
            self.session.query(ReinforcementPatternStatsModel)
            .filter(
                ReinforcementPatternStatsModel.tenant_id == self.tenant_id,
                ReinforcementPatternStatsModel.pattern_hash == pattern_hash,
            )
            .first()
        )

        now = datetime.now(timezone.utc)
        if row is None:
            row = ReinforcementPatternStatsModel(
                pattern_hash=pattern_hash,
                tenant_id=self.tenant_id,
                query_signature=str(stats.get("query_signature", "unknown")),
                total_uses=int(stats.get("total_uses", 0)),
                successful_uses=int(stats.get("successful_uses", 0)),
                failed_uses=int(stats.get("failed_uses", 0)),
                average_rating=float(stats.get("average_rating", 0.0)),
                correction_rate=float(stats.get("correction_rate", 0.0)),
                reliability_score=float(stats.get("reliability_score", 0.5)),
                threshold_adjustment=float(stats.get("threshold_adjustment", 0.0)),
                first_seen=stats.get("first_seen") or now,
                last_used=stats.get("last_used") or now,
                updated_at=now,
            )
            self.session.add(row)
        else:
            row.query_signature = str(stats.get("query_signature", row.query_signature))
            row.total_uses = int(stats.get("total_uses", row.total_uses))
            row.successful_uses = int(stats.get("successful_uses", row.successful_uses))
            row.failed_uses = int(stats.get("failed_uses", row.failed_uses))
            row.average_rating = float(stats.get("average_rating", row.average_rating))
            row.correction_rate = float(stats.get("correction_rate", row.correction_rate))
            row.reliability_score = float(stats.get("reliability_score", row.reliability_score))
            row.threshold_adjustment = float(stats.get("threshold_adjustment", row.threshold_adjustment))
            row.first_seen = stats.get("first_seen") or row.first_seen
            row.last_used = stats.get("last_used") or row.last_used
            row.updated_at = now

        self.session.flush()
        return row.to_dict()