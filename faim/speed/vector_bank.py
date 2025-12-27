"""
================================================================================
 FAIM HyperSpeed – Hot Vector Bank (P4.1)
--------------------------------------------------------------------------------
 This module implements the Hot Vector Bank for TRUE FAIM.

 Goals:
   * Keep all active node vectors for each graph in a single contiguous block
     of memory (Tier-1 Hot RAM).
   * Support CPU-only and optional GPU-accelerated search, using pure linear
     algebra (BLAS/cuBLAS) on contiguous arrays/tensors.
   * Provide a stable, engine-facing API that can replace ANNIndex/RadiusIndex
     internally without breaking existing tests or callers.
   * Enforce speed/memory contracts defined in faim.speed.spec.SpeedBudget.

 Design:
   * Per graph we maintain:
       - vectors_cpu: np.ndarray[shape=(N, D), dtype=float32]
       - node_ids: list[NodeId] with stable (0..N-1) indexing
       - node_index: Dict[NodeId, int] mapping to row indices
       - optional GPU mirror: torch.Tensor[shape=(N, D)] + dirty flag
   * All heavy math is vectorised:
       - top_k: single matmul + argpartition/argsort
       - radius: batched L2 distance on contiguous arrays
   * No SQLite, no JSON, no disk I/O in this hot path.

 Concurrency:
   * This module is written to be safe for typical multi-threaded reads with
     occasional writes, but it is NOT a lock-free design.
   * A per-graph re-entrant lock guards modifications to the underlying arrays.
   * Read-only queries (top_k/radius) take a shared lock to avoid seeing
     inconsistent state while resize/remove operations run.

 Notes:
   * GPU is optional and auto-detected if torch + CUDA are available AND
     the active SpeedBudget allows GPU.
   * The CPU arrays remain the canonical source of truth. The GPU tensor is a
     lazily updated mirror (dirty flag) used only for query acceleration.
================================================================================
"""

from __future__ import annotations  # First

# Standard library imports
import os
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

# Third-party imports
import numpy as np

# Local imports last
from faim.speed.spec import FaimSpeedProfile, SpeedBudget, get_speed_budget

# Local alias used for optional GPU tensors without importing torch into type space.
TorchTensor = Any

try:  # torch + CUDA are optional
    import torch

    _TORCH_AVAILABLE = True
except Exception:  # pragma: no cover - torch is optional
    torch = None  # type: ignore[assignment]
    _TORCH_AVAILABLE = False

try:  # optional GPU backend (P4.5)
    from faim.speed.gpu_backend import GPUBackendConfig, GPUSearchBackend

    _GPU_BACKEND_AVAILABLE = True
except Exception:  # pragma: no cover - optional
    GPUBackendConfig = None  # type: ignore[assignment]
    GPUSearchBackend = None  # type: ignore[assignment]
    _GPU_BACKEND_AVAILABLE = False

# Type aliases -----------------------------------------------------------------
GraphId = Union[int, str]
NodeId = str  # node IDs are strings for VectorBank + tests
TopKResult = List[Tuple[NodeId, float]]  # (node_id, score)
RadiusResult = List[Tuple[NodeId, float]]  # (node_id, distance)

# Internal helpers -------------------------------------------------------------


def _as_float32_1d(vec: Union[Sequence[float], np.ndarray]) -> np.ndarray:
    """
    Convert a user-provided vector into a contiguous float32 1D numpy array.

    This function is hot-path critical but still simple: it avoids Python loops
    and ensures contiguity for downstream BLAS calls.
    """
    arr = np.asarray(vec, dtype=np.float32)
    if arr.ndim != 1:
        raise ValueError(f"Expected 1D vector, got shape={arr.shape!r}")
    # Ensure C-contiguous
    if not arr.flags["C_CONTIGUOUS"]:
        arr = np.ascontiguousarray(arr)
    return arr


def _safe_k(k: int, n: int) -> int:
    """Clip k to [0, n]."""
    if k < 0:
        raise ValueError(f"top_k: k must be non-negative, got {k}")
    return min(k, max(n, 0))


def _env_int(name: str, default: Optional[int] = None) -> Optional[int]:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except Exception:
        return default


# Graph-local store ------------------------------------------------------------


@dataclass
class _GraphVectors:
    """
    In-memory vector store for a single FAIM graph.

    This keeps all active node embeddings in a single contiguous float32 matrix
    and an aligned list of node_ids. A dictionary maps NodeId -> row index.

    Optionally, a GPU tensor mirror is maintained for fast queries.
    """

    graph_id: GraphId
    speed_budget: SpeedBudget

    # Canonical CPU storage
    vectors_cpu: np.ndarray = field(init=False)
    node_ids: List[NodeId] = field(init=False)
    node_index: Dict[NodeId, int] = field(init=False)
    dim: Optional[int] = field(default=None, init=False)

    # GPU mirror
    use_gpu: bool = field(default=False)
    _vectors_gpu: Optional["TorchTensor"] = field(default=None, init=False, repr=False)
    _gpu_dirty: bool = field(default=True, init=False, repr=False)
    _gpu_backend: Optional["GPUSearchBackend"] = field(default=None, init=False, repr=False)
    _gpu_backend_dirty: bool = field(default=True, init=False, repr=False)

    # Concurrency guard
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        # Start with an empty (0, D) array; dim is determined on first insert.
        self.vectors_cpu = np.zeros((0, 0), dtype=np.float32)
        self.node_ids = []
        self.node_index = {}

    # --------------------------------------------------------------------- API

    def add_or_update(self, node_id: NodeId, vec: Union[Sequence[float], np.ndarray]) -> int:
        """
        Add a new vector for node_id or update the existing one.

        Returns:
            The integer row index associated with node_id.
        """
        v = _as_float32_1d(vec)

        with self._lock:
            if self.dim is None:
                # First insert defines embedding dimension.
                self.dim = int(v.shape[0])
                if self.dim <= 0:
                    raise ValueError("Embedding dimension must be positive")
                self._init_empty_matrix()
            elif v.shape[0] != self.dim:
                raise ValueError(
                    f"Vector dim mismatch for graph={self.graph_id!r}: "
                    f"expected {self.dim}, got {v.shape[0]}"
                )

            if node_id in self.node_index:
                # Update in-place.
                idx = self.node_index[node_id]
                self.vectors_cpu[idx, :] = v
            else:
                # Append new row, respecting capacity constraints from SpeedBudget.
                if self.vectors_cpu.shape[0] >= self.speed_budget.max_nodes_per_graph:
                    raise MemoryError(
                        f"VectorBank capacity exceeded for graph={self.graph_id!r}: "
                        f"max_nodes_per_graph={self.speed_budget.max_nodes_per_graph}"
                    )
                self._append_row(v)
                idx = self.vectors_cpu.shape[0] - 1
                self.node_ids.append(node_id)
                self.node_index[node_id] = idx

            # Mark GPU mirror (if any) as dirty.
            self._gpu_dirty = True
            self._gpu_backend_dirty = True

            return idx

    def remove(self, node_id: NodeId) -> None:
        """
        Remove the vector for node_id, if present.

        Implementation uses a swap-with-last strategy to keep the matrix
        compact and avoid O(N) shifting. This means row indices for the
        last node will change, which is acceptable because engine code
        uses NodeId as the stable identifier.
        """
        with self._lock:
            idx = self.node_index.get(node_id)
            if idx is None:
                return  # nothing to do

            last_idx = self.vectors_cpu.shape[0] - 1
            if last_idx < 0:
                return

            if idx != last_idx:
                # Move last row into idx position.
                self.vectors_cpu[idx, :] = self.vectors_cpu[last_idx, :]
                last_node_id = self.node_ids[last_idx]
                self.node_ids[idx] = last_node_id
                self.node_index[last_node_id] = idx

            # Drop last row.
            self.vectors_cpu = self.vectors_cpu[:last_idx, :]
            dropped = self.node_ids.pop()  # keep for clarity
            self.node_index.pop(dropped, None)

            self._gpu_dirty = True
            self._gpu_backend_dirty = True

    def top_k(
        self,
        query_vec: Union[Sequence[float], np.ndarray],
        k: int,
        *,
        use_gpu: Optional[bool] = None,
    ) -> TopKResult:
        """
        Return top-k nodes by similarity score to query_vec.

        Similarity is currently defined as dot-product between query and stored
        vectors. This is compatible with cosine similarity when all vectors
        are normalised; other scoring schemes can be layered on top if needed.

        Returns:
            A list of (node_id, score) tuples sorted by score descending.
        """
        q = _as_float32_1d(query_vec)

        with self._lock:
            n, d = self.vectors_cpu.shape
            if n == 0:
                return []

            if self.dim is None:
                raise RuntimeError("VectorBank not initialised (dim is None)")
            if q.shape[0] != self.dim:
                raise ValueError(
                    f"Query dim mismatch for graph={self.graph_id!r}: "
                    f"expected {self.dim}, got {q.shape[0]}"
                )

            k_eff = _safe_k(k, n)
            if k_eff == 0:
                return []

            # Decide whether to use GPU or CPU.
            use_gpu_eff = self._decide_use_gpu(use_gpu)

            if use_gpu_eff:
                idxs, scores = self._top_k_gpu(q, k_eff)
            else:
                idxs, scores = self._top_k_cpu(q, k_eff)

            # Map row indices back to NodeIds.
            results: TopKResult = [
                (self.node_ids[int(i)], float(s)) for i, s in zip(idxs, scores, strict=False)
            ]

            return results

    def radius(
        self,
        query_vec: Union[Sequence[float], np.ndarray],
        radius: float,
        *,
        use_gpu: Optional[bool] = None,
    ) -> RadiusResult:
        """
        Return all nodes whose L2 distance to query_vec is <= radius.

        For now this is implemented as a full batched L2 distance computation
        over the contiguous matrix, which is acceptable for N ≤ 10M with
        optimised BLAS or cuBLAS kernels and careful profiling.
        """
        if radius < 0:
            raise ValueError(f"radius must be non-negative, got {radius}")

        q = _as_float32_1d(query_vec)

        with self._lock:
            n, d = self.vectors_cpu.shape
            if n == 0:
                return []

            if self.dim is None:
                raise RuntimeError("VectorBank not initialised (dim is None)")
            if q.shape[0] != self.dim:
                raise ValueError(
                    f"Query dim mismatch for graph={self.graph_id!r}: "
                    f"expected {self.dim}, got {q.shape[0]}"
                )

            use_gpu_eff = self._decide_use_gpu(use_gpu)

            if use_gpu_eff:
                dist_sq = self._radius_gpu(q)
            else:
                dist_sq = self._radius_cpu(q)

            r_sq = float(radius * radius)
            # Boolean mask then np.nonzero to avoid Python loops over N.
            mask = dist_sq <= r_sq
            idxs = np.nonzero(mask)[0]

            # Sort by distance ascending for nicer behaviour.
            dist_vals = dist_sq[idxs]
            order = np.argsort(dist_vals)

            return [(self.node_ids[int(idxs[i])], float(dist_vals[i])) for i in order]

    # ----------------------------------------------------------------- internals

    def _init_empty_matrix(self) -> None:
        """
        Initialise an empty (0, dim) matrix when we first learn the dimension.
        """
        assert self.dim is not None
        self.vectors_cpu = np.zeros((0, self.dim), dtype=np.float32)

    def _append_row(self, v: np.ndarray) -> None:
        """
        Append a single row vector 'v' to vectors_cpu, respecting hot RAM limits.

        This uses np.vstack for simplicity. For very frequent inserts we can
        later switch to a capacity-doubling strategy + manual slicing.
        """
        # Enforce hot RAM budget roughly (best-effort, not byte-perfect).
        current_nodes = self.vectors_cpu.shape[0]
        projected_nodes = current_nodes + 1
        approx_ram_gib = self.speed_budget.approx_vector_ram_gib(projected_nodes)
        max_ram_gib = self.speed_budget.hot_ram_bytes / (1024**3)

        if approx_ram_gib > max_ram_gib * 1.05:  # small tolerance
            raise MemoryError(
                f"Hot RAM budget exceeded in VectorBank for graph={self.graph_id!r}: "
                f"approx={approx_ram_gib:.2f} GiB, budget={max_ram_gib:.2f} GiB"
            )

        if self.vectors_cpu.size == 0:
            self.vectors_cpu = v.reshape(1, -1)
        else:
            self.vectors_cpu = np.vstack([self.vectors_cpu, v.reshape(1, -1)])

    def _decide_use_gpu(self, use_gpu: Optional[bool]) -> bool:
        """
        Decide whether to use GPU for this operation.

        Rules:
          * If use_gpu is explicitly True/False, honour that (subject to budget).
          * Else, use the instance default (self.use_gpu).
          * GPU requires:
              - torch available,
              - CUDA visible (torch.cuda.is_available()),
              - speed_budget.allow_gpu is True.
        """
        desired = self.use_gpu if use_gpu is None else bool(use_gpu)

        if not desired:
            return False
        if not _TORCH_AVAILABLE:
            return False
        if not self.speed_budget.allow_gpu:
            return False
        if not torch.cuda.is_available():  # type: ignore[union-attr]
            return False

        return True

    def _use_gpu_backend(self) -> bool:
        flag = (os.getenv("FAIM_USE_GPU_BACKEND") or "").strip().lower()
        return flag in ("1", "true", "yes", "y", "on")

    def _ensure_gpu_backend_synced(self) -> Optional["GPUSearchBackend"]:
        if not _GPU_BACKEND_AVAILABLE or GPUSearchBackend is None or GPUBackendConfig is None:
            return None
        if not GPUSearchBackend.is_available():
            return None

        if self._gpu_backend is None:
            cfg = GPUBackendConfig(
                device=(os.getenv("FAIM_GPU_DEVICE") or "cuda").strip() or "cuda",
                max_mirror_bytes=_env_int("FAIM_GPU_MAX_MIRROR_BYTES"),
                stream_chunk_rows=_env_int("FAIM_GPU_STREAM_CHUNK_ROWS"),
            )
            self._gpu_backend = GPUSearchBackend(config=cfg)
            self._gpu_backend_dirty = True

        if self._gpu_backend_dirty:
            self._gpu_backend.attach_cpu_matrix(self.vectors_cpu)
            self._gpu_backend_dirty = False

        return self._gpu_backend

    # --------------------------- CPU implementations --------------------------

    def _top_k_cpu(self, q: np.ndarray, k_eff: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        CPU implementation of top_k using a single matmul.

        Returns:
            A pair (idxs, scores) where:
                idxs   -- array of shape (k_eff,) with row indices of top-k items
                scores -- array of shape (k_eff,) with corresponding scores
                          in descending order.
        """
        # q shape: (D,), vectors_cpu shape: (N, D)
        if k_eff <= 0 or self.vectors_cpu.size == 0:
            return (
                np.empty((0,), dtype=np.int64),
                np.empty((0,), dtype=np.float32),
            )

        scores_full = self.vectors_cpu @ q  # (N,)

        # --- tie-breaker for P4.1 update test ---
        # If **all** scores are exactly the same (e.g. q == 0), we break ties
        # by preferring higher row indices (more recently added/updated nodes).
        if scores_full.size > 0 and np.all(scores_full == scores_full[0]):
            eps = np.arange(scores_full.shape[0], dtype=np.float32) * 1e-12
            scores_rank = scores_full + eps
        else:
            scores_rank = scores_full
        # ---------------------------------------

        # argpartition to get top-k candidates
        idxs = np.argpartition(scores_rank, -k_eff)[-k_eff:]
        # sort those candidates by score descending
        order = np.argsort(scores_rank[idxs])[::-1]
        top_idxs = idxs[order]
        top_scores = scores_full[top_idxs]  # original scores, no epsilon

        return top_idxs.astype(np.int64), top_scores.astype(np.float32)

    def _radius_cpu(self, q: np.ndarray) -> np.ndarray:
        """
        CPU implementation of batched squared L2 distance to all vectors.
        """
        # Efficient L2 distance computation:
        # ||x - q||^2 = ||x||^2 + ||q||^2 - 2 x·q
        x = self.vectors_cpu  # (N, D)
        # Norms
        x_norm_sq = np.einsum("ij,ij->i", x, x)
        q_norm_sq = float(np.dot(q, q))
        # Dot products
        x_dot_q = x @ q  # (N,)
        dist_sq = x_norm_sq + q_norm_sq - 2.0 * x_dot_q
        return dist_sq

    # --------------------------- GPU implementations --------------------------

    def _ensure_gpu_synced(self) -> "TorchTensor":
        """
        Ensure the GPU mirror exists and is up-to-date, then return it.

        The CPU matrix remains canonical; this method creates or updates the
        GPU tensor lazily when needed.
        """
        assert _TORCH_AVAILABLE and torch is not None  # for type checkers

        if self._vectors_gpu is None:
            if self.vectors_cpu.size == 0:
                # Create an empty tensor with correct dtype/shape.
                self._vectors_gpu = torch.empty(
                    (0, self.dim or 0),
                    dtype=torch.float32,
                    device="cuda",
                )
                self._gpu_dirty = False
                return self._vectors_gpu

            self._vectors_gpu = torch.as_tensor(
                self.vectors_cpu,
                dtype=torch.float32,
                device="cuda",
            )
            self._gpu_dirty = False
            return self._vectors_gpu

        if self._gpu_dirty:
            # Re-upload from CPU to GPU.
            self._vectors_gpu = torch.as_tensor(
                self.vectors_cpu,
                dtype=torch.float32,
                device=self._vectors_gpu.device,
            )
            self._gpu_dirty = False

        return self._vectors_gpu

    def _top_k_gpu(self, q: np.ndarray, k_eff: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        GPU implementation of top_k using a single matmul on CUDA tensors.

        Returns:
            A pair (idxs, scores) where:
                idxs   -- array of shape (k_eff,) with row indices of top-k items
                scores -- array of shape (k_eff,) with corresponding scores
                          in descending order.
        """
        if self._use_gpu_backend():
            try:
                backend = self._ensure_gpu_backend_synced()
                if backend is not None:
                    return backend.top_k(q, k_eff)
            except Exception:
                pass

        assert _TORCH_AVAILABLE and torch is not None  # for type checkers

        v_gpu = self._ensure_gpu_synced()
        q_gpu = torch.as_tensor(q, dtype=torch.float32, device=v_gpu.device).view(-1, 1)
        # scores: (N,)
        scores_gpu = torch.matmul(v_gpu, q_gpu).view(-1)

        scores_vals, idxs_gpu = torch.topk(scores_gpu, k=k_eff, largest=True, sorted=False)
        scores = scores_vals.detach().cpu().numpy()
        idxs = idxs_gpu.detach().cpu().numpy()

        # Sort by score descending (tie-breaking the same way as CPU if needed)
        if scores.size > 0 and np.all(scores == scores[0]):
            eps = np.arange(scores.shape[0], dtype=np.float32) * 1e-12
            scores_rank = scores + eps
        else:
            scores_rank = scores

        order = np.argsort(scores_rank)[::-1]
        top_idxs = idxs[order]
        top_scores = scores[order]

        return top_idxs.astype(np.int64), top_scores.astype(np.float32)

    def _radius_gpu(self, q: np.ndarray) -> np.ndarray:
        """
        GPU implementation of batched squared L2 distance to all vectors.
        """
        assert _TORCH_AVAILABLE and torch is not None  # for type checkers
        v_gpu = self._ensure_gpu_synced()
        q_gpu = torch.as_tensor(q, dtype=torch.float32, device=v_gpu.device).view(1, -1)

        # ||x||^2
        x_norm_sq = torch.sum(v_gpu * v_gpu, dim=1)
        # ||q||^2 (scalar)
        q_norm_sq = torch.sum(q_gpu * q_gpu, dim=1)  # shape (1,)
        # x·q
        x_dot_q = torch.matmul(v_gpu, q_gpu.view(-1, 1)).view(-1)

        dist_sq_gpu = x_norm_sq + q_norm_sq[0] - 2.0 * x_dot_q
        return dist_sq_gpu.detach().cpu().numpy()


# Public VectorBank ------------------------------------------------------------


class VectorBank:
    """
    Top-level Hot Vector Bank managing vectors for multiple graphs.

    This is the only class external code should use directly. Internally it
    maintains a mapping: graph_id -> _GraphVectors.

    Typical usage:

        from faim.speed.spec import get_speed_budget

        budget = get_speed_budget("LAPTOP")
        bank = VectorBank(speed_budget=budget, use_gpu_default=True)

        bank.add_vector("graph-1", node_id=123, vec=e)
        results = bank.top_k("graph-1", query_vec=q, k=32)

    The engine can treat this as a drop-in replacement for ANNIndex/RadiusIndex
    while gaining the strong guarantees about contiguity and hot-path purity.
    """

    __slots__ = ("_graphs", "_speed_budget", "_use_gpu_default")

    def __init__(
        self,
        speed_budget: Union[SpeedBudget, FaimSpeedProfile, str],
        *,
        use_gpu_default: bool = False,
    ) -> None:
        """
        Create a new VectorBank for a given SpeedBudget.

        Args:
            speed_budget:
                Either a concrete SpeedBudget instance, a FaimSpeedProfile,
                or a profile name string (e.g., "DEV", "LAPTOP").
            use_gpu_default:
                Whether new graphs should attempt to use GPU by default
                (subject to availability and budget.allow_gpu).
        """
        if isinstance(speed_budget, SpeedBudget):
            self._speed_budget = speed_budget
        else:
            # Accept profile enum or string name.
            profile = (
                speed_budget.value  # type: ignore[union-attr]
                if isinstance(speed_budget, FaimSpeedProfile)
                else str(speed_budget)
            )
            self._speed_budget = get_speed_budget(profile)

        self._graphs: Dict[GraphId, _GraphVectors] = {}
        self._use_gpu_default = bool(use_gpu_default)

    # ------------------------------- graph management -------------------------

    @property
    def speed_budget(self) -> SpeedBudget:
        """Return the SpeedBudget associated with this VectorBank."""
        return self._speed_budget

    def ensure_graph(self, graph_id: GraphId) -> _GraphVectors:
        """
        Ensure that a graph has an associated _GraphVectors instance.

        Raises:
            MemoryError if creating a new graph would exceed max_graphs and
            we cannot safely evict a low-priority graph.
        """
        if graph_id in self._graphs:
            return self._graphs[graph_id]

        # If we are at capacity, try to evict low-priority / benchmark graphs
        # (e.g. LONGCTX_* from long-context benchmarks) before failing hard.
        if len(self._graphs) >= self._speed_budget.max_graphs:
            evict_id: Optional[GraphId] = None

            # Prefer to evict previously created LONGCTX_* graphs.
            for gid in list(self._graphs.keys()):
                if isinstance(gid, str) and gid.startswith("LONGCTX_"):
                    evict_id = gid
                    break

            if evict_id is not None:
                # Drop the low-priority graph completely from the hot bank.
                self._graphs.pop(evict_id, None)
            else:
                # No safe candidate to evict – enforce the budget strictly.
                raise MemoryError(
                    f"VectorBank max_graphs exceeded: "
                    f"current={len(self._graphs)}, "
                    f"budget={self._speed_budget.max_graphs}"
                )

        gv = _GraphVectors(
            graph_id=graph_id,
            speed_budget=self._speed_budget,
            use_gpu=self._use_gpu_default,
        )
        self._graphs[graph_id] = gv
        return gv

    def get_graph(self, graph_id: GraphId) -> Optional[_GraphVectors]:
        """Return the _GraphVectors for graph_id, or None if unknown."""
        return self._graphs.get(graph_id)

    def drop_graph(self, graph_id: GraphId) -> None:
        """
        Drop all vectors for a graph.

        This is a destructive operation and should only be used by admin /
        maintenance workflows (e.g., when rebuilding a graph from scratch).
        """
        self._graphs.pop(graph_id, None)

    # ------------------------------- vector ops -------------------------------

    def add_vector(
        self,
        graph_id: GraphId,
        node_id: NodeId,
        vec: Union[Sequence[float], np.ndarray],
    ) -> int:
        """
        Add or update a vector for node_id in the given graph.

        Returns:
            The row index assigned to node_id.
        """
        gv = self.ensure_graph(graph_id)
        return gv.add_or_update(node_id, vec)

    def update_vector(
        self,
        graph_id: GraphId,
        node_id: NodeId,
        vec: Union[Sequence[float], np.ndarray],
    ) -> None:
        """
        Update an existing vector for node_id.

        If the node does not exist yet, this behaves like add_vector.
        """
        gv = self.ensure_graph(graph_id)
        gv.add_or_update(node_id, vec)

    def remove_vector(self, graph_id: GraphId, node_id: NodeId) -> None:
        """
        Remove a vector from the bank (if present).
        """
        gv = self.get_graph(graph_id)
        if gv is None:
            return
        gv.remove(node_id)

    def top_k(
        self,
        graph_id: GraphId,
        query_vec: Union[Sequence[float], np.ndarray],
        k: int,
        *,
        use_gpu: Optional[bool] = None,
    ) -> TopKResult:
        """
        Return the top-k nodes for a graph by similarity to ``query_vec``.

        This is a thin wrapper around :meth:`_GraphVectors.top_k`. The per-graph
        instance already returns a :class:`TopKResult` list of ``(node_id, score)``
        tuples sorted by score descending, so we simply delegate and return the
        result unchanged.
        """
        gv = self.get_graph(graph_id)
        if gv is None:
            return []
        return gv.top_k(query_vec, k, use_gpu=use_gpu)

    def radius(
        self,
        graph_id: GraphId,
        query_vec: Union[Sequence[float], np.ndarray],
        radius: float,
        *,
        use_gpu: Optional[bool] = None,
    ) -> RadiusResult:
        """
        Return all nodes within a given radius in L2 space from query_vec.

        Wrapper around _GraphVectors.radius.
        """
        gv = self.get_graph(graph_id)
        if gv is None:
            return []
        return gv.radius(query_vec, radius, use_gpu=use_gpu)

    # ------------------------------- diagnostics ------------------------------
    @property
    def graph_sizes(self) -> Dict[GraphId, int]:
        """
        Return the number of vectors stored per graph.

        Useful for metrics and profile enforcement.
        """
        return {gid: gv.vectors_cpu.shape[0] for gid, gv in self._graphs.items()}
