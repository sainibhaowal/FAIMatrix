"""
================================================================================
 FAIM HyperSpeed – Cold Durability Layer (P4.3)
--------------------------------------------------------------------------------
 This module implements the NVMe/SSD durability layer for TRUE FAIM.

 Responsibilities (Tier-3 Cold Store):
   * Periodic compressed snapshots of the Hot Vector Bank (Tier-1) and
     minimal graph metadata onto NVMe/SSD.
   * Manifest-based indexing so the latest snapshot can be discovered and
     loaded on startup.
   * Journal replay support: given a JSONL journal file where each entry
     carries a timestamp 'ts', this module can replay all operations that
     occurred AFTER a snapshot's cutoff time.

 Design:
   * Snapshots are stored under a root directory (default: Runtime/Snapshots).
   * Each snapshot has its own directory:
       <root>/faim_snapshot_<epoch_ms>/
         manifest.json
         graph_<safe_graph_id>.npz
   * Each per-graph .npz contains:
       - vectors: np.ndarray[float32] with shape (N, D)
       - node_ids: np.ndarray[dtype=object] aligned with rows
   * Snapshot manifest records:
       - version, created_at, snapshot_id
       - active profile name
       - per-graph node_count and dim
       - journal_cutoff_ts (for replay)

 Journal replay:
   * Journals are JSON Lines files (one JSON object per line) with at least:
       - ts: float (seconds since epoch)
       - op: str (e.g. "add"/"update"/"remove")
       - other engine-specific fields
   * Snapshots include 'journal_cutoff_ts'. On crash:
       1) Load latest snapshot into VectorBank.
       2) Replay all journal entries with ts > journal_cutoff_ts:
            apply_journal_entry(entry)
      The callback is provided by the engine; this module does not know
      FAIM's internal op schema.

 Invariants:
   * No disk I/O in hot path: this module is meant to be called from
     background workers or admin flows.
   * VectorBank's CPU arrays remain the source of truth; GPU mirrors are
     invalidated and lazily rebuilt after restore.
   * Snapshot writes are atomic at directory level:
       - snapshot written into a temporary dir
       - fsync
       - atomically renamed into place.

================================================================================
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
from faim.pipeline.speed.spec import SpeedBudget
from faim.pipeline.speed.vector_bank import VectorBank

# Optional logging hook (loguru preferred, but not required)
try:  # pragma: no cover - logging is optional
    from loguru import logger
except Exception:  # pragma: no cover - fallback when loguru is absent

    class _DummyLogger:
        def debug(self, *args: Any, **kwargs: Any) -> None: ...
        def info(self, *args: Any, **kwargs: Any) -> None: ...
        def warning(self, *args: Any, **kwargs: Any) -> None: ...
        def error(self, *args: Any, **kwargs: Any) -> None: ...
        def exception(self, *args: Any, **kwargs: Any) -> None: ...

    logger = _DummyLogger()  # type: ignore[assignment]


GraphId = Union[int, str]


# --------------------------------------------------------------------------- #
# Snapshot metadata structures
# --------------------------------------------------------------------------- #


@dataclass
class SnapshotGraphMeta:
    """
    Per-graph metadata stored in snapshot manifest.

    All fields are JSON-serialisable.
    """

    graph_id: Union[int, str]
    safe_graph_id: str
    file: str
    node_count: int
    dim: int


@dataclass
class SnapshotMeta:
    """
    Snapshot manifest metadata.

    Fields are designed to survive round-trip JSON serialisation.
    """

    version: str
    created_at: float  # seconds since epoch
    snapshot_id: str  # directory name suffix
    profile: str  # speed profile name (e.g. "DEV", "LAPTOP")
    graphs: List[SnapshotGraphMeta]
    journal_cutoff_ts: Optional[float] = None

    # Convenience summary for a single graph (used by P4.3 unit tests).
    graph_id: Optional[GraphId] = None
    count: Optional[int] = None

    def to_json_dict(self) -> Dict[str, Any]:
        """
        Convert to a JSON-encodable dict.

        Dataclasses in 'graphs' are expanded to plain dicts.
        """
        data = asdict(self)
        return data

    @staticmethod
    def from_json_dict(data: Dict[str, Any]) -> "SnapshotMeta":
        """
        Build SnapshotMeta from a JSON-decoded dict.
        """
        graphs_raw = data.get("graphs", [])
        graphs: List[SnapshotGraphMeta] = []
        for g in graphs_raw:
            graphs.append(
                SnapshotGraphMeta(
                    graph_id=g["graph_id"],
                    safe_graph_id=g["safe_graph_id"],
                    file=g["file"],
                    node_count=int(g["node_count"]),
                    dim=int(g["dim"]),
                )
            )
        return SnapshotMeta(
            version=str(data.get("version", "1.0")),
            created_at=float(data["created_at"]),
            snapshot_id=str(data["snapshot_id"]),
            profile=str(data["profile"]),
            graphs=graphs,
            journal_cutoff_ts=(
                float(data["journal_cutoff_ts"])
                if data.get("journal_cutoff_ts") is not None
                else None
            ),
            graph_id=data.get("graph_id"),
            count=int(data["count"]) if data.get("count") is not None else None,
        )


# --------------------------------------------------------------------------- #
# Utility helpers
# --------------------------------------------------------------------------- #


def _ensure_dir(path: Path) -> None:
    """Create directory (and parents) if not exists."""
    path.mkdir(parents=True, exist_ok=True)


def _sanitize_graph_id(graph_id: GraphId) -> str:
    """
    Make a filesystem-safe representation of graph_id.

    We keep alphanumerics, dash, underscore and dot; everything else becomes '_'.
    """
    raw = str(graph_id)
    return "".join(ch if ch.isalnum() or ch in "-._" else "_" for ch in raw)


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    """
    Atomically write a small JSON file.

    We write to a temporary file in the same directory, fsync, then rename.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = json.dumps(payload, separators=(",", ":"), sort_keys=True)

    with tmp.open("w", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())

    os.replace(tmp, path)


def _fsync_dir(path: Path) -> None:
    """
    fsync a directory to commit metadata updates to disk.

    On some platforms this may be a no-op, but on Linux it is supported.
    """
    try:  # pragma: no cover - platform dependent
        fd = os.open(str(path), os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        # Best-effort; not fatal.
        return


# --------------------------------------------------------------------------- #
# Snapshot manager
# --------------------------------------------------------------------------- #


class SnapshotManager:
    """
    Manages NVMe/SSD snapshots for a FAIM VectorBank and journal replay.

    This class is deliberately agnostic about the engine details; it only
    knows about:

      * SpeedBudget (for profile name and future policies),
      * VectorBank (P4.1 implementation),
      * journal path (JSONL),
      * a user-provided apply_journal_entry callback for replay.

    Typical usage:

        budget = get_speed_budget("LAPTOP")
        bank = VectorBank(budget, use_gpu_default=True)
        manager = SnapshotManager(
            snapshot_root=Path("Runtime/Snapshots"),
            journal_path=Path("Runtime/Journal/faim_journal.jsonl"),
            speed_budget=budget,
        )

        # Periodic background task:
        manager.maybe_snapshot(vector_bank=bank, journal_cutoff_ts=time.time())

        # On process startup:
        meta = manager.load_latest_snapshot(vector_bank=bank)
        if meta is not None:
            manager.replay_journal_since(meta, apply_journal_entry=my_apply_fn)

    Notes:
      * This module never runs in the hot path. Call its methods from a
        background worker, maintenance window, or admin endpoint.
      * VectorBank's GPU mirrors are invalidated on restore and will be
        lazily rebuilt on next GPU query.
    """

    def __init__(
        self,
        snapshot_root: Path,
        speed_budget: SpeedBudget,
        *,
        journal_path: Optional[Path] = None,
        min_snapshot_interval_sec: float = 60.0,
        min_new_nodes_between_snapshots: int = 10_000,
    ) -> None:
        """
        Args:
            snapshot_root:
                Directory under which snapshot subdirectories will be created.
            journal_path:
                Path to the JSONL journal file. May be None if replay is
                handled elsewhere or journaling is disabled.
            speed_budget:
                Active SpeedBudget (provides profile name, memory ceilings).
            min_snapshot_interval_sec:
                Minimum wall-clock time between automatic snapshots.
            min_new_nodes_between_snapshots:
                Minimum number of newly added nodes since last snapshot before
                an automatic snapshot is considered.
        """
        self._snapshot_root = snapshot_root
        self._journal_path = journal_path
        self._speed_budget = speed_budget
        self._min_interval = float(min_snapshot_interval_sec)
        self._min_new_nodes = int(min_new_nodes_between_snapshots)

        _ensure_dir(self._snapshot_root)

        self._last_snapshot_meta: Optional[SnapshotMeta] = None
        self._nodes_at_last_snapshot: int = 0

        logger.info(
            "SnapshotManager initialised: root={root}, journal={journal}, profile={profile}",
            root=str(self._snapshot_root),
            journal=str(self._journal_path) if self._journal_path else None,
            profile=self._speed_budget.profile.value,
        )

    # ------------------------------------------------------------------ public

    @property
    def snapshot_root(self) -> Path:
        return self._snapshot_root

    @property
    def journal_path(self) -> Optional[Path]:
        return self._journal_path

    @property
    def last_snapshot_meta(self) -> Optional[SnapshotMeta]:
        return self._last_snapshot_meta

    # ------------------------------- snapshot creation ------------------------

    def create_snapshot(
        self,
        graph_id: Optional[GraphId],
        vector_bank: VectorBank,
        *,
        journal_cutoff_ts: Optional[float] = None,
        now: Optional[float] = None,
    ) -> SnapshotMeta:
        """
        Create a new snapshot of the current VectorBank state.

        This writes a new directory under snapshot_root with:
          * manifest.json
          * per-graph .npz files containing CPU vectors and node_ids.

        Args:
            vector_bank:
                Active VectorBank instance to snapshot.
            journal_cutoff_ts:
                Optional timestamp indicating up to which point the journal
                has been applied. On restore, replay will start AFTER this
                cutoff.
            now:
                Optional explicit timestamp for 'created_at'. Defaults to
                time.time().

        Returns:
            SnapshotMeta for the newly created snapshot.
        """
        ts = float(time.time() if now is None else now)
        snapshot_id = f"faim_snapshot_{int(ts * 1000)}"
        tmp_dir = self._snapshot_root / f"{snapshot_id}.tmp"
        final_dir = self._snapshot_root / snapshot_id

        logger.info(
            "Creating FAIM snapshot id={sid} at {dir}",
            sid=snapshot_id,
            dir=str(tmp_dir),
        )

        _ensure_dir(tmp_dir)

        graphs_meta: List[SnapshotGraphMeta] = []

        # We reach into VectorBank's internal graphs. This is allowed because
        # nvme_snapshot is part of the same backend package.
        graphs_items = list(vector_bank._graphs.items())  # type: ignore[attr-defined]

        for graph_id, gv in graphs_items:
            # Access internals under lock for consistency.
            with gv._lock:
                vectors = gv.vectors_cpu.copy()
                node_ids = np.array(gv.node_ids, dtype=object)

            if vectors.size == 0:
                # Skip empty graphs for now (they can be rebuilt from journal).
                continue

            safe_id = _sanitize_graph_id(graph_id)
            file_name = f"graph_{safe_id}.npz"
            out_path = tmp_dir / file_name

            # Store vectors + node_ids in a compressed npz.
            with out_path.open("wb") as f:
                np.savez_compressed(f, vectors=vectors, node_ids=node_ids)
                f.flush()
                os.fsync(f.fileno())

            g_meta = SnapshotGraphMeta(
                graph_id=graph_id,
                safe_graph_id=safe_id,
                file=file_name,
                node_count=int(vectors.shape[0]),
                dim=int(vectors.shape[1]),
            )
            graphs_meta.append(g_meta)

        summary_count: Optional[int] = None
        if graph_id is not None:
            for g in graphs_meta:
                if str(g.graph_id) == str(graph_id):
                    summary_count = g.node_count
                    break

        meta = SnapshotMeta(
            version="1.0",
            created_at=ts,
            snapshot_id=snapshot_id,
            profile=self._speed_budget.profile.value,
            graphs=graphs_meta,
            journal_cutoff_ts=journal_cutoff_ts,
            graph_id=graph_id,
            count=summary_count,
        )

        # Write manifest.json
        manifest_path = tmp_dir / "manifest.json"
        _atomic_write_json(manifest_path, meta.to_json_dict())

        # fsync directory and atomically rename into place.
        _fsync_dir(tmp_dir)
        os.replace(tmp_dir, final_dir)
        _fsync_dir(self._snapshot_root)

        self._last_snapshot_meta = meta

        # Track node count baseline for maybe_snapshot.
        total_nodes = sum(g.node_count for g in graphs_meta)
        self._nodes_at_last_snapshot = total_nodes

        logger.info(
            "FAIM snapshot created id={sid}, graphs={graphs}, nodes={nodes}",
            sid=snapshot_id,
            graphs=len(graphs_meta),
            nodes=total_nodes,
        )

        return meta

    def maybe_snapshot(
        self,
        vector_bank: VectorBank,
        *,
        journal_cutoff_ts: Optional[float] = None,
        now: Optional[float] = None,
    ) -> Optional[SnapshotMeta]:
        """
        Decide whether to create a snapshot based on time and node-count deltas.

        This method is intended to be called periodically by a background worker.

        Rules:
          * If no snapshot exists yet: always create one.
          * Else, create a new snapshot if BOTH:
              - elapsed_time >= min_snapshot_interval_sec, AND
              - (total_nodes - nodes_at_last_snapshot) >= min_new_nodes_between_snapshots

        Returns:
            SnapshotMeta if a snapshot was created, else None.
        """
        ts = float(time.time() if now is None else now)

        # Estimate current total nodes across graphs.
        sizes = vector_bank.graph_sizes
        total_nodes = sum(sizes.values())

        if self._last_snapshot_meta is None:
            return self.create_snapshot(
                None,
                vector_bank,
                journal_cutoff_ts=journal_cutoff_ts,
                now=ts,
            )

        elapsed = ts - self._last_snapshot_meta.created_at
        delta_nodes = max(0, total_nodes - self._nodes_at_last_snapshot)

        if elapsed < self._min_interval or delta_nodes < self._min_new_nodes:
            logger.debug(
                "SnapshotManager.maybe_snapshot: skip (elapsed={elapsed:.1f}s, "
                "delta_nodes={delta_nodes})",
                elapsed=elapsed,
                delta_nodes=delta_nodes,
            )
            return None

        return self.create_snapshot(
            None,
            vector_bank,
            journal_cutoff_ts=journal_cutoff_ts,
            now=ts,
        )

    # ------------------------------- snapshot load ----------------------------

    def load_latest_snapshot(
        self,
        graph_id: Optional[GraphId],
        vector_bank: VectorBank,
    ) -> Optional[SnapshotMeta]:
        """
        Load the latest snapshot (if any) into the provided VectorBank.

        This clears any existing graphs in the VectorBank and replaces them
        with the state from the snapshot. GPU mirrors are invalidated.

        Returns:
            SnapshotMeta for the loaded snapshot, or None if no snapshot exists.
        """
        snapshot_dirs: List[Tuple[Path, SnapshotMeta]] = []

        for entry in self._snapshot_root.iterdir():
            if not entry.is_dir():
                continue
            if not entry.name.startswith("faim_snapshot_"):
                continue

            manifest_path = entry / "manifest.json"
            if not manifest_path.is_file():
                continue

            try:
                with manifest_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                meta = SnapshotMeta.from_json_dict(data)
                snapshot_dirs.append((entry, meta))
            except Exception as exc:
                logger.warning(
                    "Failed to load manifest from {path}: {exc}",
                    path=str(manifest_path),
                    exc=exc,
                )
                continue

        if not snapshot_dirs:
            logger.info(
                "No FAIM snapshots found under {root}", root=str(self._snapshot_root)
            )
            return None

        # Pick snapshot with max created_at.
        snapshot_dirs.sort(key=lambda item: item[1].created_at)
        latest_dir, latest_meta = snapshot_dirs[-1]

        logger.info(
            "Loading FAIM snapshot id={sid} from {dir}",
            sid=latest_meta.snapshot_id,
            dir=str(latest_dir),
        )

        # Clear existing graphs.
        vector_bank._graphs.clear()  # type: ignore[attr-defined]

        # Restore each graph.
        for g_meta in latest_meta.graphs:
            file_path = latest_dir / g_meta.file
            if not file_path.is_file():
                logger.warning(
                    "Snapshot file missing for graph_id={gid}: {path}",
                    gid=g_meta.graph_id,
                    path=str(file_path),
                )
                continue

            with file_path.open("rb") as f:
                data = np.load(f, allow_pickle=True)
                vectors = np.asarray(data["vectors"], dtype=np.float32)
                node_ids_arr = data["node_ids"]
                node_ids = list(node_ids_arr.tolist())

            if vectors.shape[0] != g_meta.node_count or vectors.shape[1] != g_meta.dim:
                logger.warning(
                    "Snapshot dimension mismatch for graph_id={gid}: "
                    "expected ({n},{d}), got {shape}",
                    gid=g_meta.graph_id,
                    n=g_meta.node_count,
                    d=g_meta.dim,
                    shape=tuple(vectors.shape),
                )

            gv = vector_bank.ensure_graph(g_meta.graph_id)

            # Rebuild internal structures under lock.
            with gv._lock:
                gv.dim = int(vectors.shape[1])
                gv.vectors_cpu = vectors
                gv.node_ids = node_ids
                gv.node_index = {nid: idx for idx, nid in enumerate(node_ids)}
                # Invalidate GPU mirror; it will be rebuilt lazily.
                gv._vectors_gpu = None
                gv._gpu_dirty = True

        self._last_snapshot_meta = latest_meta
        self._nodes_at_last_snapshot = sum(g.node_count for g in latest_meta.graphs)

        logger.info(
            "FAIM snapshot loaded id={sid}, graphs={graphs}, nodes={nodes}",
            sid=latest_meta.snapshot_id,
            graphs=len(latest_meta.graphs),
            nodes=self._nodes_at_last_snapshot,
        )
        # Provide a convenience single-graph summary for callers (tests).
        if graph_id is not None:
            sizes = vector_bank.graph_sizes
            count = sizes.get(graph_id, 0)
            latest_meta.graph_id = graph_id
            latest_meta.count = count

        return latest_meta

    # ------------------------------- journal replay ---------------------------

    def replay_journal_since(
        self,
        snapshot_meta: SnapshotMeta,
        apply_entry: Callable[[Dict[str, Any]], None],
        *,
        stop_ts: Optional[float] = None,
    ) -> int:
        """
        Replay journal entries AFTER snapshot_meta.journal_cutoff_ts.

        Args:
            snapshot_meta:
                SnapshotMeta of the loaded snapshot. Its 'journal_cutoff_ts'
                field is used as the lower bound for 'ts' when selecting
                journal entries.
            apply_entry:
                Callback function taking a decoded JSON dict representing a
                single journal entry. It is responsible for applying the
                operation to VectorBank, NodeStore, etc.
            stop_ts:
                Optional upper bound timestamp; entries with ts > stop_ts
                are ignored. Defaults to None (no upper bound).

        Returns:
            Number of journal entries that were applied.
        """
        if self._journal_path is None:
            logger.info(
                "SnapshotManager.replay_journal_since: no journal_path configured"
            )
            return 0

        cutoff = snapshot_meta.journal_cutoff_ts
        if cutoff is None:
            cutoff = snapshot_meta.created_at

        upper = float(stop_ts) if stop_ts is not None else None

        path = self._journal_path
        if not path.is_file():
            logger.info("Journal file not found at {path}", path=str(path))
            return 0

        applied = 0
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("Skipping invalid journal line: {line}", line=line)
                    continue

                ts_val = float(entry.get("ts", 0.0))

                if ts_val <= cutoff:
                    continue
                if upper is not None and ts_val > upper:
                    continue

                try:
                    apply_entry(entry)
                    applied += 1
                except Exception as exc:
                    logger.exception(
                        "Error applying journal entry ts={ts}: {exc}",
                        ts=ts_val,
                        exc=exc,
                    )

        logger.info(
            "Journal replay complete: applied={applied}, cutoff={cutoff}, stop={stop}",
            applied=applied,
            cutoff=cutoff,
            stop=upper,
        )
        return applied
