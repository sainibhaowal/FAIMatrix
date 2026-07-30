"""
================================================================================
 FAIM HyperSpeed – GPU Backend (P4.5)
--------------------------------------------------------------------------------
 This module implements an optional GPU acceleration backend for TRUE FAIM.

 Goals:
   * Provide a reusable, graph-agnostic GPU search primitive that:
       - Accepts a CPU matrix of shape (N, D), dtype float32
       - Maintains an optional GPU mirror for fast queries
       - Falls back to streaming (chunked) GPU search when N·D is too large
   * Offer BLAS/cuBLAS-based top-k and radius queries:
       - scores = vectors @ query
       - L2 distance via ||x||^2 + ||q||^2 - 2 x·q

 Design:
   * GPUBackendConfig controls:
       - device string (e.g. "cuda:0")
       - max_mirror_bytes: upper bound for full GPU mirror; beyond this we
         use streaming mode
       - stream_chunk_rows: chunk size for streaming queries
   * GPUSearchBackend:
       - attach_cpu_matrix(vectors_cpu)
       - top_k(query_vec, k)
       - radius(query_vec, r)
       - internal mode: "mirror" or "streaming"
   * This module does NOT know about NodeIds or VectorBank internals. It works
     purely with row indices; callers (e.g. _GraphVectors) map indices to
     NodeIds as needed.

 Notes:
   * If torch or CUDA are not available, this backend reports itself as
     unavailable and raises RuntimeError on use. Callers should then fall
     back to CPU-only search in VectorBank.
   * This backend is compatible with classic dense embeddings and with
     hyperdimensional-style vectors (HDC) as long as they are represented as
     float32 arrays. More exotic HDC operations can be added later.

================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

import numpy as np

# Local alias used for optional GPU tensors without importing torch into type space.
# This keeps Pylance/mypy happy even if torch is missing, while runtime still uses torch.
TorchTensor = Any


try:  # torch + CUDA are optional
    import torch

    _TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover - torch is optional
    torch = None  # type: ignore[assignment]
    _TORCH_AVAILABLE = False

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class GPUBackendConfig:
    """
    Configuration for GPUSearchBackend.

    Attributes:
        device:
            CUDA device string, e.g. "cuda" or "cuda:0".
        max_mirror_bytes:
            Maximum allowed size for a full (N, D) GPU mirror in bytes.
            If the CPU matrix requires more than this, the backend switches
            to streaming mode. None means "no limit" (still subject to
            actual hardware capacity).
        stream_chunk_rows:
            Row count per chunk when running in streaming mode.
            Each chunk is uploaded to GPU, matmul is computed, and results
            are merged on CPU.
    """

    device: str = "cuda"
    max_mirror_bytes: Optional[int] = None
    stream_chunk_rows: Optional[int] = None  # auto if None


# --------------------------------------------------------------------------- #
# Backend
# --------------------------------------------------------------------------- #


class GPUSearchBackend:
    """
    GPU-accelerated search over a CPU vector matrix.

    This backend is intentionally unaware of FAIM graphs or NodeIds; it works
    solely with row indices. A caller such as VectorBank._GraphVectors can
    attach its CPU matrix and then call top_k / radius with query vectors.

    Modes:
        - "mirror":
            Keep a full GPU tensor mirror of the CPU matrix for fastest
            queries (top_k and radius).
        - "streaming":
            Do not hold a full GPU mirror; instead stream CPU chunks to GPU
            per query. Uses more PCIe traffic but scales beyond VRAM size.

    Usage:

        cfg = GPUBackendConfig(
            device="cuda:0",
            max_mirror_bytes=3 * 1024**3,  # ~3 GiB
        )
        backend = GPUSearchBackend(config=cfg)

        backend.attach_cpu_matrix(vectors_cpu)  # shape (N, D), float32

        idxs, scores = backend.top_k(query_vec, k=64)
        idxs_r, dists = backend.radius(query_vec, r=1.5)

    """

    __slots__ = (
        "_config",
        "_vectors_cpu",
        "_vectors_gpu",
        "_mode",
        "_dim",
        "_n_rows",
        "_stream_chunk_rows",
        "_max_mirror_bytes",
    )

    def __init__(self, config: Optional[GPUBackendConfig] = None) -> None:
        """
        Initializes the GPU search backend with optional configuration settings.

        :param config: Optional configuration for the backend. Defaults to GPUBackendConfig().
        """
        if config is None:
            config = GPUBackendConfig()
        self._config = config

        self._vectors_cpu: Optional[np.ndarray] = None
        self._vectors_gpu: Optional[TorchTensor] = None
        if _TORCH_AVAILABLE:
            self._vectors_gpu = None

        self._mode: Optional[str] = None  # "mirror" or "streaming"
        self._dim: int = 0
        self._n_rows: int = 0
        self._stream_chunk_rows: Optional[int] = None
        self._max_mirror_bytes: Optional[int] = None

    # ----------------------------------------------------------------- tuning

    def _cuda_mem_info(self) -> Tuple[int, int]:
        if not self.is_available():
            return 0, 0
        assert torch is not None  # nosec B101 - type checker hint
        try:
            return torch.cuda.mem_get_info(self._config.device)  # type: ignore[arg-type]
        except Exception:
            try:
                return torch.cuda.mem_get_info()
            except Exception:
                return 0, 0

    def _auto_max_mirror_bytes(self) -> int:
        free_bytes, total_bytes = self._cuda_mem_info()
        if free_bytes <= 0 and total_bytes <= 0:
            return 0
        free = free_bytes if free_bytes > 0 else total_bytes
        target = int(free * 0.6)
        floor = 256 * 1024 * 1024
        return max(target, floor)

    def _auto_stream_chunk_rows(self, dim: int) -> int:
        free_bytes, total_bytes = self._cuda_mem_info()
        free = free_bytes if free_bytes > 0 else total_bytes
        if free <= 0 or dim <= 0:
            return 250_000

        target = min(int(free * 0.2), 512 * 1024 * 1024)
        target = max(target, 32 * 1024 * 1024)
        bytes_per_row = int(dim) * 4
        rows = max(1, target // max(bytes_per_row, 1))
        return int(min(max(rows, 1_000), 1_000_000))

    # ------------------------------------------------------------------ status

    @staticmethod
    def is_available() -> bool:
        """
        Return True if torch with CUDA is available, False otherwise.
        """
        if not _TORCH_AVAILABLE:
            return False
        assert torch is not None  # nosec B101 - type checker hint
        return torch.cuda.is_available()  # type: ignore[union-attr]

    @property
    def mode(self) -> Optional[str]:
        return self._mode

    @property
    def n_rows(self) -> int:
        return self._n_rows

    @property
    def dim(self) -> int:
        return self._dim

    # ---------------------------------------------------------------- attach/detach

    def attach_cpu_matrix(self, vectors_cpu: np.ndarray) -> None:
        """
        Attach a CPU matrix for GPU-accelerated search.

        Args:
            vectors_cpu:
                numpy array of shape (N, D), dtype float32, C-contiguous.

        This method inspects the matrix size and decides whether to:
            - allocate a full GPU mirror ("mirror" mode), or
            - keep only the CPU reference and use streaming ("streaming" mode).

        If GPU is not available, this method raises RuntimeError. Callers
        should check is_available() before creating the backend.
        """
        if not self.is_available():
            raise RuntimeError("GPUSearchBackend.attach_cpu_matrix: CUDA not available")

        assert torch is not None  # nosec B101 - type checker hint

        arr = np.asarray(vectors_cpu, dtype=np.float32)
        if arr.ndim != 2:
            raise ValueError(f"Expected 2D matrix, got shape={arr.shape!r}")
        if not arr.flags["C_CONTIGUOUS"]:
            arr = np.ascontiguousarray(arr)

        n, d = arr.shape
        if n == 0:
            self._vectors_cpu = arr
            self._vectors_gpu = None
            self._n_rows = 0
            self._dim = d
            self._mode = "mirror"
            return

        bytes_needed = int(n) * int(d) * 4  # float32 = 4 bytes
        max_mirror = self._config.max_mirror_bytes
        if max_mirror is None or max_mirror <= 0:
            max_mirror = self._auto_max_mirror_bytes()
        self._max_mirror_bytes = max_mirror

        stream_rows = self._config.stream_chunk_rows
        if stream_rows is None or stream_rows <= 0:
            stream_rows = self._auto_stream_chunk_rows(d)
        self._stream_chunk_rows = int(stream_rows)

        self._vectors_cpu = arr
        self._n_rows = int(n)
        self._dim = int(d)

        mode = "mirror"
        if max_mirror is not None and bytes_needed > max_mirror:
            mode = "streaming"

        if mode == "mirror":
            try:
                if _TORCH_AVAILABLE:
                    self._vectors_gpu = torch.as_tensor(
                        arr,
                        dtype=torch.float32,
                        device=self._config.device,
                    )

                else:
                    self._vectors_gpu = None
                self._mode = "mirror"
            except RuntimeError:
                self._vectors_gpu = None
                self._mode = "streaming"
        else:
            self._vectors_gpu = None
            self._mode = "streaming"

    def detach(self) -> None:
        """
        Detach any attached matrix and free GPU memory held by this backend.
        """
        self._vectors_cpu = None
        self._vectors_gpu = None
        self._mode = None
        self._dim = 0
        self._n_rows = 0

    # ------------------------------------------------------------------ queries

    def top_k(
        self,
        query_vec: np.ndarray,
        k: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute top-k similarity scores for query_vec against all rows.

        Similarity is defined as dot product between query and each row of
        the attached matrix. Both query and matrix rows are expected to be
        float32 vectors of dimension D.

        Args:
            query_vec:
                1D numpy array of shape (D,), dtype float32.
            k:
                Number of best matches to return.

        Returns:
            (indices, scores) where:
                indices: np.ndarray[int64] of shape (k_eff,)
                scores: np.ndarray[float32] of shape (k_eff,)
            k_eff = min(k, N).

        Raises:
            RuntimeError if no matrix is attached or GPU is not available.
        """
        if self._vectors_cpu is None:
            raise RuntimeError("GPUSearchBackend.top_k: no matrix attached")

        if k <= 0 or self._n_rows == 0:
            return np.empty((0,), dtype=np.int64), np.empty((0,), dtype=np.float32)

        if not self.is_available():
            raise RuntimeError("GPUSearchBackend.top_k: CUDA not available")

        q = np.asarray(query_vec, dtype=np.float32)
        if q.ndim != 1:
            raise ValueError(f"Expected 1D query vector, got shape={q.shape!r}")
        if q.shape[0] != self._dim:
            raise ValueError(
                f"Query dim mismatch: expected {self._dim}, got {q.shape[0]}"
            )

        k_eff = min(k, self._n_rows)

        if self._mode == "mirror":
            return self._top_k_mirror(q, k_eff)
        elif self._mode == "streaming":
            return self._top_k_streaming(q, k_eff)
        else:
            raise RuntimeError(f"GPUSearchBackend.top_k: invalid mode={self._mode!r}")

    def radius(
        self,
        query_vec: np.ndarray,
        radius: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute all rows whose L2 distance to query_vec is <= radius.

        Args:
            query_vec:
                1D numpy array of shape (D,), dtype float32.
            radius:
                Distance threshold (non-negative).

        Returns:
            (indices, distances) where:
                indices: np.ndarray[int64] of shape (M,)
                distances: np.ndarray[float32] of shape (M,)
            M is the number of rows within the radius.

        Raises:
            RuntimeError if no matrix is attached or GPU is not available.
        """
        if radius < 0:
            raise ValueError(f"radius must be non-negative, got {radius}")

        if self._vectors_cpu is None:
            raise RuntimeError("GPUSearchBackend.radius: no matrix attached")

        if self._n_rows == 0:
            return np.empty((0,), dtype=np.int64), np.empty((0,), dtype=np.float32)

        if not self.is_available():
            raise RuntimeError("GPUSearchBackend.radius: CUDA not available")

        q = np.asarray(query_vec, dtype=np.float32)
        if q.ndim != 1:
            raise ValueError(f"Expected 1D query vector, got shape={q.shape!r}")
        if q.shape[0] != self._dim:
            raise ValueError(
                f"Query dim mismatch: expected {self._dim}, got {q.shape[0]}"
            )

        if self._mode == "mirror":
            return self._radius_mirror(q, radius)
        elif self._mode == "streaming":
            return self._radius_streaming(q, radius)
        else:
            raise RuntimeError(f"GPUSearchBackend.radius: invalid mode={self._mode!r}")

    def radius_search(
        self,
        query_vec: np.ndarray,
        threshold: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compatibility alias for radius() used by P4.5 tests.

        Args:
            query_vec:
                1D numpy array of shape (D,), dtype float32.
            threshold:
                Distance threshold (non-negative), forwarded to radius().
        """
        return self.radius(query_vec, radius=threshold)

    # ------------------------------------------------------------------ internals

    # -- mirror mode (full GPU tensor) ----------------------------------------

    def _top_k_mirror(
        self,
        q: np.ndarray,
        k_eff: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        assert self._vectors_gpu is not None  # nosec B101 - runtime invariant
        assert torch is not None  # nosec B101 - type checker hint

        v_gpu = self._vectors_gpu
        q_gpu = torch.as_tensor(q, dtype=torch.float32, device=v_gpu.device).view(-1, 1)

        scores_gpu = torch.matmul(v_gpu, q_gpu).view(-1)
        scores_vals, idxs_gpu = torch.topk(
            scores_gpu, k=k_eff, largest=True, sorted=True
        )

        scores = scores_vals.detach().cpu().numpy()
        idxs = idxs_gpu.detach().cpu().numpy().astype(np.int64)
        return idxs, scores

    def _radius_mirror(
        self,
        q: np.ndarray,
        radius: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        assert self._vectors_gpu is not None  # nosec B101 - runtime invariant
        assert torch is not None  # nosec B101 - type checker hint

        v_gpu = self._vectors_gpu
        q_gpu = torch.as_tensor(q, dtype=torch.float32, device=v_gpu.device).view(1, -1)

        x_norm_sq = torch.sum(v_gpu * v_gpu, dim=1)
        q_norm_sq = torch.sum(q_gpu * q_gpu, dim=1)[0]
        x_dot_q = torch.matmul(v_gpu, q_gpu.view(-1, 1)).view(-1)

        dist_sq_gpu = x_norm_sq + q_norm_sq - 2.0 * x_dot_q
        dist_sq = dist_sq_gpu.detach().cpu().numpy()

        r_sq = float(radius * radius)
        mask = dist_sq <= r_sq
        idxs = np.nonzero(mask)[0]
        if idxs.size == 0:
            return idxs.astype(np.int64), np.empty((0,), dtype=np.float32)

        dvals = dist_sq[idxs]
        order = np.argsort(dvals)
        return idxs[order].astype(np.int64), dvals[order].astype(np.float32)

    # -- streaming mode (chunked GPU search) ----------------------------------

    def _top_k_streaming(
        self,
        q: np.ndarray,
        k_eff: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        assert self._vectors_cpu is not None  # nosec B101 - runtime invariant
        assert torch is not None  # nosec B101 - type checker hint

        N = self._n_rows
        chunk_rows = max(
            1, int(self._stream_chunk_rows or self._config.stream_chunk_rows or 250_000)
        )
        device = self._config.device

        # Initialise global top-k buffers.
        best_scores = np.full((k_eff,), -np.inf, dtype=np.float32)
        best_indices = np.full((k_eff,), -1, dtype=np.int64)

        q_gpu = torch.as_tensor(q, dtype=torch.float32, device=device).view(-1, 1)

        for start in range(0, N, chunk_rows):
            end = min(start + chunk_rows, N)
            chunk = self._vectors_cpu[start:end, :]  # type: ignore[index]

            if chunk.size == 0:
                continue

            v_gpu = torch.as_tensor(
                chunk,
                dtype=torch.float32,
                device=device,
            )
            scores_gpu = torch.matmul(v_gpu, q_gpu).view(-1)
            scores_chunk = scores_gpu.detach().cpu().numpy()

            # Local top-k within chunk.
            if scores_chunk.shape[0] <= k_eff:
                local_idx = np.arange(scores_chunk.shape[0], dtype=np.int64)
            else:
                local_idx = np.argpartition(scores_chunk, -k_eff)[-k_eff:].astype(
                    np.int64
                )

            local_scores = scores_chunk[local_idx]
            local_indices = local_idx + start

            # Merge global + local top-k.
            merged_scores = np.concatenate([best_scores, local_scores])
            merged_indices = np.concatenate([best_indices, local_indices])

            top_idx = np.argpartition(merged_scores, -k_eff)[-k_eff:]
            best_scores = merged_scores[top_idx]
            best_indices = merged_indices[top_idx]

        # Sort final results by score descending.
        order = np.argsort(best_scores)[::-1]
        scores_sorted = best_scores[order]
        idxs_sorted = best_indices[order]

        # Remove any remaining sentinel (-1) indices (in case N < k).
        valid_mask = idxs_sorted >= 0
        return idxs_sorted[valid_mask], scores_sorted[valid_mask]

    def _radius_streaming(
        self,
        q: np.ndarray,
        radius: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        assert self._vectors_cpu is not None  # nosec B101 - runtime invariant
        assert torch is not None  # nosec B101 - type checker hint

        N = self._n_rows
        chunk_rows = max(
            1, int(self._stream_chunk_rows or self._config.stream_chunk_rows or 250_000)
        )
        device = self._config.device

        q_gpu = torch.as_tensor(q, dtype=torch.float32, device=device).view(1, -1)
        q_norm_sq_val = float(np.dot(q, q))
        r_sq = float(radius * radius)

        all_indices: list[int] = []
        all_dists: list[float] = []

        for start in range(0, N, chunk_rows):
            end = min(start + chunk_rows, N)
            chunk = self._vectors_cpu[start:end, :]  # type: ignore[index]

            if chunk.size == 0:
                continue

            v_gpu = torch.as_tensor(
                chunk,
                dtype=torch.float32,
                device=device,
            )

            x_norm_sq = torch.sum(v_gpu * v_gpu, dim=1)
            x_dot_q = torch.matmul(v_gpu, q_gpu.view(-1, 1)).view(-1)

            dist_sq_gpu = x_norm_sq + q_norm_sq_val - 2.0 * x_dot_q
            dist_sq = dist_sq_gpu.detach().cpu().numpy()

            mask = dist_sq <= r_sq
            idxs = np.nonzero(mask)[0]
            if idxs.size == 0:
                continue

            dvals = dist_sq[idxs]
            for i, d in zip(idxs, dvals, strict=False):
                all_indices.append(int(start + i))
                all_dists.append(float(d))

        if not all_indices:
            return np.empty((0,), dtype=np.int64), np.empty((0,), dtype=np.float32)

        idx_arr = np.asarray(all_indices, dtype=np.int64)
        dist_arr = np.asarray(all_dists, dtype=np.float32)
        order = np.argsort(dist_arr)
        return idx_arr[order], dist_arr[order]
