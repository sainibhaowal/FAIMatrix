"""Reinforcement learning for reasoning patterns.

Adjusts confidence thresholds and reasoning strategies based on feedback.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .feedback_store import FeedbackStore, ReasoningFeedback


@dataclass
class PatternStats:
    """Statistics for a learned reasoning pattern."""

    pattern_hash: str
    query_signature: str

    # Performance metrics
    total_uses: int
    successful_uses: int  # Rating >= 0.7
    failed_uses: int  # Rating < 0.5

    # Quality metrics
    average_rating: float
    correction_rate: float

    # Evolution
    first_seen: datetime
    last_used: datetime

    # Derived score
    reliability_score: float  # 0.0 to 1.0


class ReinforcementLearner:
    """
    Learns from feedback to improve future reasoning.

    Adjusts:
    - Confidence thresholds per pattern
    - Path selection preferences
    - Source reliability weights
    """

    def __init__(self, feedback_store: FeedbackStore, learning_repo=None):
        self.feedback_store = feedback_store
        self.pattern_stats: Dict[str, PatternStats] = {}
        self.threshold_adjustments: Dict[str, float] = {}
        self.learning_repo = learning_repo

    def learn_from_feedback(self, tenant_id: str) -> Dict[str, Any]:
        """
        Process recent feedback and update pattern statistics.

        Returns:
            Summary of what was learned
        """
        # Get unprocessed feedback
        stats = self.feedback_store.get_feedback_stats(tenant_id, days=30)

        # Update pattern stats
        patterns_updated = self._update_pattern_stats(tenant_id)

        # Calculate threshold adjustments
        thresholds_adjusted = self._adjust_thresholds(tenant_id)

        # Persist learned stats so they survive restarts.
        self._persist_pattern_stats(tenant_id)

        return {
            "patterns_updated": patterns_updated,
            "thresholds_adjusted": thresholds_adjusted,
            "feedback_summary": stats,
        }

    def _persist_pattern_stats(self, tenant_id: str) -> int:
        """Write the current learned pattern stats to durable storage."""
        if self.learning_repo is None:
            return 0
        persisted = 0
        for pattern_hash, pstats in self.pattern_stats.items():
            try:
                self.learning_repo.upsert(
                    {
                        "pattern_hash": pattern_hash,
                        "query_signature": pstats.query_signature,
                        "total_uses": pstats.total_uses,
                        "successful_uses": pstats.successful_uses,
                        "failed_uses": pstats.failed_uses,
                        "average_rating": pstats.average_rating,
                        "correction_rate": pstats.correction_rate,
                        "reliability_score": pstats.reliability_score,
                        "threshold_adjustment": self.threshold_adjustments.get(
                            pattern_hash, 0.0
                        ),
                        "first_seen": pstats.first_seen,
                        "last_used": pstats.last_used,
                    }
                )
                persisted += 1
            except Exception:
                # Persistence is best effort; never block learning.
                continue
        return persisted

    def _update_pattern_stats(self, tenant_id: str) -> int:
        """Update statistics for all patterns with new feedback."""
        # Discover distinct pattern hashes with feedback for this tenant.
        try:
            pattern_hashes = self.feedback_store.list_distinct_patterns(tenant_id)
        except Exception:
            pattern_hashes = list(self.pattern_stats.keys())

        updated = 0

        for pattern_hash in pattern_hashes:
            feedbacks = self.feedback_store.get_feedback_for_pattern(pattern_hash)

            if len(feedbacks) >= 3:  # Minimum samples for learning
                stats = self._calculate_pattern_stats(pattern_hash, feedbacks)
                self.pattern_stats[pattern_hash] = stats
                updated += 1

                # Mark feedbacks as processed
                for f in feedbacks:
                    if not f.processed:
                        self.feedback_store.mark_processed(f.feedback_id)

        return updated

    def _calculate_pattern_stats(
        self,
        pattern_hash: str,
        feedbacks: List[ReasoningFeedback],
    ) -> PatternStats:
        """Calculate statistics from feedback list."""

        ratings = [f.user_rating for f in feedbacks]
        corrections = [f for f in feedbacks if f.user_correction]

        total = len(feedbacks)
        successful = sum(1 for r in ratings if r >= 0.7)
        failed = sum(1 for r in ratings if r < 0.5)

        avg_rating = sum(ratings) / total if total > 0 else 0.0
        correction_rate = len(corrections) / total if total > 0 else 0.0

        # Calculate reliability score
        # High rating + low corrections = high reliability
        reliability = (avg_rating * 0.6) + ((1 - correction_rate) * 0.4)

        # Sample signature
        query_sig = feedbacks[0].query_signature if feedbacks else "unknown"

        return PatternStats(
            pattern_hash=pattern_hash,
            query_signature=query_sig,
            total_uses=total,
            successful_uses=successful,
            failed_uses=failed,
            average_rating=avg_rating,
            correction_rate=correction_rate,
            first_seen=min(f.created_at for f in feedbacks),
            last_used=max(f.created_at for f in feedbacks),
            reliability_score=reliability,
        )

    def _adjust_thresholds(self, tenant_id: str) -> Dict[str, float]:
        """Adjust confidence thresholds based on pattern performance."""

        adjustments = {}

        for pattern_hash, stats in self.pattern_stats.items():
            # If pattern has poor reliability, raise threshold
            if stats.reliability_score < 0.5:
                # Need more confidence to use this pattern
                adjustment = 0.15  # Raise threshold by 15%
                self.threshold_adjustments[pattern_hash] = adjustment
                adjustments[pattern_hash] = adjustment

            # If pattern has excellent reliability, lower threshold
            elif stats.reliability_score > 0.9 and stats.total_uses >= 10:
                # This pattern is trustworthy
                adjustment = -0.10  # Lower threshold by 10%
                self.threshold_adjustments[pattern_hash] = adjustment
                adjustments[pattern_hash] = adjustment

        return adjustments

    def suggest_reasoning_path(
        self,
        query_signature: str,
        available_paths: List[List[str]],
    ) -> Optional[List[str]]:
        """
        Suggest best reasoning path based on learned patterns.

        Returns None if no learned patterns apply.
        """
        if not available_paths:
            return None

        # Score each path
        scored_paths = []

        for path in available_paths:
            # Hash this path
            import hashlib
            import json

            path_hash = hashlib.sha256(
                json.dumps(path, sort_keys=True).encode()
            ).hexdigest()[:16]

            if path_hash in self.pattern_stats:
                stats = self.pattern_stats[path_hash]
                score = stats.reliability_score
            else:
                # Unknown path: neutral score
                score = 0.5

            scored_paths.append((path, score))

        # Return highest scored
        scored_paths.sort(key=lambda x: x[1], reverse=True)
        return scored_paths[0][0] if scored_paths else available_paths[0]

    def get_adjusted_threshold(
        self,
        pattern_hash: str,
        base_threshold: float = 0.7,
    ) -> float:
        """
        Get confidence threshold adjusted for this pattern.

        Higher threshold for unreliable patterns.
        Lower threshold for proven patterns.
        """
        adjustment = self.threshold_adjustments.get(pattern_hash, 0.0)

        # Apply adjustment with bounds
        adjusted = base_threshold + adjustment
        return max(0.3, min(0.95, adjusted))

    def adapt_strategy(self, tenant_id: str) -> Dict[str, Any]:
        """
        Suggest high-level strategy adaptations.

        Returns recommendations for system tuning.
        """
        stats = self.feedback_store.get_feedback_stats(tenant_id, days=30)

        recommendations = []

        avg_rating = stats.get("average_rating", 0.0)

        if avg_rating < 0.5:
            recommendations.append(
                {
                    "type": "critical",
                    "issue": "Low average rating",
                    "action": "Raise all confidence thresholds by 20%",
                    "reason": "System is overconfident in poor answers",
                }
            )

        elif avg_rating < 0.7:
            recommendations.append(
                {
                    "type": "warning",
                    "issue": "Moderate rating",
                    "action": "Require multiple source verification",
                    "reason": "Answers often incomplete or partially wrong",
                }
            )

        correction_rate = stats.get("correction_rate", 0.0)
        if correction_rate > 0.3:
            recommendations.append(
                {
                    "type": "action",
                    "issue": "High correction rate",
                    "action": "Enable multi-hop reasoning for all queries",
                    "reason": "Surface reasoning needs more depth",
                }
            )

        # Check by correction type
        by_type = stats.get("by_type", {})
        if by_type.get("factual", 0) > by_type.get("incomplete", 0):
            recommendations.append(
                {
                    "type": "data_quality",
                    "issue": "Many factual errors",
                    "action": "Review source reliability scores",
                    "reason": "Knowledge base may have stale/wrong facts",
                }
            )

        return {
            "current_stats": stats,
            "recommendations": recommendations,
            "adaptive_settings": self._generate_adaptive_settings(stats),
        }

    def _generate_adaptive_settings(self, stats: Dict) -> Dict[str, Any]:
        """Generate recommended settings based on performance."""

        avg_rating = stats.get("average_rating", 0.0)

        if avg_rating >= 0.8:
            # High performance: can be more aggressive
            return {
                "multi_hop_enabled": True,
                "auto_approve_threshold": 0.85,
                "require_multiple_sources": False,
                "max_hops": 4,
            }

        elif avg_rating >= 0.6:
            # Moderate: balanced approach
            return {
                "multi_hop_enabled": True,
                "auto_approve_threshold": 0.90,
                "require_multiple_sources": True,
                "max_hops": 3,
            }

        else:
            # Low performance: be conservative
            return {
                "multi_hop_enabled": False,
                "auto_approve_threshold": 0.95,
                "require_multiple_sources": True,
                "max_hops": 2,
            }
