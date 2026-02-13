"""FAIM-Native Text Vectorizer.

Converts EvidenceBlocks to FAIMVectors using deterministic hashed n-gram vectors.

NO ML MODELS. NO RANDOMNESS.

Algorithm:
1. Normalize text (whitespace collapse, NFC, lowercase)
2. Build hashed n-gram vector (3,4,5-grams → 256 buckets)
3. L2 normalize
4. Add numeric stats (length, word_count, digit_ratio, etc.)
5. Build opposition signature
"""

from __future__ import annotations

import hashlib
import math
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import (  # noqa: F401
        BlockAnchor,
        EvidenceBlock,
    )
    from faim.Faim_Native.encoding.vector_schema import VECTOR_DIMENSION, FAIMVector
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import EvidenceBlock
    from encoding.vector_schema import VECTOR_DIMENSION, FAIMVector


# Constants
NGRAM_SIZES = (3, 4, 5)  # Character n-gram sizes
NGRAM_BUCKETS = 240  # Buckets for n-gram features (leaving 16 for stats)
STAT_FEATURES = 16  # Numeric stat features


# -----------------------------------------------------------------------------
# Text Normalization (Deterministic)
# -----------------------------------------------------------------------------


def normalize_text(text: str, lowercase: bool = True) -> str:
    """Normalize text deterministically.

    Args:
        text: Input text.
        lowercase: Whether to lowercase.

    Returns:
        Normalized text.
    """
    # Unicode NFC normalization
    text = unicodedata.normalize("NFC", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    # Strip leading/trailing
    text = text.strip()

    # Lowercase
    if lowercase:
        text = text.lower()

    return text


# -----------------------------------------------------------------------------
# Hashed N-Gram Vectorization
# -----------------------------------------------------------------------------


def _hash_ngram(ngram: str, num_buckets: int) -> int:
    """Hash an n-gram to a bucket index."""
    h = hashlib.sha256(ngram.encode("utf-8")).digest()
    # Use first 4 bytes as unsigned int
    value = int.from_bytes(h[:4], "big", signed=False)
    return value % num_buckets


def build_ngram_vector(text: str, dimension: int = NGRAM_BUCKETS) -> List[float]:
    """Build hashed n-gram vector from text.

    Args:
        text: Normalized text.
        dimension: Number of buckets.

    Returns:
        Un-normalized vector of counts.
    """
    vector = [0.0] * dimension

    if not text:
        return vector

    # Generate n-grams for each size
    for n in NGRAM_SIZES:
        if len(text) < n:
            continue

        for i in range(len(text) - n + 1):
            ngram = text[i : i + n]
            bucket = _hash_ngram(ngram, dimension)
            vector[bucket] += 1.0

    return vector


def l2_normalize(vector: List[float]) -> List[float]:
    """L2 normalize a vector."""
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


# -----------------------------------------------------------------------------
# Numeric Stats Features
# -----------------------------------------------------------------------------


def compute_text_stats(text: str) -> Dict[str, float]:
    """Compute numeric statistics from text.

    Args:
        text: Normalized text.

    Returns:
        Dictionary of stat names to values.
    """
    if not text:
        return {
            "length": 0.0,
            "word_count": 0.0,
            "avg_word_len": 0.0,
            "digit_ratio": 0.0,
            "alpha_ratio": 0.0,
            "punct_ratio": 0.0,
            "upper_ratio": 0.0,
            "space_ratio": 0.0,
            "unique_word_ratio": 0.0,
            "entropy_proxy": 0.0,
            "line_count": 0.0,
            "sentence_proxy": 0.0,
            "number_count": 0.0,
            "special_char_ratio": 0.0,
            "vowel_ratio": 0.0,
            "consonant_ratio": 0.0,
        }

    length = len(text)
    words = text.split()
    word_count = len(words)
    unique_words = set(words)

    # Character counts
    digit_count = sum(1 for c in text if c.isdigit())
    alpha_count = sum(1 for c in text if c.isalpha())
    punct_count = sum(1 for c in text if c in ".,!?;:\"'()[]{}/-")
    upper_count = sum(1 for c in text if c.isupper())
    space_count = sum(1 for c in text if c.isspace())

    # Vowels and consonants
    vowels = set("aeiouAEIOU")
    consonants = set("bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ")
    vowel_count = sum(1 for c in text if c in vowels)
    consonant_count = sum(1 for c in text if c in consonants)

    # Lines and sentences
    line_count = text.count("\n") + 1
    sentence_count = len(re.findall(r"[.!?]+", text))

    # Number tokens
    number_count = len(re.findall(r"\b\d+\.?\d*\b", text))

    # Special characters
    special_count = sum(1 for c in text if not c.isalnum() and not c.isspace())

    # Entropy proxy (unique chars / length)
    unique_chars = len(set(text))
    entropy_proxy = unique_chars / length if length > 0 else 0.0

    return {
        "length": min(length / 10000.0, 1.0),  # Normalize to 0-1
        "word_count": min(word_count / 2000.0, 1.0),
        "avg_word_len": min(
            (sum(len(w) for w in words) / word_count / 20.0 if word_count > 0 else 0.0),
            1.0,
        ),
        "digit_ratio": digit_count / length if length > 0 else 0.0,
        "alpha_ratio": alpha_count / length if length > 0 else 0.0,
        "punct_ratio": punct_count / length if length > 0 else 0.0,
        "upper_ratio": upper_count / length if length > 0 else 0.0,
        "space_ratio": space_count / length if length > 0 else 0.0,
        "unique_word_ratio": len(unique_words) / word_count if word_count > 0 else 0.0,
        "entropy_proxy": min(entropy_proxy, 1.0),
        "line_count": min(line_count / 100.0, 1.0),
        "sentence_proxy": min(sentence_count / 50.0, 1.0),
        "number_count": min(number_count / 100.0, 1.0),
        "special_char_ratio": min(special_count / length if length > 0 else 0.0, 1.0),
        "vowel_ratio": vowel_count / alpha_count if alpha_count > 0 else 0.0,
        "consonant_ratio": consonant_count / alpha_count if alpha_count > 0 else 0.0,
    }


def stats_to_vector(stats: Dict[str, float]) -> List[float]:
    """Convert stats dict to fixed-order vector."""
    # Fixed key order for determinism
    keys = [
        "length",
        "word_count",
        "avg_word_len",
        "digit_ratio",
        "alpha_ratio",
        "punct_ratio",
        "upper_ratio",
        "space_ratio",
        "unique_word_ratio",
        "entropy_proxy",
        "line_count",
        "sentence_proxy",
        "number_count",
        "special_char_ratio",
        "vowel_ratio",
        "consonant_ratio",
    ]
    return [stats.get(k, 0.0) for k in keys]


# -----------------------------------------------------------------------------
# Opposition Signature
# -----------------------------------------------------------------------------


def build_opp_signature(
    ngram_vector: List[float],
    stats: Dict[str, float],
) -> Dict[str, float]:
    """Build opposition signature for antisym operations.

    The signature captures key properties of the vector for
    later use in opposition/antisymmetric operations.

    Args:
        ngram_vector: L2-normalized n-gram vector.
        stats: Text statistics.

    Returns:
        Opposition signature dictionary.
    """
    # Vector norm (should be ~1 after L2 norm, but may vary for empty)
    norm = math.sqrt(sum(v * v for v in ngram_vector))

    # Density (non-zero ratio)
    nonzero = sum(1 for v in ngram_vector if v != 0.0)
    density = nonzero / len(ngram_vector) if ngram_vector else 0.0

    # Max and mean of non-zero
    nonzero_vals = [v for v in ngram_vector if v != 0.0]
    max_val = max(nonzero_vals) if nonzero_vals else 0.0
    mean_val = sum(nonzero_vals) / len(nonzero_vals) if nonzero_vals else 0.0

    # Top-k bucket indices (for sparse comparison)
    indexed = [(i, v) for i, v in enumerate(ngram_vector)]
    indexed.sort(key=lambda x: -x[1])
    top_5 = [float(i) / len(ngram_vector) for i, _ in indexed[:5]]

    return {
        "norm": round(norm, 6),
        "density": round(density, 6),
        "max_val": round(max_val, 6),
        "mean_val": round(mean_val, 6),
        "length": round(stats.get("length", 0.0), 6),
        "entropy": round(stats.get("entropy_proxy", 0.0), 6),
        "top_0": round(top_5[0] if len(top_5) > 0 else 0.0, 6),
        "top_1": round(top_5[1] if len(top_5) > 1 else 0.0, 6),
        "top_2": round(top_5[2] if len(top_5) > 2 else 0.0, 6),
    }


@dataclass(frozen=True)
class VectorizationResult:
    """Result of text vectorization."""

    v_native: List[float]
    stats: Dict[str, float]
    opp_signature: Dict[str, float]


def vectorize_text(text: str) -> VectorizationResult:
    """Convert text to FAIM-native vector.

    Args:
        text: Raw text content.

    Returns:
        VectorizationResult object.
    """
    # Normalize
    normalized = normalize_text(text)

    # Build n-gram vector
    ngram_vector = build_ngram_vector(normalized, NGRAM_BUCKETS)

    # L2 normalize n-gram part
    ngram_normalized = l2_normalize(ngram_vector)

    # Compute stats
    stats = compute_text_stats(normalized)
    stats_vector = stats_to_vector(stats)

    # Combine: ngram (240) + stats (16) = 256
    v_native = ngram_normalized + stats_vector

    assert (  # nosec B101 - Contract enforcement, not production runtime check
        len(v_native) == VECTOR_DIMENSION
    ), f"Expected {VECTOR_DIMENSION}, got {len(v_native)}"

    # Build opposition signature
    opp_signature = build_opp_signature(ngram_normalized, stats)

    return VectorizationResult(
        v_native=v_native, stats=stats, opp_signature=opp_signature
    )


def vectorize_block(
    block: EvidenceBlock,
    residual: float = 0.0,
) -> FAIMVector:
    """Convert an EvidenceBlock to a FAIMVector.

    Args:
        block: The evidence block to vectorize.
        residual: Novelty proxy (default 0.0 for Stage-3).

    Returns:
        FAIMVector with computed v_native and hash.
    """
    v_native: List[float]
    opp_signature: Dict[str, float]

    # Route IMAGE_STUB blocks through explicit OCR-stub feature schema.
    try:
        from encoding.OCR.ocr_features import (
            extract_ocr_stub_signature,
            extract_ocr_stub_vector,
            is_image_stub,
        )
    except Exception:  # pragma: no cover - optional wiring fallback
        is_image_stub = None  # type: ignore[assignment]

    if is_image_stub is not None and is_image_stub(block):
        v_native = extract_ocr_stub_vector(block.anchor, block.content)
        opp_signature = extract_ocr_stub_signature(block.anchor)
    else:
        # Vectorize textual content (default path).
        v_res = vectorize_text(block.content)
        v_native = v_res.v_native
        opp_signature = v_res.opp_signature

    return FAIMVector.create(
        raw_id=block.raw_id,
        block_id=str(block.id),
        block_type=block.block_type,
        anchor=block.anchor,
        v_native=v_native,
        opp_signature=opp_signature,
        residual=residual,
        level=0,  # Atoms are level 0
        extractor="faim_native_v1",
        confidence=block.confidence,
    )


def vectorize_blocks(blocks: List[EvidenceBlock]) -> List[FAIMVector]:
    """Vectorize multiple blocks.

    Args:
        blocks: List of EvidenceBlocks.

    Returns:
        List of FAIMVectors in same order.
    """
    return [vectorize_block(block) for block in blocks]


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    "normalize_text",
    "build_ngram_vector",
    "l2_normalize",
    "compute_text_stats",
    "build_opp_signature",
    "vectorize_text",
    "vectorize_block",
    "vectorize_blocks",
]
