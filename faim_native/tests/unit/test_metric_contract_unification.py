"""Unit tests for metric contract unification.

Stage-4.1.1: Verify metrics_defs.py is contract-only and
FractalDiagnostics conforms to the contract.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

# Setup paths
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))


class TestMetricContractNoNumpy:
    """Verify metrics_defs.py contains NO numpy imports."""

    def test_metrics_defs_no_numpy_import(self):
        """metrics_defs.py must not import numpy."""
        metrics_defs_path = _faim_native / "core" / "metrics" / "metrics_defs.py"

        content = metrics_defs_path.read_text()

        # Parse AST to check imports
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "numpy", "metrics_defs.py imports numpy"
                    assert alias.name != "np", "metrics_defs.py imports numpy as np"

            if isinstance(node, ast.ImportFrom):
                assert node.module != "numpy", "metrics_defs.py imports from numpy"
                if node.module:
                    assert not node.module.startswith(
                        "numpy"
                    ), f"metrics_defs.py imports from {node.module}"

    def test_metrics_defs_no_numpy_string(self):
        """Double-check: 'numpy' or 'import np' string should not appear."""
        metrics_defs_path = _faim_native / "core" / "metrics" / "metrics_defs.py"

        content = metrics_defs_path.read_text()

        assert "import numpy" not in content
        assert "from numpy" not in content
        # Allow "np" in docstrings but not as import
        assert "import np" not in content.replace("import numpy as np", "")


class TestMetricKeysOrdered:
    """Verify METRIC_KEYS_ORDERED contains all expected keys."""

    def test_all_keys_present(self):
        """All metric keys should be in METRIC_KEYS_ORDERED."""
        from core.metrics.metrics_defs import METRIC_KEYS_ORDERED, MetricKey

        expected_keys = [
            MetricKey.CR,
            MetricKey.R,
            MetricKey.D_HAT,
            MetricKey.H_HAT,
            MetricKey.LAMBDA_HAT,
            MetricKey.NOVELTY,
            MetricKey.ENERGY,
        ]

        for key in expected_keys:
            assert key in METRIC_KEYS_ORDERED, f"Missing key: {key}"

    def test_keys_ordered_is_stable(self):
        """METRIC_KEYS_ORDERED should be stable for deterministic hashing."""
        from core.metrics.metrics_defs import METRIC_KEYS_ORDERED

        # Should be the same on each import (stable ordering)
        # The order is: CR, D_hat, energy, H_hat, lambda_hat, novelty, R
        expected_order = [
            "CR",
            "D_hat",
            "energy",
            "H_hat",
            "lambda_hat",
            "novelty",
            "R",
        ]
        assert METRIC_KEYS_ORDERED == expected_order

    def test_keys_are_strings(self):
        """All keys should be strings."""
        from core.metrics.metrics_defs import METRIC_KEYS_ORDERED

        for key in METRIC_KEYS_ORDERED:
            assert isinstance(key, str), f"Key {key} is not a string"


class TestMetricsSnapshotSchema:
    """Verify MetricsSnapshot schema matches contract."""

    def test_metrics_snapshot_has_required_fields(self):
        """MetricsSnapshot should have all required fields."""
        # Check dataclass fields
        import dataclasses

        from core.metrics.metrics_defs import MetricsSnapshot

        fields = {f.name for f in dataclasses.fields(MetricsSnapshot)}

        required = {
            "graph_id",
            "graph_version",
            "graph_hash",
            "metrics",
            "diagnostics_hash",
            "created_at",
        }

        assert required.issubset(fields), f"Missing fields: {required - fields}"

    def test_metrics_snapshot_is_frozen(self):
        """MetricsSnapshot should be immutable."""
        from core.metrics.metrics_defs import MetricsSnapshot

        snapshot = MetricsSnapshot(
            graph_id="test",
            graph_version=1,
            graph_hash="abc",
            metrics={"D_hat": 1.0},
            diagnostics_hash="def",
        )

        with pytest.raises(Exception):  # FrozenInstanceError  # noqa: B017
            snapshot.graph_id = "changed"

    def test_to_canonical_dict_excludes_created_at(self):
        """to_canonical_dict should NOT include created_at."""
        from datetime import datetime, timezone

        from core.metrics.metrics_defs import MetricsSnapshot

        snapshot = MetricsSnapshot(
            graph_id="test",
            graph_version=1,
            graph_hash="abc",
            metrics={"D_hat": 1.0},
            diagnostics_hash="def",
            created_at=datetime.now(timezone.utc),
        )

        canonical = snapshot.to_canonical_dict()

        assert "created_at" not in canonical


class TestFractalDiagnosticsConformance:
    """Verify FractalDiagnostics.to_metrics_snapshot() conforms to contract."""

    def test_to_metrics_snapshot_returns_metrics_snapshot(self):
        """to_metrics_snapshot should return MetricsSnapshot."""
        from core.metrics.fractal_physics import FractalDiagnostics
        from core.metrics.metrics_defs import MetricsSnapshot

        diag = FractalDiagnostics(
            graph_id="test",
            region_id="global",
            node_count=10,
            edge_count=15,
            s=0.618,
            D_hat=2.5,
            H_hat=0.7,
            lambda_hat=0.6,
            redundancy_R=0.2,
            novelty_N=0.3,
            energy_E=0.5,
            computed_at_version=1,
            diagnostics_hash="abc123",
        )

        snapshot = diag.to_metrics_snapshot(graph_hash="graph_hash_123")

        assert isinstance(snapshot, MetricsSnapshot)

    def test_to_metrics_snapshot_has_all_metric_keys(self):
        """Metrics dict should have all keys from METRIC_KEYS_ORDERED."""
        from core.metrics.fractal_physics import FractalDiagnostics
        from core.metrics.metrics_defs import METRIC_KEYS_ORDERED

        diag = FractalDiagnostics(
            graph_id="test",
            region_id="global",
            node_count=10,
            edge_count=15,
            s=0.618,
            D_hat=2.5,
            H_hat=0.7,
            lambda_hat=0.6,
            redundancy_R=0.2,
            novelty_N=0.3,
            energy_E=0.5,
            computed_at_version=1,
            diagnostics_hash="abc123",
        )

        snapshot = diag.to_metrics_snapshot(graph_hash="hash")

        for key in METRIC_KEYS_ORDERED:
            assert key in snapshot.metrics, f"Missing metric key: {key}"

    def test_metrics_values_match_diagnostics(self):
        """Metric values should match FractalDiagnostics fields."""
        from core.metrics.fractal_physics import FractalDiagnostics
        from core.metrics.metrics_defs import MetricKey

        diag = FractalDiagnostics(
            graph_id="test",
            region_id="global",
            node_count=10,
            edge_count=15,
            s=0.618,
            D_hat=2.5,
            H_hat=0.7,
            lambda_hat=0.6,
            redundancy_R=0.2,
            novelty_N=0.3,
            energy_E=0.5,
            computed_at_version=1,
            diagnostics_hash="abc123",
        )

        snapshot = diag.to_metrics_snapshot(graph_hash="hash")

        assert snapshot.metrics[MetricKey.D_HAT] == 2.5
        assert snapshot.metrics[MetricKey.H_HAT] == 0.7
        assert snapshot.metrics[MetricKey.LAMBDA_HAT] == 0.6
        assert snapshot.metrics[MetricKey.R] == 0.2
        assert snapshot.metrics[MetricKey.NOVELTY] == 0.3
        assert snapshot.metrics[MetricKey.ENERGY] == 0.5


class TestValidateMetricPayload:
    """Test validate_metric_payload function."""

    def test_valid_payload_returns_empty_list(self):
        """Valid payload should return empty error list."""
        from core.metrics.metrics_defs import validate_metric_payload

        payload = {
            "graph_id": "test",
            "graph_version": 1,
            "diagnostics_hash": "abc",
            "metrics": {
                "D_hat": 2.5,
                "H_hat": 0.7,
            },
        }

        errors = validate_metric_payload(payload)
        assert errors == []

    def test_missing_required_field_returns_error(self):
        """Missing required field should return error."""
        from core.metrics.metrics_defs import validate_metric_payload

        payload = {
            "graph_id": "test",
            # Missing graph_version
            "diagnostics_hash": "abc",
        }

        errors = validate_metric_payload(payload)
        assert any("graph_version" in e for e in errors)

    def test_out_of_range_metric_returns_error(self):
        """Metric out of range should return error."""
        from core.metrics.metrics_defs import MetricKey, validate_metric_payload

        payload = {
            "graph_id": "test",
            "graph_version": 1,
            "diagnostics_hash": "abc",
            "metrics": {
                MetricKey.H_HAT: 1.5,  # Out of range [0, 1]
            },
        }

        errors = validate_metric_payload(payload)
        assert any("H_hat" in e for e in errors)


class TestNoduplicateComputation:
    """Verify no duplicate metric computation outside fractal_physics.py."""

    def test_metrics_defs_has_no_computation_functions(self):
        """metrics_defs.py should only have contract code, no compute_* functions."""
        from core.metrics import metrics_defs

        # These are allowed contract functions
        allowed = {
            "validate_metric_payload",
            "compute_snapshot_hash",
            "create_metrics_snapshot",
        }

        public_functions = [
            name
            for name in dir(metrics_defs)
            if callable(getattr(metrics_defs, name))
            and not name.startswith("_")
            and name not in allowed
        ]

        # Filter out classes
        disallowed_compute = [
            name
            for name in public_functions
            if name.startswith("compute_") or name.startswith("estimate_")
        ]

        assert (
            disallowed_compute == []
        ), f"Found computation in metrics_defs: {disallowed_compute}"
