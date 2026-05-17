"""Implication engine for FAIM reasoning.

Manages logical implication rules and applies them during traversal.
Supports forward chaining (A implies B, know A → conclude B).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class ImplicationRule:
    """
    A logical implication rule: IF conditions THEN conclusion.

    Example:
        IF node.cognitive_type == "event" AND "meeting" in node.text
        THEN galaxy_type = "work"
    """

    rule_id: str
    name: str
    description: str

    # Conditions that must be met
    conditions: Dict[
        str, Any
    ]  # e.g., {"cognitive_type": "event", "keywords": ["meeting"]}

    # What to conclude
    conclusion: Dict[str, Any]  # e.g., {"galaxy_type": "work", "priority": 1}

    # Rule metadata
    confidence: float = 1.0  # How much to trust this rule
    priority: int = 1  # Evaluation order

    def matches(self, node_data: Dict[str, Any]) -> bool:
        """Check if a node matches this rule's conditions."""
        for key, expected in self.conditions.items():
            actual = node_data.get(key)

            if isinstance(expected, list):
                # List condition: any match
                if not any(self._value_matches(actual, exp) for exp in expected):
                    return False
            else:
                # Single value condition
                if not self._value_matches(actual, expected):
                    return False

        return True

    def _value_matches(self, actual: Any, expected: Any) -> bool:
        """Check if actual value matches expected."""
        if actual is None:
            return expected is None

        if isinstance(expected, str) and isinstance(actual, str):
            # Case-insensitive substring match for strings
            return expected.lower() in actual.lower()

        return actual == expected

    def apply(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply rule to get conclusion with confidence."""
        result = dict(self.conclusion)
        result["_rule_confidence"] = self.confidence
        result["_rule_id"] = self.rule_id
        return result


class ImplicationEngine:
    """
    Forward-chaining implication engine.

    Given known facts, derives new facts using implication rules.
    Deterministic and auditable.
    """

    def __init__(self):
        self.rules: List[ImplicationRule] = []
        self._rules_by_priority: Dict[int, List[ImplicationRule]] = {}
        self._load_default_rules()

    def _load_default_rules(self):
        """Load built-in implication rules."""

        default_rules = [
            # Temporal rules
            ImplicationRule(
                rule_id="temp_001",
                name="Before implies earlier",
                description="If A happened before B, A is earlier than B",
                conditions={"edge_type": "temporal_before"},
                conclusion={"temporal_relation": "earlier", "direction": "past"},
                confidence=0.95,
                priority=1,
            ),
            # Causal rules
            ImplicationRule(
                rule_id="cause_001",
                name="Cause implies explanation",
                description="If A causes B, A explains B",
                conditions={"edge_type": "causes"},
                conclusion={"relation_type": "explanation", "direction": "backward"},
                confidence=0.90,
                priority=1,
            ),
            ImplicationRule(
                rule_id="cause_002",
                name="Enablement implies support",
                description="If A enables B, A supports B",
                conditions={"edge_type": "enables"},
                conclusion={"relation_type": "support", "direction": "forward"},
                confidence=0.85,
                priority=2,
            ),
            # Contradiction rules
            ImplicationRule(
                rule_id="contradict_001",
                name="Contradiction implies conflict",
                description="If A contradicts B, there's a conflict to resolve",
                conditions={"edge_type": "contradicts"},
                conclusion={"requires_attention": True, "attention_type": "conflict"},
                confidence=1.0,
                priority=0,  # Highest priority
            ),
            # Cognitive type rules
            ImplicationRule(
                rule_id="cog_001",
                name="Event with date implies temporal",
                description="Event nodes with dates are temporal anchors",
                conditions={
                    "cognitive_type": "event",
                    "has_timestamp": True,
                },
                conclusion={"reasoning_priority": "high", "use_for": "timeline"},
                confidence=0.90,
                priority=1,
            ),
            ImplicationRule(
                rule_id="cog_002",
                name="Prediction implies uncertainty",
                description="Predictions should be flagged as uncertain",
                conditions={"cognitive_type": "prediction"},
                conclusion={"uncertainty_flag": True, "requires_verification": True},
                confidence=0.80,
                priority=2,
            ),
            # Galaxy rules
            ImplicationRule(
                rule_id="galaxy_001",
                name="Same source implies related",
                description="Nodes from same galaxy are likely related",
                conditions={"same_galaxy": True, "different_nodes": True},
                conclusion={"relatedness_boost": 0.2, "coherence_check": True},
                confidence=0.70,
                priority=3,
            ),
        ]

        for rule in default_rules:
            self.add_rule(rule)

    def add_rule(self, rule: ImplicationRule):
        """Add a custom implication rule."""
        self.rules.append(rule)

        if rule.priority not in self._rules_by_priority:
            self._rules_by_priority[rule.priority] = []
        self._rules_by_priority[rule.priority].append(rule)

    def evaluate(self, node_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate all rules against a node and return applicable conclusions.

        Args:
            node_data: Node properties to evaluate

        Returns:
            List of conclusion dictionaries with confidence scores
        """
        conclusions = []

        # Evaluate rules by priority order
        for priority in sorted(self._rules_by_priority.keys()):
            for rule in self._rules_by_priority[priority]:
                if rule.matches(node_data):
                    conclusion = rule.apply(node_data)
                    conclusions.append(conclusion)

        return conclusions

    def chain_forward(
        self,
        initial_facts: List[Dict[str, Any]],
        max_iterations: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Forward chaining: apply rules repeatedly until no new facts.

        Args:
            initial_facts: Starting set of known facts
            max_iterations: Safety limit to prevent infinite loops

        Returns:
            Extended list including all derived facts
        """
        all_facts = list(initial_facts)
        known_hashes = {self._hash_fact(f) for f in all_facts}

        for _iteration in range(max_iterations):
            new_facts_this_round = []

            for fact in all_facts:
                conclusions = self.evaluate(fact)

                for conclusion in conclusions:
                    conclusion_hash = self._hash_fact(conclusion)

                    if conclusion_hash not in known_hashes:
                        new_facts_this_round.append(conclusion)
                        known_hashes.add(conclusion_hash)

            # If no new facts, we're done
            if not new_facts_this_round:
                break

            all_facts.extend(new_facts_this_round)

        return all_facts

    def _hash_fact(self, fact: Dict[str, Any]) -> str:
        """Generate deterministic hash for a fact."""
        import hashlib
        import json

        # Sort keys for determinism
        fact_str = json.dumps(fact, sort_keys=True, default=str)
        return hashlib.sha256(fact_str.encode()).hexdigest()[:16]

    def get_rules_by_type(self, rule_type: str) -> List[ImplicationRule]:
        """Get all rules of a specific type."""
        return [r for r in self.rules if rule_type in r.rule_id]
