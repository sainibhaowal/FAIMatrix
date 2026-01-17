"""AT-O5: Verify perf spec dimension matches vector schema.

Tests that:
- spec.dim == VECTOR_DIMENSION (256)
- No dimension drift between encoding and perf layers
"""

from __future__ import annotations

import sys
from pathlib import Path

# Setup paths
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))


class TestSpecDimension:
    """Verify perf spec dimension matches vector schema."""

    def test_vector_dimension_is_256(self):
        """encoding.vector_schema.VECTOR_DIMENSION should be 256."""
        from encoding.vector_schema import VECTOR_DIMENSION

        assert VECTOR_DIMENSION == 256

    def test_spec_dim_matches_vector_dimension(self):
        """SpeedBudget.dim should match VECTOR_DIMENSION."""
        from encoding.vector_schema import VECTOR_DIMENSION
        from orchestration.perf.spec import SPEED_PROFILES

        for profile, budget in SPEED_PROFILES.items():
            assert (
                budget.dim == VECTOR_DIMENSION
            ), f"Profile {profile} has dim={budget.dim}, expected {VECTOR_DIMENSION}"

    def test_all_profiles_use_256_dim(self):
        """All profiles should use 256 as default_embedding_dim."""
        from orchestration.perf.spec import SPEED_PROFILES

        for profile, budget in SPEED_PROFILES.items():
            assert (
                budget.default_embedding_dim == 256
            ), f"Profile {profile} has wrong dim: {budget.default_embedding_dim}"

    def test_strict_profile_has_correct_dim(self):
        """STRICT profile specifically should use 256."""
        from orchestration.perf.spec import get_speed_budget

        strict = get_speed_budget("STRICT")
        assert strict.dim == 256

    def test_spec_imports_from_encoding(self):
        """spec.py should import VECTOR_DIMENSION from encoding."""
        spec_path = _faim_native / "orchestration" / "perf" / "spec.py"
        content = spec_path.read_text()

        # Should try to import from encoding
        assert "VECTOR_DIMENSION" in content
        assert "encoding" in content.lower() or "fallback" in content.lower()
