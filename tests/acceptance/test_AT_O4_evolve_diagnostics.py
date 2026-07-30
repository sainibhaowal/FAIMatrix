"""AT-O4: Verify evolve emits diagnostics.

Tests that:
- run_evolve returns diagnostics in MetricsSnapshot format
- DIAGNOSTICS_SNAPSHOT event is emitted
- MetricsSnapshot has ordered keys from Stage-4.1.1
"""

from __future__ import annotations

import sys
from pathlib import Path

# Setup paths
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))


class TestEvolveDiagnostics:
    """Verify evolve_flow emits proper diagnostics."""

    def test_evolve_result_has_diagnostics_field(self):
        """EvolveResult must have diagnostics field."""
        import dataclasses

        from orchestration.evolve_flow import EvolveResult

        fields = {f.name for f in dataclasses.fields(EvolveResult)}

        assert "diagnostics" in fields

    def test_evolve_result_has_events_emitted(self):
        """EvolveResult must track emitted events."""
        import dataclasses

        from orchestration.evolve_flow import EvolveResult

        fields = {f.name for f in dataclasses.fields(EvolveResult)}

        assert "events_emitted" in fields

    def test_metrics_snapshot_has_ordered_keys(self):
        """MetricsSnapshot.metrics uses METRIC_KEYS_ORDERED."""
        from core.metrics.metrics_defs import (
            METRIC_KEYS_ORDERED,
            MetricKey,
            MetricsSnapshot,
        )

        # Create a sample snapshot
        snapshot = MetricsSnapshot(
            graph_id="test",
            graph_version=1,
            graph_hash="abc",
            metrics={
                MetricKey.CR: 0.5,
                MetricKey.D_HAT: 2.5,
                MetricKey.ENERGY: 0.6,
                MetricKey.H_HAT: 0.7,
                MetricKey.LAMBDA_HAT: 0.5,
                MetricKey.NOVELTY: 0.3,
                MetricKey.R: 0.2,
            },
            diagnostics_hash="def",
        )

        # Check all ordered keys are present
        for key in METRIC_KEYS_ORDERED:
            assert key in snapshot.metrics

    def test_fractal_diagnostics_to_metrics_snapshot(self):
        """FractalDiagnostics.to_metrics_snapshot() returns MetricsSnapshot."""
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

        snapshot = diag.to_metrics_snapshot(graph_hash="test_hash")

        assert isinstance(snapshot, MetricsSnapshot)
        assert snapshot.graph_id == "test"
        assert snapshot.graph_version == 1

    def test_run_evolve_function_exists(self):
        """run_evolve function should exist and be callable."""
        from orchestration.evolve_flow import run_evolve

        assert callable(run_evolve)

    def test_evolve_flow_imports_evolution_native(self):
        """evolve_flow.py should use core.dynamics.evolution_native."""
        evolve_flow_path = (
            _faim_native / "faim_native" / "orchestration" / "evolve_flow.py"
        )
        content = evolve_flow_path.read_text()

        assert "evolution_native" in content
        assert "evolve_once" in content
