# =============================================================================
# FAIM — GOLD EDITION (COMMERCIAL / INDUSTRIAL PRODUCTION)
# =============================================================================
# File: faim/api/state.py
#
# PURPOSE
#   - Process-wide state (SQLite store + optional in-process registry cache)
#   - Canonical GraphId coercion helpers
#   - Store helpers used by API layer
#   - Deterministic iteration for tests/UI
#
# HARD RULES (LOCKED)
#   - SQLite store is SOURCE OF TRUTH.
#   - Registry is OPTIONAL cache only; never required for correctness.
#   - Deterministic ordering for tests and UI consistency.
#   - Never raise from helper paths in a way that breaks API stability.
# =============================================================================

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, cast

from faim.core.graph import InMemoryGraphRegistry
from faim.core.types import GraphId, NodeRecord
from faim.storage.sqlite_store import DEFAULT_DB_PATH, SqliteStore

# =============================================================================
# SECTION 0 — REGISTRY (OPTIONAL CACHE; NEVER SOURCE OF TRUTH)
# =============================================================================

GRAPH_REGISTRY = InMemoryGraphRegistry()

# =============================================================================
# SECTION 1 — REPO ROOT + DB PATH (HARDENED)
# =============================================================================


def _repo_root() -> Path:
    """
    Resolve repo root safely.

    - Production: set FAIM_ROOT explicitly (recommended).
    - Dev: fallback to current working directory.

    NOTE: We do NOT import settings here to avoid import cycles.
    """
    raw = (os.getenv("FAIM_ROOT") or ".").strip()
    if not raw:
        raw = "."
    return Path(raw).expanduser().resolve()


def _db_path() -> Path:
    """
    Resolve SQLite DB path.

    Priority:
      1) FAIM_DB_PATH env
      2) <FAIM_ROOT>/Runtime/DB/faim_nodes.sqlite3
    """
    raw = (os.getenv("FAIM_DB_PATH") or "").strip()
    if raw:
        p = Path(raw).expanduser().resolve()
    else:
        p = DEFAULT_DB_PATH
        if not p.is_absolute():
            p = (_repo_root() / p).resolve()

    # Ensure parent exists (safe + idempotent)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


_DB_PATH = _db_path()

# =============================================================================
# SECTION 2 — PERSISTENT STORE (SOURCE OF TRUTH)
# =============================================================================

# SqliteStore is expected to manage connections internally; keep singleton per process.
NODE_STORE = SqliteStore(db_path=str(_DB_PATH))

# =============================================================================
# SECTION 3 — TYPE COERCION (GraphId is NewType(str) in most builds)
# =============================================================================


def _gid(s: str) -> GraphId:
    """
    Canonical coercion to GraphId (usually NewType("GraphId", str)).

    Keep it extremely lightweight and never raise.
    """
    # Normalize to str (defensive). Do NOT change actual graph id semantics.
    try:
        v = s if isinstance(s, str) else str(s)
    except Exception:
        v = ""
    return cast(GraphId, v)


# =============================================================================
# SECTION 4 — STORE HELPERS (USED BY API LAYER)
# =============================================================================


def iter_nodes_from_store(graph_id: str) -> Iterable[NodeRecord]:
    """
    Iterate nodes from SOURCE OF TRUTH.

    IMPORTANT:
      - Return type is Iterable to match existing callers.
      - Underlying store may stream results; do not force list here.
      - Must never throw in normal operation; any store exception should bubble
        only if your store layer already guarantees stability. Otherwise, wrap
        at call sites (API layer already does best-effort).
    """
    return NODE_STORE.iter_nodes(_gid(graph_id))


def count_nodes_from_store(graph_id: str) -> int:
    """
    Count nodes in SOURCE OF TRUTH.
    """
    try:
        return int(NODE_STORE.count_nodes(_gid(graph_id)))
    except Exception:
        # Harden: count failures should not crash upstream metrics endpoints.
        return 0


# =============================================================================
# SECTION 5 — OPTIONAL CACHE WARMUP (BEST-EFFORT ONLY)
# =============================================================================


def ensure_registry_loaded(graph_id: str) -> None:
    """
    Best-effort cache warmup. Never required for correctness.

    Behavior:
      - If registry graph has a .nodes dict and it's empty, populate it once
        from the persistent store.
      - Deterministic insert ordering based on node id string to stabilize tests.

    Safety:
      - Never raises (cache is optional).
    """
    try:
        g = GRAPH_REGISTRY.get_or_create(_gid(graph_id))
        nodes_map = getattr(g, "nodes", None)
        if nodes_map is None:
            return
        if len(nodes_map) > 0:
            return

        # Pull nodes, sort deterministically by id-ish field
        raw_nodes = list(iter_nodes_from_store(graph_id))

        def _node_key(n: object) -> str:
            v = getattr(n, "id", None) or getattr(n, "node_id", None)
            try:
                return str(v) if v is not None else ""
            except Exception:
                return ""

        raw_nodes.sort(key=_node_key)

        for n in raw_nodes:
            nid = getattr(n, "id", None) or getattr(n, "node_id", None)
            if nid is None:
                continue
            # Preserve original key type if possible (some stores use int IDs)
            nodes_map[nid] = n
    except Exception:
        return
