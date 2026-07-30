"""Enhanced Cortex turn planner with multi-hop reasoning and decomposition.

Phase 2: Advanced planning with query breakdown and multi-hop strategy.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Tuple

from .schemas import CortexTaskType

# Import reasoning engine
try:
    from faim.Faim_Native.core.reasoning.paths import PathConstraints, PathOptimizer
except (ImportError, RuntimeError, ModuleNotFoundError):
    from core.reasoning.paths import PathConstraints, PathOptimizer


class QueryComplexity(Enum):
    """Classification of query complexity."""

    SIMPLE = "simple"  # Single fact lookup
    COMPOUND = "compound"  # Multiple related facts
    COMPLEX = "complex"  # Requires reasoning/inference
    EXPLORATORY = "exploratory"  # Open-ended investigation


@dataclass(frozen=True)
class SubQuery:
    """A decomposed sub-query with execution metadata."""

    id: str
    text: str
    query_type: str
    priority: int
    depends_on: List[str] = field(default_factory=list)
    expected_output: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlannedTurn:
    """Enhanced planned turn with reasoning strategy."""

    task_type: CortexTaskType
    goal: str
    complexity: QueryComplexity

    # Multi-hop reasoning
    enable_multi_hop: bool = False
    max_hops: int = 1
    traversal_goal: str = ""

    # Query decomposition
    sub_queries: Tuple[SubQuery, ...] = field(default_factory=tuple)
    requires_synthesis: bool = False

    # Execution strategy
    parallel_execution: bool = False
    execution_order: List[str] = field(default_factory=list)

    # Constraints
    constraints: PathConstraints = field(default_factory=PathConstraints)

    # Source reliability requirements
    min_source_reliability: float = 0.5
    require_multiple_sources: bool = False


class QueryDecomposer:
    """Decomposes complex queries into executable sub-queries."""

    # Pattern matchers for complex queries
    COMPLEX_PATTERNS = {
        "comparison": {
            "patterns": [
                r"compare\s+(.+?)\s+(?:and|with|vs|versus)\s+(.+)",
                r"(?:what is|what's)?\s*(?:the)?\s*difference\s+between\s+(.+?)\s+and\s+(.+)",
                r"how\s+(?:does|do)\s+(.+?)\s+compare\s+(?:to|with)\s+(.+)",
            ],
            "task_type": CortexTaskType.compare,
        },
        "causal_analysis": {
            "patterns": [
                r"(?:why|what caused|reason for|explain)\s+(?:did|has|is)?\s*(.+?)(?:\?|$)",
                r"(?:how|what)\s+(?:caused|led to|resulted in)\s+(.+)",
                r"what\s+is\s+the\s+(?:cause|reason)\s+(?:of|for)\s+(.+)",
            ],
            "task_type": CortexTaskType.investigate,
        },
        "trend_analysis": {
            "patterns": [
                r"(?:trend|pattern|history|progression)\s+(?:of|in|for)?\s+(.+)",
                r"how\s+has\s+(.+?)\s+(?:changed|evolved|progressed)",
                r"(?:show|plot|chart)\s+(.+?)\s+(?:over|through)\s+time",
            ],
            "task_type": CortexTaskType.timeline,
        },
        "ranking": {
            "patterns": [
                r"(?:rank|order|list)\s+(?:the)?\s*(?:top|best|worst)?\s*(\d+)?\s*(.+)",
                r"what\s+(?:are|is)\s+the\s+(?:top|best|worst)\s+(\d+)?\s*(.+)",
            ],
            "task_type": CortexTaskType.answer,
        },
        "exploratory": {
            "patterns": [
                r"(?:tell me about|explain|describe)\s+(.+)",
                r"what\s+(?:do we know|is known)\s+about\s+(.+)",
                r"(?:summarize|overview)\s+(?:of)?\s+(.+)",
            ],
            "task_type": CortexTaskType.answer,
        },
    }

    def __init__(self):
        self._compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns for efficiency."""
        compiled = {}
        for query_type, config in self.COMPLEX_PATTERNS.items():
            compiled[query_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in config["patterns"]
            ]
        return compiled

    def analyze_complexity(self, query_text: str) -> QueryComplexity:
        """Determine query complexity."""
        text = query_text.lower()

        # Check for multi-part indicators
        multi_part_indicators = [
            " and ",
            " but ",
            " however ",
            " also ",
            " furthermore",
            " moreover",
            " in addition",
            " besides",
        ]

        part_count = sum(1 for ind in multi_part_indicators if ind in text)

        # Check for question words
        question_words = ["why", "how", "explain", "compare", "analyze"]
        has_complex_question = any(word in text for word in question_words)

        # Classify
        if part_count == 0 and not has_complex_question:
            return QueryComplexity.SIMPLE
        elif part_count <= 1 and not has_complex_question:
            return QueryComplexity.COMPOUND
        elif has_complex_question or part_count >= 2:
            return QueryComplexity.COMPLEX
        else:
            return QueryComplexity.EXPLORATORY

    def decompose(self, query_text: str) -> List[SubQuery]:
        """
        Decompose query into sub-queries.

        Returns empty list if query is simple (no decomposition needed).
        """
        text = query_text.strip()
        complexity = self.analyze_complexity(text)

        # Simple queries don't need decomposition
        if complexity == QueryComplexity.SIMPLE:
            return []

        sub_queries = []

        # Try to match complex patterns
        for query_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    sub_queries = self._create_subqueries_from_match(
                        query_type, match, text
                    )
                    return sub_queries

        # Fallback: split on conjunctions
        return self._split_on_conjunctions(text)

    def _create_subqueries_from_match(
        self,
        query_type: str,
        match: re.Match,
        original_text: str,
    ) -> List[SubQuery]:
        """Create sub-queries from regex match."""
        groups = match.groups()

        sub_queries = []

        if query_type == "comparison" and len(groups) >= 2:
            # Compare X and Y → [What is X?, What is Y?, How do they differ?]
            left, right = groups[0], groups[1]
            sub_queries = [
                SubQuery(
                    id="sq_001",
                    text=f"What is {left}?",
                    query_type="fact_retrieval",
                    priority=1,
                    expected_output=f"Facts about {left}",
                ),
                SubQuery(
                    id="sq_002",
                    text=f"What is {right}?",
                    query_type="fact_retrieval",
                    priority=1,
                    expected_output=f"Facts about {right}",
                ),
                SubQuery(
                    id="sq_003",
                    text=f"What are the key differences between {left} and {right}?",
                    query_type="analysis",
                    priority=2,
                    depends_on=["sq_001", "sq_002"],
                    expected_output="Comparison analysis",
                ),
            ]

        elif query_type == "causal_analysis":
            subject = groups[0] if groups else original_text
            sub_queries = [
                SubQuery(
                    id="sq_001",
                    text=f"What is the current state of {subject}?",
                    query_type="fact_retrieval",
                    priority=1,
                    expected_output=f"Current value/state of {subject}",
                ),
                SubQuery(
                    id="sq_002",
                    text=f"What events or factors are related to {subject}?",
                    query_type="multi_hop",
                    priority=1,
                    expected_output="Related events and factors",
                    constraints={"edge_types": ["causes", "leads_to", "implies"]},
                ),
                SubQuery(
                    id="sq_003",
                    text=f"Analyze: What caused changes in {subject}?",
                    query_type="inference",
                    priority=2,
                    depends_on=["sq_001", "sq_002"],
                    expected_output="Causal analysis",
                ),
            ]

        elif query_type == "trend_analysis":
            subject = groups[0] if groups else original_text
            sub_queries = [
                SubQuery(
                    id="sq_001",
                    text=f"Find all temporal data points for {subject}",
                    query_type="temporal_retrieval",
                    priority=1,
                    expected_output="Time-series data",
                    constraints={"require_timestamps": True},
                ),
                SubQuery(
                    id="sq_002",
                    text=f"Analyze trend: How has {subject} changed over time?",
                    query_type="trend_analysis",
                    priority=2,
                    depends_on=["sq_001"],
                    expected_output="Trend description",
                ),
            ]

        return sub_queries

    def _split_on_conjunctions(self, text: str) -> List[SubQuery]:
        """Fallback: split query on conjunctions."""
        # Simple splitting on "and" for compound queries
        parts = re.split(r"\s+and\s+", text, flags=re.IGNORECASE)

        if len(parts) <= 1:
            return []

        sub_queries = []
        for i, part in enumerate(parts, 1):
            sub_queries.append(
                SubQuery(
                    id=f"sq_{i:03d}",
                    text=part.strip(),
                    query_type="fact_retrieval",
                    priority=1,
                    expected_output="Facts",
                )
            )

        return sub_queries


class EnhancedPlanner:
    """Enhanced planner with multi-hop and decomposition support."""

    def __init__(self):
        self.decomposer = QueryDecomposer()
        self.optimizer = PathOptimizer()

    def plan(
        self,
        query_text: str,
        answer_mode: str,
        confidence: float,
        enable_multi_hop: bool = True,
    ) -> PlannedTurn:
        """
        Create an enhanced plan for the query.

        Args:
            query_text: User's query
            answer_mode: Requested answer mode
            confidence: Current confidence level
            enable_multi_hop: Whether to allow multi-hop reasoning

        Returns:
            PlannedTurn with full execution strategy
        """
        # Base classification
        base_plan = self._base_classify(query_text, answer_mode, confidence)

        # Analyze complexity
        complexity = self.decomposer.analyze_complexity(query_text)

        # Determine if multi-hop needed
        needs_multi_hop = self._needs_multi_hop(query_text, complexity)
        hop_budget = self._compute_hop_budget(
            query_text=query_text,
            complexity=complexity,
            task_type=base_plan.task_type,
            needs_multi_hop=needs_multi_hop,
        )

        # Decompose if complex
        sub_queries = self.decomposer.decompose(query_text)
        requires_synthesis = len(sub_queries) > 1

        # Build enhanced plan
        plan = PlannedTurn(
            task_type=base_plan.task_type,
            goal=base_plan.goal,
            complexity=complexity,
            # Multi-hop settings
            enable_multi_hop=enable_multi_hop and needs_multi_hop,
            max_hops=hop_budget,
            traversal_goal=self._extract_traversal_goal(query_text),
            # Decomposition
            sub_queries=tuple(sub_queries),
            requires_synthesis=requires_synthesis,
            # Execution
            parallel_execution=len(sub_queries) > 1
            and not any(sq.depends_on for sq in sub_queries),
            execution_order=self._compute_execution_order(sub_queries),
            # Constraints
            constraints=self._build_constraints(base_plan.task_type, hop_budget),
            # Source requirements
            min_source_reliability=(
                0.7 if complexity == QueryComplexity.COMPLEX else 0.5
            ),
            require_multiple_sources=complexity == QueryComplexity.EXPLORATORY,
        )

        return plan

    def _max_supported_hops(self) -> int:
        """Return configured max hop ceiling.

        Defaults to 24 for the production claim, but remains configurable so
        larger bounded deployments can opt into deeper traversal explicitly.
        """
        raw = str(os.getenv("FAIM_CORTEX_MAX_HOPS", "24")).strip()
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = 24
        return max(1, min(value, 128))

    def _compute_hop_budget(
        self,
        *,
        query_text: str,
        complexity: QueryComplexity,
        task_type: CortexTaskType,
        needs_multi_hop: bool,
    ) -> int:
        """Estimate a bounded hop budget from query difficulty.

        This is intentionally deterministic. The same query text and task type
        produce the same hop budget unless the configured global cap changes.
        """
        if not needs_multi_hop:
            return 1

        text = query_text.lower()
        max_supported = self._max_supported_hops()

        base_by_complexity = {
            QueryComplexity.SIMPLE: 1,
            QueryComplexity.COMPOUND: 2,
            QueryComplexity.COMPLEX: 6,
            QueryComplexity.EXPLORATORY: 8,
        }
        hop_budget = base_by_complexity.get(complexity, 3)

        indicator_weights = {
            "why": 2,
            "how": 1,
            "because": 2,
            "cause": 2,
            "impact": 2,
            "effect": 2,
            "consequence": 2,
            "timeline": 2,
            "history": 2,
            "sequence": 2,
            "compare": 1,
            "versus": 1,
            "difference": 1,
            "investigate": 3,
            "trace": 3,
            "root": 3,
            "dependency": 3,
            "downstream": 4,
            "upstream": 4,
            "across": 1,
            "through": 1,
            "chain": 2,
        }
        hop_budget += sum(weight for token, weight in indicator_weights.items() if token in text)

        if len(text.split()) >= 12:
            hop_budget += 2
        if len(text.split()) >= 24:
            hop_budget += 2

        if task_type == CortexTaskType.timeline:
            hop_budget = max(hop_budget, 6)
        elif task_type == CortexTaskType.compare:
            hop_budget = max(hop_budget, 4)
        elif task_type == CortexTaskType.contradiction:
            hop_budget = max(hop_budget, 4)
        elif task_type == CortexTaskType.investigate:
            hop_budget = max(hop_budget, 8)

        return max(1, min(hop_budget, max_supported))

    def _base_classify(
        self,
        query_text: str,
        answer_mode: str,
        confidence: float,
    ) -> Any:
        """Use original classification as base."""
        from .planner import classify_turn

        return classify_turn(query_text, answer_mode, confidence)

    def _needs_multi_hop(self, query_text: str, complexity: QueryComplexity) -> bool:
        """Determine if query requires multi-hop reasoning."""
        text = query_text.lower()

        # Explicit causal/reasoning questions need multi-hop
        reasoning_indicators = [
            "why",
            "cause",
            "reason",
            "led to",
            "resulted in",
            "because",
            "explain",
            "how did",
            "what led to",
        ]

        if any(ind in text for ind in reasoning_indicators):
            return True

        # Complex queries benefit from multi-hop
        if complexity in [QueryComplexity.COMPLEX, QueryComplexity.EXPLORATORY]:
            return True

        return False

    def _extract_traversal_goal(self, query_text: str) -> str:
        """Extract what we're looking for in graph traversal."""
        text = query_text.lower()

        # Look for causal goals
        if "why" in text or "cause" in text or "reason" in text:
            return "find_causes"

        if "how" in text and ("happen" in text or "change" in text):
            return "find_mechanism"

        if "impact" in text or "effect" in text or "consequence" in text:
            return "find_effects"

        # Default
        return "find_related"

    def _compute_execution_order(self, sub_queries: List[SubQuery]) -> List[str]:
        """Determine execution order based on dependencies."""
        if not sub_queries:
            return []

        # Topological sort by priority and dependencies
        order = []
        completed = set()

        while len(order) < len(sub_queries):
            # Find queries with no unmet dependencies
            ready = [
                sq
                for sq in sub_queries
                if sq.id not in completed
                and all(dep in completed for dep in sq.depends_on)
            ]

            if not ready:
                # Circular dependency - break by priority
                ready = [sq for sq in sub_queries if sq.id not in completed]

            # Sort by priority
            ready.sort(key=lambda sq: sq.priority)

            # Add to order
            for sq in ready:
                order.append(sq.id)
                completed.add(sq.id)

        return order

    def _build_constraints(
        self,
        task_type: CortexTaskType,
        hop_budget: int,
    ) -> PathConstraints:
        """Build path constraints based on task type."""

        if task_type == CortexTaskType.timeline:
            return PathConstraints(
                max_hops=min(hop_budget, max(6, hop_budget)),
                require_temporal_order=True,
                allowed_edge_types={"temporal_before", "temporal_after", "implies"},
                max_branching_factor=8,
            )

        elif task_type == CortexTaskType.contradiction:
            return PathConstraints(
                max_hops=min(hop_budget, 8),
                allowed_edge_types={"contradicts", "opposes", "disagrees"},
                min_confidence=0.6,
                max_branching_factor=6,
            )

        elif task_type == CortexTaskType.compare:
            return PathConstraints(
                max_hops=min(hop_budget, 12),
                allowed_edge_types={"related_to", "part_of", "similar_to", "contrasts"},
                max_branching_factor=8,
            )

        elif task_type == CortexTaskType.investigate:
            return PathConstraints(
                max_hops=hop_budget,
                allowed_edge_types={
                    "causes",
                    "leads_to",
                    "implies",
                    "enables",
                    "related_to",
                },
                max_branching_factor=10,
            )

        else:
            return PathConstraints(
                max_hops=min(hop_budget, 8),
                max_branching_factor=8,
            )


# Convenience function
def plan_turn_enhanced(
    query_text: str,
    answer_mode: str,
    confidence: float,
    enable_multi_hop: bool = True,
) -> PlannedTurn:
    """Create enhanced plan for a turn."""
    planner = EnhancedPlanner()
    return planner.plan(query_text, answer_mode, confidence, enable_multi_hop)
