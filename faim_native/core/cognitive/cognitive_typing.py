"""FAIM-Native Cognitive Typing: Neural Constellation Classification.

Classifies memory nodes into cognitive types for galaxy visualization.
Each node gets a color based on what kind of memory it represents:

🔵 fact         - Declarative knowledge (what is)
🟢 event        - Episodic experiences (what happened)
🟠 procedure    - Skills and workflows (how to)
🟡 prediction   - Hypotheses and forecasts (what might be)
🔴 contradiction - Conflicts and uncertainty (what conflicts)
⚪ source       - Raw document reference (where from)
🟣 work         - Professional/project context

Galaxy: A document becomes a galaxy center, with its nodes orbiting as colored planets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set

# FAIM-Native lexical imports (zero ML, deterministic)
# Supports both absolute and relative imports for different contexts
try:
    # Try absolute import first (when faim package is installed)
    from faim.Faim_Native.lexical.synonym_expander import get_synonyms, is_available
except (ImportError, RuntimeError, ModuleNotFoundError):
    try:
        # Try relative import from same package
        from lexical.synonym_expander import get_synonyms, is_available
    except (ImportError, RuntimeError, ModuleNotFoundError):
        # Final fallback: direct import with sys.path manipulation
        import sys
        from pathlib import Path

        _lexical_path = Path(__file__).parent.parent.parent / "lexical"
        if str(_lexical_path.parent) not in sys.path:
            sys.path.insert(0, str(_lexical_path.parent))
        from lexical.synonym_expander import get_synonyms, is_available


class CognitiveType(str, Enum):
    """Cognitive classification for memory nodes."""

    FACT = "fact"  # 🔵 Blue: Declarative knowledge
    EVENT = "event"  # 🟢 Green: Episodic experiences
    PROCEDURE = "procedure"  # 🟠 Orange: Skills, workflows
    PREDICTION = "prediction"  # 🟡 Yellow: Hypotheses, forecasts
    CONTRADICTION = "contradiction"  # 🔴 Red: Conflicts, uncertainty
    SOURCE = "source"  # ⚪ White: Document references
    WORK = "work"  # 🟣 Purple: Professional context


# Color mapping for visualization
COGNITIVE_COLORS: Dict[CognitiveType, str] = {
    CognitiveType.FACT: "#3b82f6",  # blue-500
    CognitiveType.EVENT: "#22c55e",  # green-500
    CognitiveType.PROCEDURE: "#f97316",  # orange-500
    CognitiveType.PREDICTION: "#eab308",  # yellow-500
    CognitiveType.CONTRADICTION: "#ef4444",  # red-500
    CognitiveType.SOURCE: "#f8fafc",  # slate-50 (white-ish)
    CognitiveType.WORK: "#a855f7",  # purple-500
}

# Keywords for pattern matching (base patterns)
_BASE_PATTERNS: Dict[CognitiveType, List[str]] = {
    CognitiveType.EVENT: [
        "met",
        "meeting",
        "call",
        "called",
        "visited",
        "saw",
        "happened",
        "on monday",
        "on tuesday",
        "on wednesday",
        "on thursday",
        "on friday",
        "yesterday",
        "last week",
        "last month",
        "in 20",
        "at 1",
        "at 2",
        "at 3",
        "conference",
        "workshop",
        "presentation",
        "demo",
        "launch",
        "release",
        "incident",
        "outage",
        "update",
        "upgrade",
        "deployed",
    ],
    CognitiveType.PROCEDURE: [
        "how to",
        "steps",
        "guide",
        "tutorial",
        "process",
        "workflow",
        "install",
        "configure",
        "setup",
        "deploy",
        "build",
        "run",
        "execute",
        "first",
        "second",
        "third",
        "then",
        "next",
        "finally",
        "documentation",
        "manual",
        "instructions",
        "recipe",
    ],
    CognitiveType.PREDICTION: [
        "will",
        "may",
        "might",
        "could",
        "should",
        "predict",
        "forecast",
        "expect",
        "anticipate",
        "upcoming",
        "future",
        "next quarter",
        "next year",
        "plan",
        "roadmap",
        "estimate",
        "projection",
        "trend",
        "growth",
        "potential",
        "likely",
        "probably",
    ],
    CognitiveType.CONTRADICTION: [
        "but",
        "however",
        "although",
        "despite",
        "conflict",
        "disagree",
        "contradict",
        "vs",
        "versus",
        "instead of",
        "rather than",
        "unclear",
        "uncertain",
        "ambiguous",
        "debatable",
        "disputed",
        "old estimate",
        "previous",
        "outdated",
        "deprecated",
    ],
    CognitiveType.WORK: [
        "project",
        "sprint",
        "milestone",
        "deliverable",
        "task",
        "ticket",
        "client",
        "customer",
        "stakeholder",
        "team",
        "colleague",
        "revenue",
        "sales",
        "budget",
        "cost",
        "profit",
        "kpi",
        "q1",
        "q2",
        "q3",
        "q4",
        "fy20",
        "fiscal",
    ],
}

# Cache for expanded patterns (lazy-loaded, thread-safe via module-level caching)
_EXPANDED_PATTERNS: Optional[Dict[CognitiveType, Set[str]]] = None


def _build_semantic_patterns(
    max_synonyms_per_word: int = 5,
) -> Dict[CognitiveType, Set[str]]:
    """
    Build WordNet-expanded semantic patterns for cognitive classification.

    Expands base keywords with synonyms from embedded WordNet data.
    Falls back to base patterns if WordNet unavailable.

    Args:
        max_synonyms_per_word: Maximum synonyms to add per keyword (prevents over-expansion)

    Returns:
        Dictionary mapping cognitive types to expanded keyword sets
    """
    global _EXPANDED_PATTERNS

    if _EXPANDED_PATTERNS is not None:
        return _EXPANDED_PATTERNS

    # Check if WordNet is available
    wordnet_available = is_available()

    expanded: Dict[CognitiveType, Set[str]] = {}

    for cog_type, keywords in _BASE_PATTERNS.items():
        # Start with base keywords
        expanded_set: Set[str] = set(keywords)

        if wordnet_available:
            # Add WordNet synonyms for each keyword
            for keyword in keywords:
                # Only expand single-word keywords (phrases don't have synonyms)
                if " " not in keyword and len(keyword) > 2:
                    synonyms = get_synonyms(keyword)
                    # Take top N synonyms (sorted alphabetically ensures determinism)
                    limited_syns = list(synonyms)[:max_synonyms_per_word]
                    expanded_set.update(limited_syns)

        expanded[cog_type] = expanded_set

    _EXPANDED_PATTERNS = expanded
    return expanded


def get_semantic_patterns() -> Dict[CognitiveType, Set[str]]:
    """
    Get cached semantic patterns (builds on first call).

    Returns:
        WordNet-expanded patterns for cognitive classification
    """
    return _build_semantic_patterns()


# Backward-compatible alias for existing code
PATTERNS: Dict[CognitiveType, List[str]] = {
    k: list(v) for k, v in _BASE_PATTERNS.items()
}


def classify_cognitive_type(
    text: str, context: Optional[Dict] = None, use_semantic_expansion: bool = True
) -> CognitiveType:
    """Classify text into cognitive type using semantic pattern matching.

    Uses WordNet-expanded patterns for better semantic coverage while maintaining
    FAIM's deterministic, auditable, zero-ML architecture.

    Args:
        text: The text content to classify
        context: Optional context like timestamps, source type, etc.
        use_semantic_expansion: Whether to use WordNet-expanded patterns (default: True)

    Returns:
        CognitiveType enum value
    """
    text_lower = text.lower()
    scores: Dict[CognitiveType, int] = {ct: 0 for ct in CognitiveType}

    # Select pattern source: semantic (WordNet) or base (exact keywords)
    if use_semantic_expansion:
        patterns = get_semantic_patterns()
    else:
        patterns = _BASE_PATTERNS

    # Score based on semantic patterns
    for cog_type, keywords in patterns.items():
        for keyword in keywords:
            if keyword in text_lower:
                scores[cog_type] += 1

    # Boost scores based on context hints
    if context:
        # If has explicit timestamp, boost EVENT
        if context.get("has_timestamp"):
            scores[CognitiveType.EVENT] += 2

        # If from a code/process doc, boost PROCEDURE
        if context.get("source_type") in ["code", "documentation", "manual"]:
            scores[CognitiveType.PROCEDURE] += 2

        # If contains uncertainty markers, boost PREDICTION
        if context.get("uncertainty_score", 0) > 0.5:
            scores[CognitiveType.PREDICTION] += 2

        # If explicitly marked as source reference
        if context.get("is_source_reference"):
            return CognitiveType.SOURCE

    # Check for contradiction patterns (strong signal)
    if scores[CognitiveType.CONTRADICTION] >= 1:
        return CognitiveType.CONTRADICTION

    # Check for event patterns (temporal anchors)
    if scores[CognitiveType.EVENT] >= 2:
        return CognitiveType.EVENT

    # Check for procedure patterns (imperative/how-to)
    if scores[CognitiveType.PROCEDURE] >= 2:
        return CognitiveType.PROCEDURE

    # Check for prediction patterns (future-oriented)
    if scores[CognitiveType.PREDICTION] >= 2:
        return CognitiveType.PREDICTION

    # Check for work patterns (professional context)
    if scores[CognitiveType.WORK] >= 2:
        return CognitiveType.WORK

    # Default: FACT (declarative knowledge is most common)
    return CognitiveType.FACT


# Backward-compatible alias
classify_cognitive_type_semantic = classify_cognitive_type


def generate_galaxy_id(raw_id: str, title_hint: Optional[str] = None) -> str:
    """Generate a galaxy ID from raw document ID.

    Galaxies are named neighborhoods centered on source documents.
    """
    import hashlib

    # Use raw_id to create consistent galaxy identifier
    hash_input = f"{raw_id}:{title_hint or ''}"
    galaxy_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]

    # Create human-readable prefix if title hint available
    if title_hint:
        # Clean title: lowercase, replace spaces with underscores, limit length
        clean_title = re.sub(r"[^\w\s]", "", title_hint.lower())
        clean_title = clean_title.replace(" ", "_")[:20]
        return f"{clean_title}_{galaxy_hash}"

    return f"galaxy_{galaxy_hash}"


def extract_galaxy_title(raw_id: str, text_sample: Optional[str] = None) -> str:
    """Extract a readable title for the galaxy from content.

    Uses filename or first line of content to name the galaxy.
    """
    # Try to extract from raw_id (often a filename)
    if "/" in raw_id:
        filename = raw_id.split("/")[-1]
    else:
        filename = raw_id

    # Clean filename
    clean = re.sub(r"[_\-]", " ", filename)
    clean = re.sub(r"\.\w+$", "", clean)  # Remove extension
    clean = clean.title()

    if clean and len(clean) > 3:
        return clean

    # Fallback to text sample
    if text_sample:
        first_line = text_sample.split("\n")[0][:50]
        return first_line or "Untitled Galaxy"

    return "Untitled Galaxy"


@dataclass
class CognitiveClassification:
    """Result of cognitive classification for a memory node."""

    cognitive_type: CognitiveType
    galaxy_id: str
    galaxy_title: str
    confidence: float  # 0.0 to 1.0
    color: str  # hex color code


def classify_for_constellation(
    text: str, raw_id: str, context: Optional[Dict] = None
) -> CognitiveClassification:
    """Full classification for neural constellation view.

    Returns cognitive type, galaxy assignment, and visualization metadata.
    """
    # Classify the cognitive type
    cog_type = classify_cognitive_type(text, context)

    # Generate galaxy ID and title
    title_hint = extract_galaxy_title(raw_id, text[:200])
    galaxy_id = generate_galaxy_id(raw_id, title_hint)

    # Calculate confidence (simplified)
    confidence = 0.8 if cog_type != CognitiveType.FACT else 0.6

    return CognitiveClassification(
        cognitive_type=cog_type,
        galaxy_id=galaxy_id,
        galaxy_title=title_hint,
        confidence=confidence,
        color=COGNITIVE_COLORS[cog_type],
    )
