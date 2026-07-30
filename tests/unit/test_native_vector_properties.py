"""Unit tests for native vector properties.

Tests dimension, L2 norm stability, no NaN/Inf.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Setup paths
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.contracts.types import BlockAnchor, EvidenceBlock  # noqa: E402
from encoding.text_vectorizer import (  # noqa: E402
    l2_normalize,
    vectorize_block,
    vectorize_text,
)
from encoding.vector_schema import VECTOR_DIMENSION  # noqa: E402


class TestNativeVectorProperties:
    """Unit tests for native vector properties."""

    def test_dimension_is_fixed(self):
        """Vector dimension should always be 256."""
        texts = [
            "short",
            "medium length text with more words",
            "a" * 10000,  # Very long
            "",  # Empty
            "日本語テスト",  # Unicode
            "123456789",  # Numbers only
        ]

        for text in texts:
            v_res = vectorize_text(text)
            v = v_res.v_native
            assert len(v) == VECTOR_DIMENSION, f"Failed for text: {text[:20]}..."

    def test_no_nan_values(self):
        """Vector should never contain NaN."""
        texts = [
            "normal text",
            "",
            "0" * 1000,
            "\n\n\n",
            "🎉🎊🎁",
        ]

        for text in texts:
            v_res = vectorize_text(text)
            v = v_res.v_native
            for i, val in enumerate(v):
                assert not math.isnan(val), f"NaN at index {i} for text: {text[:20]}..."

    def test_no_inf_values(self):
        """Vector should never contain Inf."""
        texts = [
            "normal text",
            "",
            "a" * 100000,  # Very long
            "1" * 100000,  # Many digits
        ]

        for text in texts:
            v_res = vectorize_text(text)
            v = v_res.v_native
            for i, val in enumerate(v):
                assert not math.isinf(val), f"Inf at index {i} for text: {text[:20]}..."

    def test_l2_norm_stable(self):
        """L2 norm of n-gram part should be ~1 (after normalization)."""
        texts = [
            "This is a normal sentence.",
            "Another test with different words.",
            "Numbers 123 and special chars !@#",
        ]

        for text in texts:
            v_res = vectorize_text(text)
            v = v_res.v_native
            # First 240 elements are L2 normalized n-grams
            ngram_part = v[:240]
            norm = math.sqrt(sum(x * x for x in ngram_part))

            # Should be close to 1.0 (or 0 for empty)
            assert norm < 1.1 or norm == 0.0, f"Norm {norm} too high for text: {text}"

    def test_values_bounded(self):
        """Most values should be reasonably bounded."""
        texts = [
            "Normal text content.",
            "A" * 1000,
            "12345" * 100,
        ]

        for text in texts:
            v_res = vectorize_text(text)
            v = v_res.v_native
            # N-gram part (first 240) is L2 normalized
            for i, val in enumerate(v[:240]):
                assert (
                    -2.0 <= val <= 2.0
                ), f"Ngram value {val} out of bounds at index {i}"
            # Stats part (last 16) can be 0-1 normalized
            for i, val in enumerate(v[240:]):
                assert (
                    0.0 <= val <= 1.1
                ), f"Stat value {val} out of bounds at index {240+i}"

    def test_l2_normalize_unit_vector(self):
        """L2 normalization should produce unit vector."""
        vectors = [
            [1.0, 2.0, 3.0, 4.0],
            [0.1, 0.2, 0.3],
            [100.0, 200.0],
        ]

        for vec in vectors:
            normalized = l2_normalize(vec)
            norm = math.sqrt(sum(x * x for x in normalized))
            assert abs(norm - 1.0) < 1e-10, f"Norm {norm} not 1.0"

    def test_l2_normalize_zero_vector(self):
        """L2 normalization of zero vector should return zero."""
        vec = [0.0, 0.0, 0.0]
        normalized = l2_normalize(vec)
        assert normalized == vec

    def test_stats_bounded_0_1(self):
        """Most stats should be bounded 0-1."""
        text = "Test text with words and numbers 123."
        v_res = vectorize_text(text)
        stats = v_res.stats

        bounded_keys = [
            "digit_ratio",
            "alpha_ratio",
            "punct_ratio",
            "upper_ratio",
            "space_ratio",
            "unique_word_ratio",
        ]

        for key in bounded_keys:
            if key in stats:
                assert 0.0 <= stats[key] <= 1.0, f"{key} = {stats[key]} out of bounds"

    def test_vector_from_block_properties(self):
        """Vector from block should have all properties."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=100)
        block = EvidenceBlock.create(
            raw_id="test_raw",
            anchor=anchor,
            content="Test content for vector properties.",
        )

        vec = vectorize_block(block)

        # Check dimension
        assert len(vec.v_native) == VECTOR_DIMENSION

        # Check no NaN/Inf
        for val in vec.v_native:
            assert not math.isnan(val)
            assert not math.isinf(val)

        # Check opp_signature exists
        assert vec.opp_signature is not None
        assert "norm" in vec.opp_signature

    def test_empty_content_produces_valid_vector(self):
        """Empty content should produce valid (possibly zero) vector."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=0)
        block = EvidenceBlock.create(
            raw_id="test_raw",
            anchor=anchor,
            content="",
        )

        vec = vectorize_block(block)

        assert len(vec.v_native) == VECTOR_DIMENSION
        assert vec.verify_hash()

    def test_unicode_produces_valid_vector(self):
        """Unicode content should produce valid vector."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=100)
        block = EvidenceBlock.create(
            raw_id="test_raw",
            anchor=anchor,
            content="日本語テスト 中文测试 한국어테스트 🎉🎊",
        )

        vec = vectorize_block(block)

        assert len(vec.v_native) == VECTOR_DIMENSION
        assert vec.verify_hash()

        for val in vec.v_native:
            assert not math.isnan(val)
            assert not math.isinf(val)

    def test_opp_signature_has_required_fields(self):
        """Opposition signature should have required fields."""
        text = "Test content for signature."
        v_res = vectorize_text(text)
        opp_sig = v_res.opp_signature

        required = ["norm", "density", "max_val", "mean_val"]
        for field in required:
            assert field in opp_sig, f"Missing field: {field}"
