# tests/test_fractal_dimension_metrics.py
"""
Fractal-dimension metric tests (P1.5).

Validates:
- Degenerate cases (P <= 1) → D = 0.
- D = log(P) / log(1 / s) with GOLDEN_SCALE = 1 / φ.
"""

from __future__ import annotations

import math

from faim.core.math import GOLDEN_SCALE
from faim.core.metrics import estimate_fractal_dimension


def test_estimate_fractal_dimension_degenerate_cases() -> None:
    assert estimate_fractal_dimension(1.0) == 0.0
    assert estimate_fractal_dimension(0.0) == 0.0
    assert estimate_fractal_dimension(-5.0) == 0.0


def test_estimate_fractal_dimension_matches_theoretical_target() -> None:
    # For a theoretical branching P = (1 / s) ** 2.5, we should get D ≈ 2.5.
    P = (1.0 / GOLDEN_SCALE) ** 2.5
    D = estimate_fractal_dimension(P, scale=GOLDEN_SCALE)
    assert math.isclose(D, 2.5, rel_tol=1e-6, abs_tol=1e-6)
