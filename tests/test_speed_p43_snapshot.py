# ======================================================================
# FAIM HyperSpeed P4.3 – NVMe Snapshot layer
# Golden Edition – small round-trip snapshot test.
# NOTE: We intentionally keep this test light; large-scale performance
# and crash-recovery tests live in dedicated benches/integration tests.
# ======================================================================

from pathlib import Path

import numpy as np
from faim.speed.nvme_snapshot import SnapshotManager
from faim.speed.spec import get_speed_budget
from faim.speed.vector_bank import VectorBank


def test_p43_snapshot_roundtrip_single_graph(tmp_path: Path):
    """
    Create a snapshot for a small graph, reload into a fresh VectorBank,
    and verify graph sizes match. Journal replay is not exercised here;
    that is covered by higher-level integration tests.
    """
    budget = get_speed_budget("CORE_DEV")
    bank = VectorBank(budget, use_gpu_default=False)
    gid = "snap-graph"

    rng = np.random.default_rng(1234)
    dim = budget.dim
    n = 256

    for i in range(n):
        v = rng.normal(size=(dim,)).astype(np.float32)
        bank.add_vector(gid, f"n{i}", v)

    # Init SnapshotManager – journal path is optional and may or may not
    # be used by your current implementation.
    snapshot_root = tmp_path / "Snapshots"
    snapshot_root.mkdir(parents=True, exist_ok=True)
    journal_path = tmp_path / "journal.jsonl"

    mgr = SnapshotManager(snapshot_root, budget, journal_path=journal_path)

    meta = mgr.create_snapshot(gid, bank)
    assert meta.graph_id == gid
    assert meta.count == n

    # New bank, load snapshot
    new_bank = VectorBank(budget, use_gpu_default=False)
    loaded_meta = mgr.load_latest_snapshot(gid, new_bank)
    assert loaded_meta is not None
    assert loaded_meta.graph_id == gid
    assert loaded_meta.count == n

    # graph_sizes must match
    assert bank.graph_sizes[gid] == new_bank.graph_sizes[gid]
