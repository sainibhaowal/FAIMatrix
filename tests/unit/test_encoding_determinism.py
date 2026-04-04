"""Unit tests for encoding determinism.

Same block twice → identical v_native and vector_hash.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Setup paths
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.contracts.types import BlockAnchor, EvidenceBlock  # noqa: E402
from encoding.text_vectorizer import (  # noqa: E402
    build_ngram_vector,
    compute_text_stats,
    l2_normalize,
    normalize_text,
    vectorize_block,
    vectorize_text,
)
from encoding.vector_schema import VECTOR_DIMENSION  # noqa: E402


class TestEncodingDeterminism:
    """Unit tests for encoding determinism."""

    def test_normalize_text_deterministic(self):
        """Text normalization should be deterministic."""
        text = "  Hello   World  \n\t Test  "

        result1 = normalize_text(text)
        result2 = normalize_text(text)

        assert result1 == result2
        assert result1 == "hello world test"

    def test_ngram_vector_deterministic(self):
        """N-gram vector should be deterministic."""
        text = "hello world test"

        vec1 = build_ngram_vector(text)
        vec2 = build_ngram_vector(text)

        assert vec1 == vec2

    def test_l2_normalize_deterministic(self):
        """L2 normalization should be deterministic."""
        vector = [1.0, 2.0, 3.0, 4.0]

        norm1 = l2_normalize(vector)
        norm2 = l2_normalize(vector)

        assert norm1 == norm2

    def test_stats_deterministic(self):
        """Stats computation should be deterministic."""
        text = "Hello World! This is a test with 123 numbers."

        stats1 = compute_text_stats(text)
        stats2 = compute_text_stats(text)

        assert stats1 == stats2

    def test_vectorize_text_deterministic(self):
        """Text vectorization should be deterministic."""
        text = "This is a test for deterministic encoding."

        v_res1 = vectorize_text(text)
        v_res2 = vectorize_text(text)
        v1, s1, o1 = v_res1.v_native, v_res1.stats, v_res1.opp_signature
        v2, s2, o2 = v_res2.v_native, v_res2.stats, v_res2.opp_signature

        assert v1 == v2
        assert s1 == s2
        assert o1 == o2

    def test_vectorize_block_deterministic(self):
        """Block vectorization should produce identical hashes."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=50)
        block = EvidenceBlock.create(
            raw_id="test_raw",
            anchor=anchor,
            content="Deterministic encoding test content.",
        )

        vec1 = vectorize_block(block)
        vec2 = vectorize_block(block)

        # v_native should be identical
        assert vec1.v_native == vec2.v_native

        # vector_hash should be identical
        assert vec1.vector_hash == vec2.vector_hash

    def test_different_content_different_hash(self):
        """Different content should produce different hashes."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=50)

        block1 = EvidenceBlock.create(
            raw_id="test_raw",
            anchor=anchor,
            content="Content A",
        )
        block2 = EvidenceBlock.create(
            raw_id="test_raw",
            anchor=anchor,
            content="Content B",
        )

        vec1 = vectorize_block(block1)
        vec2 = vectorize_block(block2)

        assert vec1.vector_hash != vec2.vector_hash

    def test_whitespace_normalization(self):
        """Different whitespace should normalize to same v_native."""
        # Test that normalized text produces same n-gram features
        from encoding.text_vectorizer import vectorize_text

        v_res1 = vectorize_text("hello   world")
        v_res2 = vectorize_text("hello world")
        v1 = v_res1.v_native
        v2 = v_res2.v_native

        # After normalization, v_native should be identical
        assert v1 == v2

    def test_case_normalization(self):
        """Different case should normalize to same v_native."""
        # Test that normalized text produces same n-gram features
        from encoding.text_vectorizer import vectorize_text

        v_res1 = vectorize_text("Hello World")
        v_res2 = vectorize_text("HELLO WORLD")
        v1 = v_res1.v_native
        v2 = v_res2.v_native

        # After normalization, v_native should be identical
        assert v1 == v2

    def test_unicode_normalization(self):
        """Unicode should normalize consistently."""
        # café with combining acute vs precomposed
        text1 = "cafe\u0301"  # e + combining acute
        text2 = "café"  # precomposed é

        norm1 = normalize_text(text1)
        norm2 = normalize_text(text2)

        assert norm1 == norm2

    def test_empty_text_deterministic(self):
        """Empty text should produce consistent result."""
        v_res1 = vectorize_text("")
        v_res2 = vectorize_text("")
        v1, s1, o1 = v_res1.v_native, v_res1.stats, v_res1.opp_signature
        v2, s2, o2 = v_res2.v_native, v_res2.stats, v_res2.opp_signature

        assert v1 == v2
        assert len(v1) == VECTOR_DIMENSION

    def test_repeated_vectorization_stable(self):
        """Repeated vectorization should be stable."""
        text = "Test stability across many iterations."

        hashes = set()
        for _ in range(100):
            v_res = vectorize_text(text)
            v = v_res.v_native
            # Use tuple for hashability
            hashes.add(tuple(v[:10]))  # Just first 10 for speed

        # All should be identical
        assert len(hashes) == 1
