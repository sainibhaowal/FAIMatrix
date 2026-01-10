# ============================================================================
#  FAIM CORE ENGINE  –  GOLDEN EDITION
# ----------------------------------------------------------------------------
#  P1/P2 semantics + P4 HyperSpeed wiring (foundational, no behaviour change
#  vs existing tests).
#
#  Responsibilities:
#    - Deterministic DummyEmbedder for tests
#    - Inheritance construction via faim.core.math.inheritance_construction
#    - Antisymmetric merge via faim.core.antisym.merge_records
#    - Persistent storage in SqliteStore + PayloadStore + EventJournal
#    - ANN + Radius indices for parent search & antisymmetry radius
#    - P4 wiring: VectorBank, HotNodeCache, SnapshotManager, WriteQueue,
#                 IngestWorker (currently scaffold-only for writes)
#
#  Public API (stable for P1/P2 tests):
#    - DummyEmbedder(dim)
#    - FAIMEngine(profile="Default", persist_mode="relaxed")
#         add_memory(graph_id, payload, meta=None) -> NodeId
#         retrieve(graph_id, query, k=...) -> list[NodeRecord]
#         evolve(graph_id) -> None           # placeholder (P3+)
#         shutdown() -> None                 # clean snapshot + worker stop
# ============================================================================

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Any, Dict, List, Optional, Sequence, cast

import numpy as np

from faim.core.embedder import Embedder as EmbedderProtocol
from faim.core.memory import UsageTracker, VectorMemory
from faim.data.storage.cipher import build_cipher_from_env
from faim.data.storage.encrypted_payload_store import EncryptedPayloadStore
from faim.data.storage.journal import EventJournal, JournalEvent
from faim.data.storage.payload_store import PayloadStore
from faim.data.storage.store import FAIMStore
from faim.pipeline.speed.hot_cache import HotNodeCache
from faim.pipeline.speed.ingest_worker import IngestWorker
from faim.pipeline.speed.nvme_snapshot import SnapshotManager
from faim.pipeline.speed.spec import PersistMode, get_speed_budget
from faim.pipeline.speed.vector_bank import VectorBank
from faim.pipeline.speed.write_queue import WriteQueue, WriteTask

from .analytics import AnalyticsScheduler
from .antisym import merge_records
from .events import emit_cluster_updated, emit_inference_found, emit_insight_discovered

# P3 evolution imports
from .evolution import (
    EvolutionAdapter,
    EvolutionConfig,
    EvolutionScheduler,
    QueryStats,
    Region,
    RegionEvolutionConfig,
    RegionStats,
    compute_region_redundancy,
    discover_regions,
    evolve_graph_once,
    evolve_region,
)
from .invention import InventionScheduler
from .math import InheritanceResult, inheritance_construction
from .types import GraphId, NodeId, NodeRecord, ParentRef, Vector

EMBED_DIM = 64  # deterministic embedding size for tests

# --------------------------------------------------------------------------- #
# Embedding
# --------------------------------------------------------------------------- #


@dataclass
class DummyEmbedder:
    """
    Deterministic toy embedder based on SHA256.

    This is not semantic; it just produces a stable unit vector so that
    tests can rely on fixed behaviour without loading a real model.

    It conforms to faim.core.embedding.Embedder (Protocol) via:

        encode(payload: str) -> Vector
    """

    dim: int = EMBED_DIM

    def encode(self, payload: str) -> Vector:
        """Return a unit-length deterministic embedding for the payload."""
        data = payload.encode("utf-8")
        digest = hashlib.sha256(data).digest()
        needed = self.dim

        # Repeat digest bytes until we have enough, then cast to float32.
        buf = (digest * ((needed // len(digest)) + 1))[:needed]
        arr = np.frombuffer(buf, dtype=np.uint8).astype(np.float32)

        norm = float(np.linalg.norm(arr))
        if norm == 0.0:
            return arr
        return (arr / norm).astype(np.float32)


# --------------------------------------------------------------------------- #
# Core engine
# --------------------------------------------------------------------------- #


class FAIMEngine:
    """FAIM engine implementing the P1/P2 contract with P3/P4 wiring.

    P2 semantics:
    - Synchronous writes to SqliteStore and EventJournal.
    - ANN and Radius indices for parent search and antisymmetric merge.
    - retrieve(...) uses ANN plus FAIMStore as before.

    P4 wiring (foundational only):
    - VectorBank and HotNodeCache are populated alongside ANN/Radius so that
      HyperSpeed benchmarks and future P4-based retrieval can be added
      without breaking existing tests.
    - SnapshotManager is configured to snapshot VectorBank and replay journal
      entries into hot structures at startup.
    - WriteQueue and IngestWorker are initialised but not yet used to move
      SqliteStore writes off the hot path.

    P3 wiring:
    - evolve(graph_id) runs evolution using faim.core.evolution:
        * Graph mode (default): evolve_graph_once(...)
        * Region mode (FAIM_P3_REGION_MODE=1): evolve_region(...) via adapter.
    """

    def __init__(
        self,
        profile: str = "Default",
        persist_mode: str = "relaxed",
        *,
        embedder: Optional[EmbedderProtocol] = None,
        store: Optional[FAIMStore] = None,
        payload_store: Optional[PayloadStore] = None,
        journal: Optional[EventJournal] = None,
        usage: Optional[UsageTracker] = None,
        parent_top_k: int = 8,
        antisym_theta: float = 0.25,
    ) -> None:
        # Core P2 components -------------------------------------------------
        # NOTE: store must be explicitly provided. In production, use PostgresStore.
        # No SQLite fallback - run via Docker with Postgres.
        if store is None:
            raise ValueError(
                "FAIMEngine requires an explicit store parameter. "
                "Use PostgresStore from production_state.get_faim_context() "
                "or provide a store implementation."
            )
        default_store = store

        # Main graph store.
        self._store = store

        # Base payload store (pre-encryption): either explicit or same as main store.
        base_payload_store: PayloadStore = payload_store or (
            default_store if isinstance(default_store, PayloadStore) else None
        )
        if base_payload_store is None:
            raise ValueError("FAIMEngine requires a payload_store parameter.")

        # Optional compression + encryption layer (P2).
        enc_flag = os.getenv("FAIM_ENABLE_PAYLOAD_ENCRYPTION", "").strip().lower()
        # Attribute is always exposed as the abstract interface.
        self._payload_store: PayloadStore
        if enc_flag in ("1", "true", "yes"):
            cipher = build_cipher_from_env()
            self._payload_store = EncryptedPayloadStore(
                base_payload_store,
                cipher,
            )
        else:
            self._payload_store = base_payload_store

        self._embedder: EmbedderProtocol = embedder or DummyEmbedder()
        self._journal: EventJournal = journal or (default_store if isinstance(default_store, EventJournal) else None)
        self._usage: UsageTracker = usage or UsageTracker()

        embed_dim_any: Any = getattr(self._embedder, "dim", EMBED_DIM)
        try:
            embed_dim = int(embed_dim_any)
            if embed_dim <= 0:
                embed_dim = EMBED_DIM
        except Exception:
            embed_dim = EMBED_DIM

        self._memory = VectorMemory(dim=embed_dim)

        self._parent_top_k = int(parent_top_k)
        self._antisym_theta = float(antisym_theta)

        # P4.0 - speed budget and persist mode ------------------------------
        self._speed_budget = get_speed_budget(profile)
        try:
            self._persist_mode: PersistMode = PersistMode[persist_mode.upper()]
        except Exception:
            # Fallback to RELAXED if an unknown string is passed.
            self._persist_mode = PersistMode.RELAXED

        # P4.1 + P4.2 - hot vector bank and warm node cache -----------------
        self._vector_bank = VectorBank(
            speed_budget=self._speed_budget,
            use_gpu_default=self._speed_budget.allow_gpu,
        )
        self._hot_cache: HotNodeCache[NodeRecord] = HotNodeCache(speed_budget=self._speed_budget)

        # P4.3 - snapshot manager -------------------------------------------
        # NOTE: Using /tmp paths for Docker. Snapshots are ephemeral since
        # persistent storage is now handled by Postgres/Qdrant.
        journal_path = Path("/tmp/faim/journal/faim_journal.jsonl")  # nosec B108
        journal_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_root = Path("/tmp/faim/snapshots")  # nosec B108
        snapshot_root.mkdir(parents=True, exist_ok=True)

        self._snapshot_manager = SnapshotManager(
            snapshot_root=snapshot_root,
            journal_path=journal_path,
            speed_budget=self._speed_budget,
        )

        # P4.4 - write queue and ingest worker scaffold ---------------------
        self._write_queue = WriteQueue(
            speed_budget=self._speed_budget,
            maxsize=100_000,
        )

        def _writer(batch: Sequence[WriteTask]) -> None:
            """Background writer stub used by IngestWorker.

            Currently a no-op so that we can exercise the queue and worker
            without changing P2 semantics. Future P4 work will route batched
            writes into SqliteStore and EventJournal here.
            """
            # Intentionally unused until async writes are enabled.
            del batch

        self._ingest_worker = IngestWorker(
            write_queue=self._write_queue,
            writer=_writer,
            batch_size=2000,
            max_batch_delay=0.05,
        )
        self._ingest_worker.start()

        # Crash recovery for hot structures ---------------------------------
        # Load latest VectorBank snapshot, then replay journal into it.
        meta = self._snapshot_manager.load_latest_snapshot(
            None,
            self._vector_bank,
        )
        if meta is not None:
            self._snapshot_manager.replay_journal_since(
                meta,
                apply_entry=self._apply_journal_entry,
            )

        # P3.5 - Autonomous Self-Ness Schedulers -----------------------------
        # These start dreaming when Engine is born. No external watchers needed.
        self._evolution_scheduler: Optional[EvolutionScheduler] = EvolutionScheduler(store=self._store)
        self._evolution_scheduler.start()

        self._invention_scheduler: Optional[InventionScheduler] = None

        # P5 - Analytics Scheduler (Clustering, Inference, Insights) ----------
        self._analytics_scheduler = AnalyticsScheduler(
            store=self._store,
            emit_cluster_updated=emit_cluster_updated,
            emit_inference_found=emit_inference_found,
            emit_insight_discovered=emit_insight_discovered,
            interval_seconds=30.0,
            min_nodes_for_trigger=10,
        )
        self._analytics_scheduler.start()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def add_memory(
        self,
        graph_id: str,
        payload: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> NodeId:
        """Add a memory node into the given graph.

        Behaviour (P2):
        - Persist payload in PayloadStore.
        - ANN-based parent search.
        - Inheritance construction (math layer).
        - Radius-based antisymmetric merge.
        - Upsert node in SqliteStore + update ANN/Radius + append journal.

        P4 wiring:
        - VectorBank receives the final vector.
        - HotNodeCache receives the final NodeRecord.
        """
        meta = meta or {}
        g_id = cast(GraphId, graph_id)
        now = time()

        # Persist payload ----------------------------------------------------
        payload_bytes = payload.encode("utf-8")
        payload_ref = self._payload_store.put_payload(
            g_id,
            payload_bytes,
            mime_type="text/plain",
        )
        # ------------------------------------------------------------------
        # Exact-dedup: if this exact payload already exists in this graph,
        # reuse the existing node instead of creating a duplicate.
        # ------------------------------------------------------------------
        find_by_payload = getattr(self._store, "find_node_id_by_payload_ref", None)
        if callable(find_by_payload):
            existing_id: NodeId | None = self._store.find_node_id_by_payload_ref(g_id, payload_ref)
            if existing_id is not None:
                existing = self._store.get_node(g_id, existing_id)
                if existing is not None:
                    # touch usage (increments + updates last_used_at)
                    self._usage.touch(existing, at=now)
                    self._store.upsert_node(existing)

                    data = {
                        "node_id": str(existing.id),
                        "payload_ref": str(payload_ref),
                        "reason": "duplicate_payload_ref",
                    }
                    self._journal.append(JournalEvent(ts=now, graph_id=g_id, op="touch", data=data))
                    self._append_jsonl_journal(now, g_id, "touch", data)

                    # keep hot structures in sync
                    self._hot_cache.put(existing.id, existing)
                    self._vector_bank.add_vector(str(g_id), existing.id, existing.vec)

                    return existing.id

        # Embedding ---------------------------------------------------------
        e = self._embedder.encode(payload)

        # Parent search (ANN) -----------------------------------------------
        parents: List[NodeRecord] = []
        if self._memory.size(g_id) > 0 and self._parent_top_k > 0:
            hits = self._memory.search(g_id, e, self._parent_top_k)
            for parent_id, _score in hits:
                parent = self._store.get_node(g_id, parent_id)
                if parent is not None:
                    parents.append(parent)

        parent_vecs: List[Vector] = [p.vec for p in parents]
        inh: InheritanceResult = inheritance_construction(parent_vecs, e)
        candidate_vec = inh.v_new

        # Antisymmetry: radius search before inserting ----------------------
        merge_target_id: Optional[NodeId] = None
        if self._memory.size(g_id) > 0:
            neighbors = self._memory.query_radius(
                g_id,
                candidate_vec,
                radius=self._antisym_theta,
            )
            if neighbors:
                merge_target_id = neighbors[0][0]

        # Merge into existing node ------------------------------------------
        if merge_target_id is not None:
            keep = self._store.get_node(g_id, merge_target_id)
            if keep is not None:
                virtual_id_str = f"{graph_id}:virtual:{hashlib.sha256(payload_bytes).hexdigest()[:8]}"
                virtual_id = cast(NodeId, virtual_id_str)

                drop = NodeRecord(
                    id=virtual_id,
                    graph_id=g_id,
                    vec=candidate_vec,
                    parents=[
                        ParentRef(parent_id=p.id, fraction=f) for p, f in zip(parents, inh.fractions, strict=False)
                    ],
                    children=[],
                    payload_ref=payload_ref,
                    created_at=now,
                    last_used_at=now,
                    use_count=1,
                    merged_count=0,
                    flags=0,
                )
                merged = merge_records(keep, drop)

                # Core store and indices (P2) ------------------------------
                self._store.upsert_node(merged)
                self._memory.update(g_id, merged.id, merged.vec)

                merge_data = {
                    "into": str(merged.id),
                    "virtual_from": str(drop.id),
                    "payload_ref": str(payload_ref),
                    "meta": meta,
                }

                self._journal.append(
                    JournalEvent(
                        ts=now,
                        graph_id=g_id,
                        op="merge",
                        data=merge_data,
                    )
                )
                self._append_jsonl_journal(now, g_id, "merge", merge_data)

                # P4 hot structures ----------------------------------------
                self._vector_bank.update_vector(graph_id, merged.id, merged.vec)
                self._hot_cache.put(merged.id, merged)

                return merged.id
            # If store is out of sync, fall through and treat as new node.

        # Insert new node ---------------------------------------------------
        ordinal = self._store.count_nodes(g_id)
        raw_id = f"{graph_id}:{ordinal}:{hashlib.sha256(payload_bytes).hexdigest()[:8]}"
        node_id = cast(NodeId, raw_id)

        node = NodeRecord(
            id=node_id,
            graph_id=g_id,
            vec=candidate_vec,
            parents=[ParentRef(parent_id=p.id, fraction=f) for p, f in zip(parents, inh.fractions, strict=False)],
            children=[],
            payload_ref=payload_ref,
            created_at=now,
            last_used_at=now,
            use_count=1,
            merged_count=0,
            flags=0,
        )

        # Core store and indices (P2) ---------------------------------------
        self._store.upsert_node(node)
        self._memory.add(g_id, node_id, node.vec)

        add_data = {
            "node_id": str(node_id),
            "payload_ref": str(payload_ref),
            "meta": meta,
        }

        self._journal.append(
            JournalEvent(
                ts=now,
                graph_id=g_id,
                op="add",
                data=add_data,
            )
        )
        self._append_jsonl_journal(now, g_id, "add", add_data)

        # P4 hot structures --------------------------------------------------
        self._vector_bank.add_vector(graph_id, node_id, node.vec)
        self._hot_cache.put(node_id, node)

        # P5 - Notify analytics scheduler of new node ------------------------
        self._analytics_scheduler.notify_node_added(graph_id)
        if self._evolution_scheduler:
            self._evolution_scheduler.notify_activity(graph_id)

        return node_id

    def retrieve(
        self,
        graph_id: str,
        query: str,
        k: int = 32,
    ) -> List[NodeRecord]:
        """Retrieve up to k nodes for a query.

        Current implementation (P2-compatible):
        - Embed query using DummyEmbedder.
        - Attempt VectorBank-based top-k first (P4 hot path).
        - Fallback to ANN-based top-k (P2 baseline) if VectorBank has
          no entries for the graph.
        - Materialise NodeRecords from FAIMStore and update usage stats.
        """
        g_id = cast(GraphId, graph_id)
        now = time()

        q_vec = self._embedder.encode(query)

        nodes: List[NodeRecord] = []

        # P4: try VectorBank hot path first ---------------------------------
        hits = self._vector_bank.top_k(graph_id, q_vec, k)
        if hits:
            for node_raw, _score in hits:
                node = self._store.get_node(g_id, cast(NodeId, node_raw))
                if node is not None:
                    self._usage.touch(node, at=now)
                    self._store.upsert_node(node)
                    nodes.append(node)
            return nodes

        # P2 baseline: ANN search -------------------------------------------
        if self._memory.size(g_id) == 0:
            return []

        ann_hits = self._memory.search(g_id, q_vec, k)
        for node_id, _score in ann_hits:
            node = self._store.get_node(g_id, node_id)
            if node is not None:
                self._usage.touch(node, at=now)
                self._store.upsert_node(node)
                nodes.append(node)

        return nodes

    def embed(self, text: str) -> Vector:
        """Public API: Embed text into a vector.

        This is the ONLY gateway to embeddings. External code must call this
        method instead of accessing embedder directly.

        Args:
            text: The text to embed.

        Returns:
            A normalized vector representation of the text.
        """
        return self._embedder.encode(text)

    def evolve(self, graph_id: str) -> None:
        """Run Phase P3 evolution for a graph.

        Modes
        -----
        - Graph mode (default):
            Uses evolve_graph_once(...) to apply merge/prune/promote rules
            at the graph level with region proxies.

        - Region mode (enable with FAIM_P3_REGION_MODE=1):
            Uses adapter-based evolve_region(...) over discovered regions.

        This method is deterministic given the same store state and config
        and is safe to call periodically.
        """
        g_id = cast(GraphId, graph_id)
        region_mode = os.getenv("FAIM_P3_REGION_MODE", "").strip().lower() in ("1", "true", "yes")

        if not region_mode:
            # --- Graph-level evolution (simple + fast) ---------------------
            _ = evolve_graph_once(self._store, g_id, config=EvolutionConfig())
            return

        # --- Region-level evolution via internal adapter -------------------
        regions = discover_regions(self._store, g_id, config=EvolutionConfig())
        if not regions:
            return

        reg_map: Dict[str, Region] = {r.region_id: r for r in regions}
        engine = self

        class _EngineEvolutionAdapter(EvolutionAdapter):
            def __init__(self, reg_map: Dict[str, Region]) -> None:
                self._reg_map = reg_map

            def load_region_stats(self, graph_id: str, region_id: str) -> RegionStats:
                r = self._reg_map.get(region_id)
                if r is None:
                    return RegionStats(
                        graph_id=str(graph_id),
                        region_id=str(region_id),
                        node_ids=[],
                        vectors=np.zeros((0, 1), dtype=float),
                        usage_counts=np.zeros((0,), dtype=int),
                        merged_counts=np.zeros((0,), dtype=int),
                        created_ats=np.zeros((0,), dtype=float),
                        redundancy_index=0.0,
                    )

                node_ids: List[str] = []
                vecs: List[np.ndarray] = []
                usage: List[int] = []
                merged: List[int] = []
                created: List[float] = []

                for nid in r.node_ids:
                    n = engine._store.get_node(g_id, nid)
                    if n is None or (n.flags & 0b1):
                        continue
                    node_ids.append(str(n.id))
                    vecs.append(n.vec.astype(float))
                    usage.append(int(n.use_count))
                    merged.append(int(n.merged_count))
                    created.append(float(n.created_at))

                if vecs:
                    V = np.stack(vecs, axis=0)
                else:
                    V = np.zeros((0, 1), dtype=float)

                R = compute_region_redundancy(engine._store, r, config=EvolutionConfig())

                return RegionStats(
                    graph_id=str(graph_id),
                    region_id=str(region_id),
                    node_ids=node_ids,
                    vectors=V,
                    usage_counts=np.asarray(usage, dtype=int),
                    merged_counts=np.asarray(merged, dtype=int),
                    created_ats=np.asarray(created, dtype=float),
                    redundancy_index=float(R),
                )

            def get_query_stats(self, graph_id: str, region_id: str) -> QueryStats:
                # Proxy: use per-node use_count as hits; misses not tracked yet.
                r = self._reg_map.get(region_id)
                hits_map: Dict[str, int] = {}
                total_hits = 0
                if r is not None:
                    for nid in r.node_ids:
                        n = engine._store.get_node(g_id, nid)
                        if n is None or (n.flags & 0b1):
                            continue
                        h = int(max(0, n.use_count))
                        hits_map[str(n.id)] = h
                        total_hits += h
                return QueryStats(hits=total_hits, misses=0, per_node_hits=hits_map)

            def merge_nodes(self, graph_id: str, keep_id: str, drop_id: str) -> None:
                keep = engine._store.get_node(g_id, cast(NodeId, keep_id))
                drop = engine._store.get_node(g_id, cast(NodeId, drop_id))
                if keep is None or drop is None:
                    return

                merged = merge_records(keep, drop)
                engine._store.upsert_node(merged)

                # Tombstone dropped node
                drop = NodeRecord(
                    id=drop.id,
                    graph_id=drop.graph_id,
                    vec=drop.vec,
                    parents=drop.parents,
                    children=drop.children,
                    payload_ref=drop.payload_ref,
                    created_at=drop.created_at,
                    last_used_at=drop.last_used_at,
                    use_count=drop.use_count,
                    merged_count=drop.merged_count + 1,
                    flags=drop.flags | 0b1,
                )
                engine._store.upsert_node(drop)

                # Update indices + hot structures
                engine._ann.update(g_id, merged.id, merged.vec)
                engine._radius.update(g_id, merged.id, merged.vec)
                engine._vector_bank.update_vector(graph_id, merged.id, merged.vec)
                engine._hot_cache.put(merged.id, merged)

                engine._journal.append(
                    JournalEvent(
                        ts=time(),
                        graph_id=g_id,
                        op="merge",
                        data={"into": str(merged.id), "from": str(drop.id)},
                    )
                )

            def prune_node(self, graph_id: str, node_id: str) -> None:
                n = engine._store.get_node(g_id, cast(NodeId, node_id))
                if n is None:
                    return

                # Detach from parents
                for pref in n.parents:
                    p = engine._store.get_node(g_id, pref.parent_id)
                    if p is None:
                        continue
                    if n.id not in p.children:
                        continue
                    new_children = [cid for cid in p.children if cid != n.id]
                    p = NodeRecord(
                        id=p.id,
                        graph_id=p.graph_id,
                        vec=p.vec,
                        parents=p.parents,
                        children=new_children,
                        payload_ref=p.payload_ref,
                        created_at=p.created_at,
                        last_used_at=p.last_used_at,
                        use_count=p.use_count,
                        merged_count=p.merged_count,
                        flags=p.flags,
                    )
                    engine._store.upsert_node(p)

                # Logical delete: set lowest flag bit
                if (n.flags & 0b1) == 0:
                    n = NodeRecord(
                        id=n.id,
                        graph_id=n.graph_id,
                        vec=n.vec,
                        parents=n.parents,
                        children=n.children,
                        payload_ref=n.payload_ref,
                        created_at=n.created_at,
                        last_used_at=n.last_used_at,
                        use_count=n.use_count,
                        merged_count=n.merged_count,
                        flags=n.flags | 0b1,
                    )
                    engine._store.upsert_node(n)

            def promote_node(self, graph_id: str, node_id: str) -> None:
                # Minimal policy: pin node in hot cache.
                n = engine._store.get_node(g_id, cast(NodeId, node_id))
                if n is None:
                    return
                engine._hot_cache.put(n.id, n)

        adapter = _EngineEvolutionAdapter(reg_map)
        cfg = RegionEvolutionConfig()

        for r in regions:
            evolve_region(str(g_id), r.region_id, adapter, config=cfg)

    def shutdown(self) -> None:
        """Perform a clean shutdown.

        - Create a final VectorBank snapshot.
        - Stop the ingest worker thread.
        """
        self._snapshot_manager.create_snapshot(
            None,
            self._vector_bank,
            journal_cutoff_ts=time(),
        )
        self._ingest_worker.stop(graceful=True)
        self._ingest_worker.join()

        # Stop autonomous schedulers
        if self._evolution_scheduler is not None:
            self._evolution_scheduler.stop()
        if self._invention_scheduler is not None:
            self._invention_scheduler.stop()

    # ------------------------------------------------------------------ #
    # JSONL journal mirroring (for SnapshotManager replay)
    # ------------------------------------------------------------------ #

    def _append_jsonl_journal(
        self,
        ts: float,
        graph_id: GraphId,
        op: str,
        data: Dict[str, Any],
    ) -> None:
        """Best-effort mirror of EventJournal entries into JSONL.

        SnapshotManager replays from Runtime/Journal/faim_journal.jsonl.
        This must NEVER raise: if disk/journal is broken, FAIM should still
        run using the SQLite store.
        """
        path = self._snapshot_manager.journal_path
        if path is None:
            return

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "ts": float(ts),
                "graph_id": str(graph_id),
                "op": op,
                "data": data,
            }
            with path.open("a", encoding="utf-8") as f:
                json.dump(entry, f, separators=(",", ":"))
                f.write("\n")
        except Exception:
            # Best-effort only: ignore any journal write failures.
            return

    # ------------------------------------------------------------------ #
    # Journal replay helper (P4.3)
    # ------------------------------------------------------------------ #

    def _apply_journal_entry(self, entry: Dict[str, Any]) -> None:
        """Replay a single journal entry into hot structures.

        Used by SnapshotManager.replay_journal_since(...).

        Expected entry schema (JSON lines written by EventJournal):
        - "op": string (for example "add", "merge").
        - "graph_id": graph identifier.
        - "data": object with operation-specific fields.

        We only care about:
        - "add":   data["node_id"]
        - "merge": data["into"]

        For these events, the corresponding NodeRecord is reloaded from
        FAIMStore (if present) and pushed into VectorBank and HotNodeCache.
        """
        op = entry.get("op")
        if op not in {"add", "merge"}:
            return

        graph_raw = entry.get("graph_id")
        data = entry.get("data") or {}
        if graph_raw is None:
            return

        graph_id = cast(GraphId, str(graph_raw))

        node_id_str: Optional[str]
        if op == "add":
            node_id_str = data.get("node_id")
        else:
            node_id_str = data.get("into")

        if not node_id_str:
            return

        node_id = cast(NodeId, node_id_str)
        node = self._store.get_node(graph_id, node_id)
        if node is None:
            return

        # Update hot structures to reflect journaled state.
        self._vector_bank.add_vector(str(graph_id), node.id, node.vec)
        self._hot_cache.put(node.id, node)
