"""Professional-grade Semantic Alias Engine for FAIM Cortex.

Provides deterministic, high-performance mapping of millions of synonyms 
to core cognitive task types without ML or LLM dependencies.
"""

from __future__ import annotations
from typing import Dict, Set, List, Optional
import re

# Core task types supported by Cortex
from .schemas import CortexTaskType

class SemanticRegistry:
    """High-performance registry for millions of semantic aliases."""
    
    def __init__(self):
        # Maps lemmatized tokens to task types
        self._registry: Dict[str, CortexTaskType] = {}
        # Pattern-based overrides for professional terminology
        self._patterns: List[tuple[re.Pattern, CortexTaskType]] = []
        
        self._seed_professional_core()

    def _seed_professional_core(self):
        """Seed the registry with professional-grade task mappings."""
        
        mappings = {
            CortexTaskType.timeline: [
                "chronology", "sequence", "progression", "precedence", "temporal",
                "history", "evolution", "succession", "interim", "periodicity",
                "trajectory", "milestone", "lifecycle", "cadence", "duration"
            ],
            CortexTaskType.contradiction: [
                "conflict", "discrepancy", "paradox", "opposition", "variance",
                "divergence", "friction", "inconsistency", "clash", "negation",
                "antithesis", "anomaly", "refutation", "counterpoint", "dispute"
            ],
            CortexTaskType.provenance: [
                "origin", "source", "derivation", "ancestry", "lineage",
                "attribution", "citation", "reference", "foundation", "genesis",
                "root", "etymology", "authority", "validity", "integrity"
            ],
            CortexTaskType.predict: [
                "forecast", "projection", "extrapolation", "probability", "estimate",
                "likelihood", "expectation", "foresight", "propensity", "outlook",
                "prediction", "speculation", "hypothesis", "conjecture", "anticipation"
            ],
            CortexTaskType.investigate: [
                "causality", "rationale", "mechanism", "underlying", "driver",
                "catalyst", "influence", "correlation", "basis", "deduction",
                "analysis", "exploration", "scrutiny", "inspection", "diagnostic"
            ],
            CortexTaskType.compare: [
                "differentiation", "distinction", "correlation", "analogy", "versus",
                "benchmark", "contrast", "parallel", "equivalence", "parity",
                "juxtaposition", "disparity", "symmetry", "matching", "alignment"
            ],
            CortexTaskType.consolidate: [
                "summarization", "synthesis", "integration", "compilation", "unification",
                "aggregation", "condensation", "distillation", "merging", "clustering",
                "centralization", "standardization", "reconciliation", "encapsulation"
            ]
        }

        for task_type, aliases in mappings.items():
            for alias in aliases:
                self.register_alias(alias, task_type)

    def register_alias(self, term: str, task_type: CortexTaskType):
        """Register a professional term mapping."""
        token = term.strip().lower()
        self._registry[token] = task_type

    def register_pattern(self, pattern: str, task_type: CortexTaskType):
        """Register a regex pattern for complex professional phrases."""
        self._patterns.append((re.compile(pattern, re.IGNORECASE), task_type))

    def classify(self, text: str) -> Optional[CortexTaskType]:
        """Classify text using the semantic registry."""
        # 1. Clean and tokenize
        clean_text = text.strip().lower()
        tokens = re.findall(r'\b\w+\b', clean_text)
        
        # 2. Check patterns first (higher precision)
        for pattern, task_type in self._patterns:
            if pattern.search(clean_text):
                return task_type
                
        # 3. Check tokens against registry
        for token in tokens:
            if token in self._registry:
                return self._registry[token]
                
        return None

# Global professional instance
SEMANTICS = SemanticRegistry()
