"""Path optimization and constraints for reasoning.

Provides constraint satisfaction and path scoring for multi-hop reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class PathConstraints:
    """
    Constraints for pathfinding operations.

    Defines what paths are acceptable based on domain requirements.
    """

    # Depth constraints
    max_hops: int = 3
    min_hops: int = 1

    # Confidence constraints
    min_confidence: float = 0.1
    max_confidence: float = 1.0

    # Edge type constraints
    allowed_edge_types: Optional[set] = None
    forbidden_edge_types: Optional[set] = None

    # Node constraints
    required_node_types: Optional[set] = None
    forbidden_node_types: Optional[set] = None

    # Path structure constraints
    allow_cycles: bool = False
    max_branching_factor: int = 10

    # Temporal constraints
    require_temporal_order: bool = False  # Enforce chronological paths
    max_temporal_gap_days: Optional[int] = None

    def check_path(self, path) -> tuple[bool, str]:
        """
        Validate a path against all constraints.

        Returns:
            (is_valid, reason) tuple
        """
        # Check hop count
        if len(path.hops) < self.min_hops:
            return False, f"Too few hops: {len(path.hops)} < {self.min_hops}"

        if len(path.hops) > self.max_hops:
            return False, f"Too many hops: {len(path.hops)} > {self.max_hops}"

        # Check confidence
        if path.confidence < self.min_confidence:
            return (
                False,
                f"Confidence too low: {path.confidence:.2f} < {self.min_confidence}",
            )

        if path.confidence > self.max_confidence:
            return (
                False,
                f"Confidence too high (suspicious): {path.confidence:.2f} > {self.max_confidence}",
            )

        # Check edge types
        if self.allowed_edge_types:
            for hop in path.hops:
                if hop.edge_type not in self.allowed_edge_types:
                    return False, f"Forbidden edge type: {hop.edge_type}"

        if self.forbidden_edge_types:
            for hop in path.hops:
                if hop.edge_type in self.forbidden_edge_types:
                    return False, f"Forbidden edge type: {hop.edge_type}"

        # Check for cycles
        if not self.allow_cycles:
            visited = {str(path.start_node)}
            for hop in path.hops:
                node_id = str(hop.next_node_id)
                if node_id in visited:
                    return False, "Path contains cycle"
                visited.add(node_id)

        return True, "Valid"


class PathOptimizer:
    """
    Optimizes reasoning paths based on multiple criteria.

    Provides scoring functions and selection strategies.
    """

    def __init__(self):
        self.scoring_weights = {
            "confidence": 0.40,
            "conciseness": 0.20,  # Prefer shorter paths
            "diversity": 0.15,  # Prefer different routes
            "recency": 0.15,  # Prefer recent information
            "authority": 0.10,  # Prefer authoritative sources
        }

    def score_path(
        self,
        path,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Calculate composite score for a path.

        Higher score = better path.
        """
        scores = {}

        # Confidence score (already calculated)
        scores["confidence"] = path.confidence

        # Conciseness score (exponential decay with length)
        scores["conciseness"] = 0.9 ** len(path.hops)

        # Diversity score (unique edge types)
        edge_types = set(hop.edge_type for hop in path.hops)
        scores["diversity"] = len(edge_types) / max(len(path.hops), 1)

        # Recency score (if temporal data available)
        scores["recency"] = self._calculate_recency(path, context)

        # Authority score (source reliability)
        scores["authority"] = self._calculate_authority(path, context)

        # Weighted sum
        total_score = sum(
            scores[key] * self.scoring_weights[key] for key in self.scoring_weights
        )

        return total_score

    def _calculate_recency(
        self,
        path,
        context: Optional[Dict[str, Any]],
    ) -> float:
        """Calculate recency score based on node timestamps."""
        # Default: assume recent
        if not context or "current_time" not in context:
            return 0.8

        current_time = context["current_time"]

        # Extract timestamps from path metadata
        timestamps = []
        for key, value in path.metadata.items():
            if "timestamp" in key and value:
                try:
                    from datetime import datetime

                    ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    timestamps.append(ts)
                except Exception:
                    pass

        if not timestamps:
            return 0.5  # Neutral if no timestamps

        # Average age
        from datetime import datetime

        if isinstance(current_time, str):
            current_time = datetime.fromisoformat(current_time.replace("Z", "+00:00"))

        avg_age = sum((current_time - ts).days for ts in timestamps) / len(timestamps)

        # Score: newer is better (exponential decay)
        import math

        return math.exp(-avg_age / 30)  # 30-day half-life

    def _calculate_authority(
        self,
        path,
        context: Optional[Dict[str, Any]],
    ) -> float:
        """Calculate authority score based on source reliability."""
        # Default: moderate authority
        return 0.7

    def select_best_paths(
        self,
        paths: List[Any],
        top_k: int = 5,
        constraints: Optional[PathConstraints] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[tuple[Any, float]]:
        """
        Select top-k paths based on scores and constraints.

        Returns:
            List of (path, score) tuples, sorted by score descending.
        """
        scored_paths = []

        for path in paths:
            # Check constraints
            if constraints:
                is_valid, reason = constraints.check_path(path)
                if not is_valid:
                    continue

            # Calculate score
            score = self.score_path(path, context)
            scored_paths.append((path, score))

        # Sort by score descending
        scored_paths.sort(key=lambda x: x[1], reverse=True)

        return scored_paths[:top_k]

    def diversify_paths(
        self,
        paths: List[tuple[Any, float]],
        min_diversity: float = 0.5,
    ) -> List[tuple[Any, float]]:
        """
        Ensure selected paths are diverse (different routes).

        Uses greedy selection with diversity penalty.
        """
        if not paths:
            return []

        selected = [paths[0]]  # Always take highest scored

        for path, score in paths[1:]:
            # Check diversity against selected paths
            is_diverse = True
            for sel_path, _ in selected:
                similarity = self._calculate_path_similarity(path, sel_path)
                if similarity > (1 - min_diversity):
                    is_diverse = False
                    break

            if is_diverse:
                selected.append((path, score))

        return selected

    def _calculate_path_similarity(self, path1, path2) -> float:
        """Calculate Jaccard similarity between two paths."""
        nodes1 = {str(path1.start_node)} | {str(hop.next_node_id) for hop in path1.hops}
        nodes2 = {str(path2.start_node)} | {str(hop.next_node_id) for hop in path2.hops}

        if not nodes1 or not nodes2:
            return 0.0

        intersection = len(nodes1 & nodes2)
        union = len(nodes1 | nodes2)

        return intersection / union if union > 0 else 0.0

    def merge_paths(
        self,
        paths: List[Any],
        strategy: str = "consensus",
    ) -> Dict[str, Any]:
        """
        Merge multiple paths into a unified conclusion.

        Strategies:
        - consensus: Only include conclusions supported by multiple paths
        - best: Use highest confidence path only
        - weighted: Weight by path confidence
        """
        if not paths:
            return {"conclusion": None, "confidence": 0.0}

        if strategy == "best":
            best = max(paths, key=lambda p: p.confidence)
            return {
                "conclusion": best.explanation,
                "confidence": best.confidence,
                "source_path": best.path_id,
            }

        elif strategy == "consensus":
            # Find common nodes across paths
            all_end_nodes = [str(p.end_node) for p in paths]
            from collections import Counter

            node_counts = Counter(all_end_nodes)

            # Most common conclusion
            if node_counts:
                consensus_node, count = node_counts.most_common(1)[0]
                confidence = count / len(paths)

                return {
                    "conclusion": f"Consensus: {consensus_node}",
                    "confidence": confidence,
                    "supporting_paths": count,
                    "total_paths": len(paths),
                }

            return {"conclusion": None, "confidence": 0.0}

        elif strategy == "weighted":
            # Weighted average of conclusions
            total_weight = sum(p.confidence for p in paths)

            if total_weight == 0:
                return {"conclusion": None, "confidence": 0.0}

            # For now, return best weighted explanation
            weighted_confidence = total_weight / len(paths)
            best_path = max(paths, key=lambda p: p.confidence)

            return {
                "conclusion": best_path.explanation,
                "confidence": weighted_confidence,
                "num_paths": len(paths),
            }

        else:
            raise ValueError(f"Unknown merge strategy: {strategy}")
