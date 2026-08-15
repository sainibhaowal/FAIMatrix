"""Unit tests for the evolve-metrics Prometheus scraper script."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRAper_Path = Path(__file__).resolve().parents[2] / "scripts" / "scrape_evolve_metrics.py"


def _load_scraper():
    spec = importlib.util.spec_from_file_location("scrape_evolve_metrics", _SCRAper_Path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["scrape_evolve_metrics"] = module
    spec.loader.exec_module(module)
    return module


_module = None


def _scraper():
    global _module
    if _module is None:
        _module = _load_scraper()
    return _module


def test_metrics_to_text_emits_expected_families():
    m = _scraper()
    data = {
        "graph_id": "g1",
        "cycles": {
            "count": 3,
            "last_version": 7,
            "last_merges": 2,
            "last_prunes": 1,
            "last_inventions": 0,
        },
        "data_safety": {
            "backups_available": 2,
            "latest_cycle_backups": 1,
            "coverage_ok": True,
        },
        "learning": {
            "enabled": True,
            "learned": True,
            "outcomes_count": 25,
            "knob_drift_count": 2,
            "reward_trend_slope": 0.31,
            "trust_ready": True,
        },
        "alerts": [],
    }
    text = m.metrics_to_text(data, "g1", scrape_ts=1_700_000_000)
    assert "faim_evolve_cycles_completed{graph_id=\"g1\"} 3" in text
    assert "faim_evolve_backup_coverage_ok{graph_id=\"g1\"} 1" in text
    assert "faim_evolve_learning_trust_ready{graph_id=\"g1\"} 1" in text
    assert "faim_evolve_learning_reward_trend{graph_id=\"g1\"} 0.31" in text
    assert (
        'faim_evolve_updated_timestamp_seconds{graph_id="g1"} 1700000000' in text
    )
    assert "faim_evolve_alert" not in text


def test_metrics_to_text_flags_critical_alerts():
    m = _scraper()
    data = {
        "cycles": {"count": 1, "last_version": 2, "last_prunes": 4},
        "data_safety": {
            "backups_available": 1,
            "latest_cycle_backups": 1,
            "coverage_ok": False,
        },
        "learning": {"enabled": False, "outcomes_count": 0},
        "alerts": [
            {"level": "critical", "code": "backup_coverage_gap", "message": "x"},
            {"level": "info", "code": "no_cycles_recorded", "message": "y"},
        ],
    }
    text = m.metrics_to_text(data, "g1", scrape_ts=0)
    assert "faim_evolve_backup_coverage_ok{graph_id=\"g1\"} 0" in text
    assert (
        'faim_evolve_alert{code="backup_coverage_gap",level="critical"} 1' in text
    )
    assert 'faim_evolve_alert{code="no_cycles_recorded",level="info"} 1' in text


def test_deadman_marker_records_last_success_timestamp(tmp_path):
    m = _scraper()
    deadman = tmp_path / "evolve_deadman.prom"
    m._write_deadman(
        str(deadman),
        "g1",
        ok=1,
        scrape_ts=1_700_000_000,
        current_ts=1_700_000_300,
    )
    text = deadman.read_text(encoding="utf-8")
    assert 'faim_evolve_scrape_ok{graph_id="g1"} 1' in text
    assert (
        'faim_evolve_updated_timestamp_seconds{graph_id="g1"} 1700000000' in text
    )
    assert 'faim_evolve_scrape_failure_age_seconds{graph_id="g1"} 300' in text


def test_deadman_not_written_when_no_path() -> None:
    m = _scraper()
    # Should not raise and must not create anything.
    m._write_deadman(None, "g1", ok=1, scrape_ts=1, current_ts=2)