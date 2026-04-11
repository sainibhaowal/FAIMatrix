"""Runtime synonym expansion using embedded WordNet data.

Loads from data/wordnet_synonyms.json.gz — zero runtime dependencies.
If data file is missing, gracefully falls back to original text (FAIM still works).

Thread-safe singleton loading pattern.
"""

import gzip
import json
import threading
from pathlib import Path
from typing import Dict, Optional, Set

# Path to embedded synonym data
_DATA_PATH = Path(__file__).parent / "data" / "wordnet_synonyms.json.gz"

# Singleton state (thread-safe)
_synonyms: Optional[Dict[str, list]] = None
_lock = threading.Lock()
_AVAILABLE: Optional[bool] = None


def _load() -> bool:
    """
    Lazy-load synonym data. Thread-safe.

    Returns:
        True if data successfully loaded, False otherwise
    """
    global _synonyms, _AVAILABLE

    # Check if already determined
    if _AVAILABLE is not None:
        return _AVAILABLE

    # Lock and load
    with _lock:
        # Double-check after acquiring lock
        if _AVAILABLE is not None:
            return _AVAILABLE

        try:
            with gzip.open(_DATA_PATH, "rt", encoding="utf-8") as f:
                _synonyms = json.load(f)
            _AVAILABLE = True
        except (FileNotFoundError, gzip.BadGzipFile, json.JSONDecodeError, OSError):
            # Data file missing or corrupted — graceful fallback
            _synonyms = {}
            _AVAILABLE = False

    return _AVAILABLE


def is_available() -> bool:
    """
    Check if WordNet synonym data is available.

    Returns:
        True if data loaded successfully, False if missing or corrupted
    """
    return _load()


def get_synonyms(word: str) -> Set[str]:
    """
    Return set of synonyms for a word.

    Args:
        word: Word to look up (case-insensitive)

    Returns:
        Set of synonym strings, or empty set if unavailable or no synonyms
    """
    if not _load():
        return set()
    return set(_synonyms.get(word.lower(), []))


def expand_synonyms_text(text: str, max_synonyms_per_word: int = 5) -> str:
    """
    Expand text with WordNet synonyms.

    Appends synonyms after each word. If WordNet data unavailable,
    returns original text unchanged (graceful fallback).

    Order of words is preserved: [word, syn1, syn2, ...] for each word.

    Args:
        text: Lowercased input text (must be pre-lowercased by normalize_text)
        max_synonyms_per_word: Max synonyms to append per word (cap prevents over-expansion)

    Returns:
        Text with synonyms expanded, or original text if data unavailable
    """
    if not _load() or not _synonyms:
        return text  # Graceful fallback — return original

    tokens = text.split()
    expanded = []

    for token in tokens:
        # Add the original word
        expanded.append(token)

        # Look up synonyms (if any)
        syns = _synonyms.get(token, [])
        if syns:
            # Take top N synonyms (already sorted alphabetically from builder)
            # Alphabetic sort ensures determinism
            expanded.extend(syns[:max_synonyms_per_word])

    return " ".join(expanded)
