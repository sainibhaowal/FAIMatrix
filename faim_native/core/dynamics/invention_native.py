"""FAIM-Native Invention.

Deterministic macro-node creation from co-activation patterns.

Rules:
- Track co-activation using EventJournal
- If same set repeats >= N times, create macro node
- λ (evolution pressure) must be >= threshold
- Expected redundancy reduction must be positive
- v_native = normalized mean of member vectors
- level = max(parents.level) + 1
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple
from uuid import UUID

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import uuid7  # noqa: F401
    from faim.Faim_Native.core.metrics.fractal_physics import (  # noqa: F401
        DEFAULT_CONFIG,
        FractalDiagnostics,
        compute_diagnostics,
    )
    from faim.Faim_Native.encoding.vector_schema import VECTOR_DIMENSION
    from faim.Faim_Native.store.pg.repos.edge_repo import EdgeRepo
    from faim.Faim_Native.store.pg.repos.node_repo import NodeRepo
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.metrics.fractal_physics import compute_diagnostics
    from encoding.vector_schema import VECTOR_DIMENSION
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.node_repo import NodeRepo


# Default thresholds for invention
LAMBDA_THRESHOLD: float = 0.3  # Minimum λ to trigger invention
MIN_COACTIVATION_COUNT: int = 3  # Minimum times a set must repeat
MIN_REDUNDANCY_REDUCTION: float = 0.01  # Minimum expected redundancy reduction


@dataclass
class InventionResult:
    """Result of invention operation.

    Attributes:
        macros_created: Number of macro nodes created.
        events_emitted: Number of events emitted.
        macro_ids: List of created macro node IDs.
        lambda_hat: λ value at time of invention.
        redundancy_reduced: Estimated redundancy reduction.
    """

    macros_created: int = 0
    events_emitted: int = 0
    macro_ids: List[UUID] = field(default_factory=list)
    lambda_hat: float = 0.0
    redundancy_reduced: float = 0.0
    processed_events: int = 0
    signatures_tracked: int = 0
    skipped_candidates: int = 0
    last_event_seq: int = 0


def _l2_normalize(vector: List[float]) -> List[float]:
    """L2 normalize a vector."""
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def compute_mean_vector(vectors: List[List[float]]) -> List[float]:
    """Compute mean of vectors.

    Args:
        vectors: List of v_native vectors.

    Returns:
        L2-normalized mean vector.
    """
    if not vectors:
        return [0.0] * VECTOR_DIMENSION

    dim = len(vectors[0])
    n = len(vectors)

    mean = [0.0] * dim
    for v in vectors:
        for i, val in enumerate(v):
            mean[i] += val / n

    return _l2_normalize(mean)


def compute_macro_hash(member_ids: List[str]) -> str:
    """Compute hash for macro node.

    Args:
        member_ids: Sorted list of member node IDs.

    Returns:
        SHA256 hash.
    """
    sorted_ids = sorted(member_ids)
    json_str = json.dumps(sorted_ids, separators=(",", ":"))
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def compute_redundancy_reduction(
    member_vectors: List[List[float]],
    mean_vector: List[float],
) -> float:
    """Estimate redundancy reduction from creating macro.

    Measures how much redundancy is absorbed by the macro node.
    Higher value = more redundant pairs absorbed.

    Args:
        member_vectors: Vectors of member nodes.
        mean_vector: Mean vector (macro representation).

    Returns:
        Estimated redundancy reduction in [0, 1].
    """
    if len(member_vectors) < 2:
        return 0.0

    # Count high-similarity pairs among members
    pair_count = 0
    high_sim_pairs = 0
    threshold = 0.8

    for i in range(len(member_vectors)):
        for j in range(i + 1, len(member_vectors)):
            sim = _cosine_similarity(member_vectors[i], member_vectors[j])
            pair_count += 1
            if sim > threshold:
                high_sim_pairs += 1

    if pair_count == 0:
        return 0.0

    # Redundancy reduction = fraction of high-sim pairs absorbed
    return high_sim_pairs / pair_count


def should_invent(
    lambda_hat: float,
    coactivation_count: int,
    redundancy_reduction: float,
    *,
    lambda_threshold: float = LAMBDA_THRESHOLD,
    min_count: int = MIN_COACTIVATION_COUNT,
    min_reduction: float = MIN_REDUNDANCY_REDUCTION,
) -> bool:
    """Determine if invention should proceed.

    Invention requires all conditions:
    1. λ >= lambda_threshold (evolution pressure)
    2. coactivation_count >= min_count (repeated pattern)
    3. redundancy_reduction >= min_reduction (benefit)

    Args:
        lambda_hat: Current evolution pressure.
        coactivation_count: Times this set was co-activated.
        redundancy_reduction: Expected redundancy reduction.
        lambda_threshold: Minimum λ required.
        min_count: Minimum co-activation count.
        min_reduction: Minimum redundancy reduction.

    Returns:
        True if invention should proceed.
    """
    return (
        lambda_hat >= lambda_threshold
        and coactivation_count >= min_count
        and redundancy_reduction >= min_reduction
    )


def find_coactivation_sets(
    events: List[Dict[str, Any]],
    min_count: int = 3,
    min_set_size: int = 2,
) -> List[Tuple[FrozenSet[str], int]]:
    """Find repeated co-activation sets from events.

    Args:
        events: List of event records with kind and payload.
        min_count: Minimum repetitions to qualify.
        min_set_size: Minimum nodes in a set.

    Returns:
        List of (node_id_set, count) tuples sorted by count desc.
    """
    set_counts: Counter = Counter()

    # Track node sets from NODE_UPSERT batches (grouped by GRAPH_VERSION_BUMP)
    current_batch: Set[str] = set()

    for event in events:
        kind = event.get("kind") or (event.kind if hasattr(event, "kind") else None)
        payload = event.get("payload") or (
            event.payload if hasattr(event, "payload") else {}
        )

        if kind == "NODE_UPSERT":
            node_id = payload.get("node_id")
            if node_id:
                current_batch.add(node_id)
        elif kind == "GRAPH_VERSION_BUMP":
            if len(current_batch) >= min_set_size:
                set_counts[frozenset(current_batch)] += 1
            current_batch = set()

    # Handle final batch
    if len(current_batch) >= min_set_size:
        set_counts[frozenset(current_batch)] += 1

    # Filter and sort
    result = [
        (node_set, count)
        for node_set, count in set_counts.items()
        if count >= min_count and len(node_set) >= min_set_size
    ]
    result.sort(key=lambda x: (-x[1], sorted(x[0])))

    return result


def invent_macro(
    graph_id: str,
    member_ids: List[UUID],
    node_repo: NodeRepo,
    edge_repo: EdgeRepo,
    event_repo,
    *,
    lambda_hat: Optional[float] = None,
    coactivation_count: int = MIN_COACTIVATION_COUNT,
    skip_lambda_check: bool = False,
    lambda_threshold: float = LAMBDA_THRESHOLD,
    min_count: int = MIN_COACTIVATION_COUNT,
    min_reduction: float = MIN_REDUNDANCY_REDUCTION,
) -> Optional[UUID]:
    """Create a macro node from members with λ check.

    Args:
        graph_id: Graph identifier.
        member_ids: List of member node IDs.
        node_repo: Node repository.
        edge_repo: Edge repository.
        event_repo: Event repository.
        lambda_hat: Current evolution pressure (optional, will compute if None).
        coactivation_count: How many times this set was co-activated.
        skip_lambda_check: Skip λ threshold check (for testing).

    Returns:
        Macro node ID or None if failed or conditions not met.
    """
    if len(member_ids) < 2:
        return None

    # Get member vectors
    member_vectors = []
    member_nodes = []
    max_level = 0

    for mid in member_ids:
        node = node_repo.get_node(graph_id, mid)
        if node:
            member_nodes.append(node)
            member_vectors.append(node.v_native)
            max_level = max(max_level, node.level or 0)

    if len(member_vectors) < 2:
        return None

    # Compute mean vector
    mean_vector = compute_mean_vector(member_vectors)

    # Compute redundancy reduction
    redundancy_reduction = compute_redundancy_reduction(member_vectors, mean_vector)

    # Compute λ if not provided
    if lambda_hat is None:
        nodes = node_repo.list_nodes(graph_id, limit=1000)
        edges = edge_repo.list_all_edges(graph_id, limit=10000)
        vectors = [n.v_native for n in nodes if n.v_native]
        residuals = [(n.residual / 1e9 if n.residual else 0.0) for n in nodes]

        if vectors:
            diag = compute_diagnostics(
                graph_id=graph_id,
                vectors=vectors,
                residuals=residuals,
                edge_count=len(edges),
                graph_version=0,
            )
            lambda_hat = diag.lambda_hat
        else:
            lambda_hat = 0.0

    # Check invention conditions
    if not skip_lambda_check:
        if not should_invent(
            lambda_hat,
            coactivation_count,
            redundancy_reduction,
            lambda_threshold=lambda_threshold,
            min_count=min_count,
            min_reduction=min_reduction,
        ):
            return None

    # Compute hash
    vector_hash = compute_macro_hash([str(m) for m in member_ids])

    # Check if macro already exists
    existing = node_repo.get_by_vector_hash(graph_id, vector_hash)
    if existing:
        return existing.node_id

    # Build opp_signature
    opp_signature = {
        "norm": 1.0,
        "density": 1.0,
        "member_count": len(member_ids),
        "lambda_at_invention": round(lambda_hat, 6),
        "redundancy_reduction": round(redundancy_reduction, 6),
    }

    # Compute residual for macro
    # Residual = 1 - avg similarity to parents
    parent_sims = [_cosine_similarity(mean_vector, pv) for pv in member_vectors]
    avg_sim = sum(parent_sims) / len(parent_sims) if parent_sims else 0
    residual = max(0.0, min(1.0, 1.0 - avg_sim))

    # Create macro node with level = max(parents) + 1
    macro_level = max_level + 1

    macro_id = node_repo.create_macro_node(
        graph_id=graph_id,
        v_native=mean_vector,
        vector_hash=vector_hash,
        opp_signature=opp_signature,
        level=macro_level,
        residual=residual,
    )

    # Set inheritance edges from members to macro
    # Each member contributes equally
    fraction = 1.0 / len(member_ids)
    parents = [(mid, fraction) for mid in member_ids]
    edge_repo.set_inheritance_parents(
        graph_id=graph_id,
        child_id=macro_id,
        parents=parents,
    )

    # Emit event with full diagnostics reference
    session = getattr(node_repo, "session", None)
    if session is not None:
        event_repo.emit(
            session=session,
            graph_id=graph_id,
            kind="INVENT_MACRO_NODE",
            payload={
                "macro_id": str(macro_id),
                "member_ids": [str(m) for m in member_ids],
                "level": macro_level,
                "lambda_hat": round(lambda_hat, 6),
                "redundancy_reduction": round(redundancy_reduction, 6),
                "coactivation_count": coactivation_count,
            },
        )

    return macro_id


def _normalize_signature_counts(
    raw_counts: Optional[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Normalize persisted signature-count payload."""
    if not isinstance(raw_counts, dict):
        return {}

    normalized: Dict[str, Dict[str, Any]] = {}
    for signature, value in raw_counts.items():
        if not isinstance(signature, str):
            continue
        if not isinstance(value, dict):
            continue
        members = value.get("members")
        if not isinstance(members, list):
            continue
        clean_members = sorted(
            [str(m) for m in members if isinstance(m, str) and m.strip()]
        )
        if len(clean_members) < 2:
            continue
        normalized[signature] = {
            "count": int(max(0, int(value.get("count", 0)))),
            "members": clean_members,
            "last_seq": int(max(0, int(value.get("last_seq", 0)))),
            "invented": bool(value.get("invented", False)),
        }
    return normalized


def run_invention_cycle(
    graph_id: str,
    *,
    session: Any,
    node_repo: NodeRepo,
    edge_repo: EdgeRepo,
    event_repo: Any,
    state_repo: Any,
    lambda_hat: float,
    min_coactivation_count: int = MIN_COACTIVATION_COUNT,
    lambda_threshold: float = LAMBDA_THRESHOLD,
    min_redundancy_reduction: float = MIN_REDUNDANCY_REDUCTION,
    max_macros_per_cycle: int = 3,
    event_window: int = 5000,
    max_tracked_signatures: int = 1000,
    max_member_set_size: int = 32,
    event_page_size: int = 500,
) -> InventionResult:
    """Run incremental, bounded invention over newly appended events.

    This is the runtime-safe bridge that wires invention into evolve flows.
    """
    result = InventionResult(lambda_hat=lambda_hat)
    state = state_repo.get_or_create(graph_id=graph_id, session=session)

    try:
        latest_seq = int(event_repo.get_max_seq(session, graph_id))
    except Exception:
        latest_seq = 0

    result.last_event_seq = latest_seq
    if latest_seq <= 0:
        return result

    start_seq = int(max(0, state.last_event_seq or 0))
    window_floor = max(0, latest_seq - max(100, int(event_window)))
    if start_seq < window_floor:
        start_seq = window_floor

    signature_counts = _normalize_signature_counts(state.signature_counts)
    # Drop stale signatures that have not been seen in the active window.
    signature_counts = {
        key: value
        for key, value in signature_counts.items()
        if value["last_seq"] >= start_seq
    }

    after_seq = start_seq
    pending_nodes: Set[str] = set()
    while True:
        events = event_repo.get_by_seq(
            session,
            graph_id=graph_id,
            after_seq=after_seq,
            limit=max(50, int(event_page_size)),
        )
        if not events:
            break

        for event in events:
            payload = event.payload if isinstance(event.payload, dict) else {}
            if event.kind == "NODE_UPSERT":
                node_id = payload.get("node_id")
                if isinstance(node_id, str) and node_id:
                    pending_nodes.add(node_id)
            elif event.kind == "GRAPH_VERSION_BUMP":
                if 2 <= len(pending_nodes) <= max_member_set_size:
                    members = sorted(pending_nodes)
                    signature = compute_macro_hash(members)
                    entry = signature_counts.get(signature) or {
                        "count": 0,
                        "members": members,
                        "last_seq": 0,
                        "invented": False,
                    }
                    entry["count"] = int(entry.get("count", 0)) + 1
                    entry["members"] = members
                    entry["last_seq"] = int(event.seq or 0)
                    signature_counts[signature] = entry
                pending_nodes.clear()
            after_seq = max(after_seq, int(event.seq or 0))
            result.processed_events += 1

        if len(events) < max(50, int(event_page_size)):
            break

    if not signature_counts:
        state_repo.save(
            graph_id=graph_id,
            last_event_seq=after_seq,
            signature_counts={},
            last_cycle_macros=0,
            last_cycle_at=datetime.now(timezone.utc),
            session=session,
        )
        result.last_event_seq = after_seq
        return result

    candidates = sorted(
        [
            (signature, data)
            for signature, data in signature_counts.items()
            if not data.get("invented")
            and int(data.get("count", 0)) >= int(min_coactivation_count)
        ],
        key=lambda item: (-int(item[1].get("count", 0)), item[0]),
    )

    for _signature, data in candidates:
        if result.macros_created >= max(0, int(max_macros_per_cycle)):
            break

        members_raw = data.get("members") or []
        if not isinstance(members_raw, list):
            result.skipped_candidates += 1
            continue
        if not (2 <= len(members_raw) <= max_member_set_size):
            result.skipped_candidates += 1
            continue

        member_ids: List[UUID] = []
        for node_id in members_raw:
            try:
                parsed = UUID(str(node_id))
            except (ValueError, TypeError):
                continue
            if node_repo.get_by_id(graph_id, parsed) is None:
                continue
            member_ids.append(parsed)

        if len(member_ids) < 2:
            result.skipped_candidates += 1
            continue

        vector_hash = compute_macro_hash([str(mid) for mid in member_ids])
        existing_macro = node_repo.get_by_vector_hash(graph_id, vector_hash)
        if existing_macro is not None:
            data["invented"] = True
            data["last_seq"] = max(int(data.get("last_seq", 0)), after_seq)
            continue

        macro_id = invent_macro(
            graph_id=graph_id,
            member_ids=member_ids,
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            lambda_hat=lambda_hat,
            coactivation_count=int(data.get("count", 0)),
            skip_lambda_check=False,
            lambda_threshold=lambda_threshold,
            min_count=min_coactivation_count,
            min_reduction=min_redundancy_reduction,
        )
        if macro_id is None:
            result.skipped_candidates += 1
            continue

        data["invented"] = True
        data["last_seq"] = max(int(data.get("last_seq", 0)), after_seq)
        result.macros_created += 1
        result.events_emitted += 1
        result.macro_ids.append(macro_id)

    if len(signature_counts) > max(10, int(max_tracked_signatures)):
        ordered = sorted(
            signature_counts.items(),
            key=lambda item: (int(item[1].get("last_seq", 0)), item[0]),
            reverse=True,
        )
        signature_counts = dict(ordered[: max(10, int(max_tracked_signatures))])

    state_repo.save(
        graph_id=graph_id,
        last_event_seq=after_seq,
        signature_counts=signature_counts,
        last_cycle_macros=result.macros_created,
        last_cycle_at=datetime.now(timezone.utc),
        session=session,
    )
    result.last_event_seq = after_seq
    result.signatures_tracked = len(signature_counts)
    return result


# Exports
__all__ = [
    "InventionResult",
    "LAMBDA_THRESHOLD",
    "MIN_COACTIVATION_COUNT",
    "MIN_REDUNDANCY_REDUCTION",
    "compute_mean_vector",
    "compute_macro_hash",
    "compute_redundancy_reduction",
    "should_invent",
    "find_coactivation_sets",
    "invent_macro",
    "run_invention_cycle",
]
