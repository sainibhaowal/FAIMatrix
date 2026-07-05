"""Multi-hop graph traversal engine for FAIM reasoning.

Enables A → B → C chains of inference across the knowledge graph.
Deterministic, bounded, and auditable.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

# Flexible imports for different contexts
try:
    from faim.Faim_Native.store.pg.models_faim import EdgeModel, NodeModel
except (ImportError, RuntimeError, ModuleNotFoundError):
    try:
        from store.pg.models_faim import EdgeModel, NodeModel
    except (ImportError, RuntimeError, ModuleNotFoundError):
        # Fallback for testing
        EdgeModel = Any
        NodeModel = Any


@dataclass(frozen=True)
class Hop:
    """Single hop in a reasoning path: node → edge → next_node."""

    edge_id: str
    node_id: str
    node_label: str
    edge_type: str
    edge_weight: float
    next_node_id: str
    next_node_label: str
    edge_properties: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": str(self.edge_id),
            "node_id": str(self.node_id),
            "node_label": self.node_label,
            "edge_type": self.edge_type,
            "edge_weight": self.edge_weight,
            "edge_properties": self.edge_properties,
            "next_node_id": str(self.next_node_id),
            "next_node_label": self.next_node_label,
            "reasoning": self.reasoning,
        }


@dataclass(frozen=True)
class ReasoningPath:
    """A complete multi-hop path through the knowledge graph."""

    path_id: str
    start_node: str
    end_node: str
    hops: Tuple[Hop, ...]
    confidence: float
    path_length: int
    explanation: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Validate confidence bounds
        object.__setattr__(self, "confidence", max(0.0, min(1.0, self.confidence)))

    @property
    def hop_count(self) -> int:
        return len(self.hops)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "start_node": str(self.start_node),
            "end_node": str(self.end_node),
            "hops": [hop.to_dict() for hop in self.hops],
            "confidence": self.confidence,
            "path_length": self.path_length,
            "explanation": self.explanation,
            "metadata": self.metadata,
        }


class MultiHopTraverser:
    """
    Deterministic multi-hop graph traversal for FAIM reasoning.

    Supports reasoning chains up to MAX_HOPS depth with confidence decay.
    All operations are auditable and reproducible.
    """

    # Configuration constants
    MAX_HOPS = 24
    MIN_EDGE_WEIGHT = 0.3
    MAX_PATHS_PER_QUERY = 10
    CONFIDENCE_DECAY = 0.9  # Multiplicative decay per hop
    MAX_FRONTIER_WIDTH = 96
    MAX_TOTAL_EXPANSIONS = 4096

    # Edge types that support reasoning
    REASONING_EDGE_TYPES = {
        "implies",
        "causes",
        "enables",
        "leads_to",
        "supports",
        "contradicts",
        "part_of",
        "related_to",
        "temporal_before",
        "temporal_after",
    }

    def __init__(
        self,
        session,
        tenant_id: str,
        graph_id: Optional[str] = None,
    ):
        """
        Initialize traverser for a specific tenant/graph context.

        Args:
            session: Database session
            tenant_id: Tenant identifier for isolation
            graph_id: Optional graph to constrain traversal
        """
        self.session = session
        self.tenant_id = tenant_id
        self.graph_id = graph_id
        self._node_cache: Dict[str, Dict[str, Any]] = {}
        self._edge_cache: Dict[str, List[EdgeModel]] = {}

    def traverse(
        self,
        start_node_ids: List[str],
        goal: Optional[str],
        max_hops: Optional[int] = None,
        min_confidence: Optional[float] = None,
        edge_types: Optional[Set[str]] = None,
        max_frontier_width: Optional[int] = None,
        max_total_expansions: Optional[int] = None,
        return_partial_paths: bool = True,
    ) -> List[ReasoningPath]:
        """
        Find reasoning paths from start nodes toward a goal.

        Algorithm:
        1. Initialize frontier with start nodes
        2. For each hop depth:
           - Expand frontier by following edges
           - Check if any node matches goal
           - Build paths for matches
        3. Score and rank all paths
        4. Return top paths

        Args:
            start_node_ids: Entry points for traversal
            goal: Target concept to find (semantic matching)
            max_hops: Max traversal depth (default: MAX_HOPS)
            min_confidence: Minimum path confidence threshold
            edge_types: Which edge types to follow (default: REASONING_EDGE_TYPES)

        Returns:
            List of ReasoningPath objects, sorted by confidence
        """
        max_hops = max_hops or self.MAX_HOPS
        min_confidence = min_confidence or 0.1
        edge_types = edge_types or self.REASONING_EDGE_TYPES
        max_frontier_width = max_frontier_width or self.MAX_FRONTIER_WIDTH
        max_total_expansions = max_total_expansions or self.MAX_TOTAL_EXPANSIONS

        all_paths: List[ReasoningPath] = []

        for start_id in start_node_ids:
            paths = self._traverse_from_start(
                start_id=start_id,
                goal=goal,
                max_hops=max_hops,
                min_confidence=min_confidence,
                edge_types=edge_types,
                max_frontier_width=max_frontier_width,
                max_total_expansions=max_total_expansions,
                return_partial_paths=return_partial_paths,
            )
            all_paths.extend(paths)

        # Sort by confidence descending
        all_paths.sort(key=lambda p: (-p.confidence, p.path_length, p.path_id))

        return all_paths[: self.MAX_PATHS_PER_QUERY]

    def _traverse_from_start(
        self,
        start_id: str,
        goal: Optional[str],
        max_hops: int,
        min_confidence: float,
        edge_types: Set[str],
        max_frontier_width: int,
        max_total_expansions: int,
        return_partial_paths: bool,
    ) -> List[ReasoningPath]:
        """Breadth-first traversal from a single start node."""

        paths: List[ReasoningPath] = []
        partial_paths: List[ReasoningPath] = []
        expansions = 0

        # Frontier: (current_node_id, hops_so_far, confidence_so_far, visited_set)
        frontier: List[Tuple[str, List[Hop], float, Set[str]]] = [
            (start_id, [], 1.0, {start_id})
        ]

        for _depth in range(max_hops):
            next_frontier: List[Tuple[str, List[Hop], float, Set[str]]] = []

            for current_id, hops, confidence, visited in frontier:
                # Skip if confidence too low
                if confidence < min_confidence:
                    continue
                if expansions >= max_total_expansions:
                    break

                # Get outgoing edges
                edges = self._get_outgoing_edges(current_id, edge_types)

                for edge in edges:
                    if expansions >= max_total_expansions:
                        break
                    next_id = str(edge.dst_node_id)
                    edge_weight = self._normalized_edge_weight(edge)

                    # Skip visited nodes (prevent cycles)
                    if next_id in visited:
                        continue

                    # Skip low-weight edges
                    if edge_weight < self.MIN_EDGE_WEIGHT:
                        continue

                    # Build hop
                    hop = self._build_hop(current_id, edge, next_id)
                    new_hops = hops + [hop]

                    # Calculate new confidence with decay
                    new_confidence = confidence * edge_weight * self.CONFIDENCE_DECAY
                    expansions += 1

                    # Check if goal reached
                    if goal and self._matches_goal(next_id, goal):
                        path = self._build_path(
                            start_id, next_id, new_hops, new_confidence
                        )
                        paths.append(path)
                    elif return_partial_paths:
                        partial_paths.append(
                            self._build_path(
                                start_id,
                                next_id,
                                new_hops,
                                new_confidence,
                                goal=goal,
                                partial=True,
                            )
                        )

                    # Add to next frontier
                    new_visited = visited | {next_id}
                    next_frontier.append(
                        (next_id, new_hops, new_confidence, new_visited)
                    )

            next_frontier.sort(
                key=lambda item: (
                    -float(item[2]),
                    len(item[1]),
                    item[0],
                )
            )
            frontier = next_frontier[:max_frontier_width]

            # Early exit if no more nodes
            if not frontier or expansions >= max_total_expansions:
                break

        deduped: Dict[str, ReasoningPath] = {}
        for path in paths:
            existing = deduped.get(path.path_id)
            if existing is None or path.confidence > existing.confidence:
                deduped[path.path_id] = path

        if not deduped and return_partial_paths:
            partial_paths.sort(key=lambda p: (-p.confidence, p.path_length, p.path_id))
            for path in partial_paths[: self.MAX_PATHS_PER_QUERY]:
                existing = deduped.get(path.path_id)
                if existing is None or path.confidence > existing.confidence:
                    deduped[path.path_id] = path

        return list(deduped.values())

    def _get_outgoing_edges(
        self,
        node_id: str,
        edge_types: Set[str],
    ) -> List[EdgeModel]:
        """Fetch outgoing edges from cache or database."""

        cache_key = f"{node_id}:{sorted(edge_types)}"

        if cache_key not in self._edge_cache:
            # Query database
            if self.graph_id:
                edges = (
                    self.session.query(EdgeModel)
                    .filter(
                        EdgeModel.tenant_id == self.tenant_id,
                        EdgeModel.graph_id == self.graph_id,
                        EdgeModel.src_node_id == node_id,
                        EdgeModel.kind.in_(edge_types),
                    )
                    .all()
                )
            else:
                edges = (
                    self.session.query(EdgeModel)
                    .filter(
                        EdgeModel.tenant_id == self.tenant_id,
                        EdgeModel.src_node_id == node_id,
                        EdgeModel.kind.in_(edge_types),
                    )
                    .all()
                )

            self._edge_cache[cache_key] = edges

        return self._edge_cache[cache_key]

    def _normalized_edge_weight(self, edge: EdgeModel) -> float:
        """Convert stored fixed-point edge weights into [0, 1]."""
        raw_weight = float(edge.weight or 0.0)
        if raw_weight > 1.0:
            raw_weight = raw_weight / 1e9
        return max(0.0, min(1.0, raw_weight))

    def _build_hop(
        self,
        from_id: str,
        edge: EdgeModel,
        to_id: str,
    ) -> Hop:
        """Construct a Hop object from edge data."""

        from_node = self._get_node(from_id)
        to_node = self._get_node(to_id)

        reasoning = self._generate_hop_reasoning(from_node, edge, to_node)

        return Hop(
            edge_id=str(edge.edge_id),
            node_id=from_id,
            node_label=from_node.get("label", "Unknown") if from_node else "Unknown",
            edge_type=edge.kind,
            edge_weight=self._normalized_edge_weight(edge),
            edge_properties=edge.meta or {},
            next_node_id=to_id,
            next_node_label=to_node.get("label", "Unknown") if to_node else "Unknown",
            reasoning=reasoning,
        )

    def _get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Fetch node from cache or database."""

        if node_id not in self._node_cache:
            node = (
                self.session.query(NodeModel)
                .filter(
                    NodeModel.tenant_id == self.tenant_id,
                    NodeModel.node_id == node_id,
                )
                .first()
            )

            if node:
                anchor = getattr(node, "anchor_json", None) or {}
                label = (
                    anchor.get("filename")
                    or getattr(node, "block_id", None)
                    or getattr(node, "raw_id", None)
                    or str(getattr(node, "node_id", node_id))
                )
                self._node_cache[node_id] = {
                    "node_id": str(node.node_id),
                    "label": str(label)[:100],
                    "text": json.dumps(anchor, sort_keys=True) if anchor else str(label),
                    "cognitive_type": getattr(node, "cognitive_type", None),
                    "galaxy_id": getattr(node, "galaxy_id", None),
                }
            else:
                self._node_cache[node_id] = None

        return self._node_cache[node_id]

    def _generate_hop_reasoning(
        self,
        from_node: Optional[Dict[str, Any]],
        edge: EdgeModel,
        to_node: Optional[Dict[str, Any]],
    ) -> str:
        """Generate human-readable reasoning for this hop."""

        from_label = from_node.get("label", "Unknown") if from_node else "Unknown"
        to_label = to_node.get("label", "Unknown") if to_node else "Unknown"
        edge_type = edge.kind

        templates = {
            "implies": f"{from_label} implies {to_label}",
            "causes": f"{from_label} causes {to_label}",
            "enables": f"{from_label} enables {to_label}",
            "leads_to": f"{from_label} leads to {to_label}",
            "supports": f"{from_label} supports {to_label}",
            "contradicts": f"{from_label} contradicts {to_label}",
            "part_of": f"{from_label} is part of {to_label}",
            "related_to": f"{from_label} is related to {to_label}",
            "temporal_before": f"{from_label} happened before {to_label}",
            "temporal_after": f"{from_label} happened after {to_label}",
        }

        return templates.get(edge_type, f"{from_label} → {edge_type} → {to_label}")

    def _matches_goal(self, node_id: str, goal: str) -> bool:
        """Check if node semantically matches the goal."""

        node = self._get_node(node_id)
        if not node:
            return False

        goal_lower = goal.lower()
        text_lower = (node.get("text") or "").lower()
        label_lower = (node.get("label") or "").lower()

        # Direct substring match
        if goal_lower in text_lower or goal_lower in label_lower:
            return True

        # Keyword matching
        goal_keywords = set(goal_lower.split())
        text_keywords = set(text_lower.split())

        # If >50% of goal keywords present, consider it a match
        if goal_keywords:
            overlap = len(goal_keywords & text_keywords)
            if overlap / len(goal_keywords) >= 0.5:
                return True

        return False

    def _build_path(
        self,
        start_id: str,
        end_id: str,
        hops: List[Hop],
        confidence: float,
        *,
        goal: Optional[str] = None,
        partial: bool = False,
    ) -> ReasoningPath:
        """Construct a ReasoningPath from traversal results."""

        # Generate unique path ID
        path_components = [start_id] + [hop.next_node_id for hop in hops]
        path_hash = hashlib.sha256(
            json.dumps(path_components, sort_keys=True).encode()
        ).hexdigest()[:12]

        # Build explanation
        explanation_parts = [
            f"Starting from: {hops[0].node_label if hops else start_id}"
        ]
        for i, hop in enumerate(hops, 1):
            explanation_parts.append(
                f"  {i}. {hop.reasoning} (confidence: {hop.edge_weight:.2f})"
            )
        explanation_parts.append(
            f"Final conclusion: {hops[-1].next_node_label if hops else end_id}"
        )
        if partial:
            explanation_parts.append(
                f"Traversal stopped before exact goal match; best partial route toward '{goal or 'graph goal'}' returned."
            )
        explanation_parts.append(f"Overall confidence: {confidence:.2f}")

        return ReasoningPath(
            path_id=f"path_{path_hash}",
            start_node=start_id,
            end_node=end_id,
            hops=tuple(hops),
            confidence=confidence,
            path_length=len(hops),
            explanation="\n".join(explanation_parts),
            metadata={
                "traversal_timestamp": datetime.now(timezone.utc).isoformat(),
                "tenant_id": self.tenant_id,
                "graph_id": self.graph_id,
                "goal": goal or "",
                "partial": partial,
                "node_ids": [start_id] + [hop.next_node_id for hop in hops],
                "edge_ids": [hop.edge_id for hop in hops],
            },
        )

    def find_causal_chain(
        self,
        cause_node_id: str,
        effect_node_id: str,
        max_hops: int = 3,
    ) -> Optional[ReasoningPath]:
        """
        Find a causal path from cause to effect.

        Specialized traversal for "Why did X happen?" questions.
        """
        paths = self.traverse(
            start_node_ids=[cause_node_id],
            goal=effect_node_id,
            max_hops=max_hops,
            edge_types={"causes", "leads_to", "implies", "enables"},
        )

        return paths[0] if paths else None

    def find_explanations(
        self,
        effect_node_id: str,
        max_hops: int = 2,
    ) -> List[ReasoningPath]:
        """
        Find all possible explanations for an effect.

        Walks backwards through causal edges to find root causes.
        """
        # Get nodes that have edges TO the effect node
        incoming_edges = (
            self.session.query(EdgeModel)
            .filter(
                EdgeModel.tenant_id == self.tenant_id,
                EdgeModel.dst_node_id == effect_node_id,
                EdgeModel.kind.in_({"causes", "leads_to", "implies"}),
            )
            .all()
        )

        cause_node_ids = [str(edge.src_node_id) for edge in incoming_edges]

        explanations = []
        for cause_id in cause_node_ids:
            path = self.find_causal_chain(cause_id, effect_node_id, max_hops)
            if path:
                explanations.append(path)

        return sorted(explanations, key=lambda p: p.confidence, reverse=True)
