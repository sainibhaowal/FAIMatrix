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

from sqlalchemy.exc import IntegrityError

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
    from core.cognitive.cognitive_typing import CognitiveType
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
    # Non-fatal subsystem failures are returned to the evolution orchestrator
    # instead of being indistinguishable from an empty/no-op cycle.
    errors: List[str] = field(default_factory=list)


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


def _derive_member_labels(
    graph_id: str,
    member_nodes: List[Any],
    node_repo: NodeRepo,
    session: Any,
) -> List[str]:
    """Extract concise human-readable concept labels for macro constituents."""
    repr_by_id: Dict[str, str] = {}
    if session is not None and member_nodes:
        try:
            from store.pg.repos.representation_repo import RepresentationRepo

            rrepo = RepresentationRepo(
                session=session, tenant_id=getattr(node_repo, "tenant_id", "default")
            )
            rows = rrepo.list_by_node_ids(
                graph_id=graph_id,
                node_ids=[n.node_id for n in member_nodes],
            )
            repr_by_id = {
                str(r.node_id): str(getattr(r, "normalized_text", "") or "").strip()
                for r in rows
            }
        except Exception:  # nosec B110 - best effort label resolution
            repr_by_id = {}

    snippets: List[str] = []
    seen = set()
    for n in member_nodes:
        nid = str(getattr(n, "node_id", ""))
        text = repr_by_id.get(nid, "")
        if not text:
            sig = getattr(n, "opp_signature", None) or {}
            if isinstance(sig, dict):
                text = str(sig.get("title") or sig.get("label") or "").strip()
        if not text:
            anchor = getattr(n, "anchor_json", None) or {}
            if isinstance(anchor, dict):
                text = str(anchor.get("text") or anchor.get("canonical") or "").strip()
        if text:
            clean = " ".join(text.split())
            if len(clean) > 36:
                clean = f"{clean[:33].rstrip()}..."
            key = clean.lower()
            if key not in seen:
                seen.add(key)
                snippets.append(clean)
    return snippets


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
    synthesis_origin: str = "coactivation",
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

    # Create macro node with level = max(parents) + 1
    macro_level = max_level + 1
    session = getattr(node_repo, "session", None)

    # Compute residual and Coefficient of Fractional Parentage (CFP) weights
    parent_sims = [_cosine_similarity(mean_vector, pv) for pv in member_vectors]
    avg_sim = sum(parent_sims) / len(parent_sims) if parent_sims else 0.0
    residual = max(0.08, min(0.85, 1.0 - avg_sim))

    raw_weights: List[float] = []
    for n, sim in zip(member_nodes, parent_sims, strict=False):
        mass = max(1.0, float(getattr(n, "touch_count", 1) or 1))
        raw_weights.append(mass * max(0.05, float(sim)))
    w_sum = sum(raw_weights)
    if w_sum > 0:
        cfp_weights = [round(w / w_sum, 6) for w in raw_weights]
    else:
        cfp_weights = [round(1.0 / len(member_nodes), 6) for _ in member_nodes]

    # Build human-readable macro title and summary
    snippets = _derive_member_labels(graph_id, member_nodes, node_repo, session)
    if snippets:
        joined = " ⊗ ".join(snippets[:3])
        macro_title = f"Macro: {joined}"
        if len(macro_title) > 120:
            macro_title = f"{macro_title[:117].rstrip()}..."
    else:
        macro_title = (
            f"Synthesized Macro [L{macro_level}] ({len(member_nodes)} constituents)"
        )

    weight_preview = ", ".join(f"{w:.2f}" for w in cfp_weights[:4])
    macro_summary = (
        f"Level-{macro_level} abstraction synthesized from {len(member_nodes)} "
        f"constituent nodes via {synthesis_origin} (CFP weights: {weight_preview})."
    )

    # Build opp_signature
    opp_signature = {
        "norm": 1.0,
        "density": 1.0,
        "member_count": len(member_nodes),
        "lambda_at_invention": round(lambda_hat, 6),
        "redundancy_reduction": round(redundancy_reduction, 6),
        "title": macro_title,
        "summary": macro_summary,
        "synthesis_origin": synthesis_origin,
        "weights": {
            str(n.node_id): round(float(w), 4)
            for n, w in zip(member_nodes, cfp_weights, strict=False)
        },
    }

    # Determine dominant cognitive type from members
    member_types = [n.cognitive_type for n in member_nodes if n.cognitive_type]
    if member_types:
        # Vote: use the most common type among members
        cognitive_type = Counter(member_types).most_common(1)[0][0]
    else:
        # No member types available — try to classify from member text content
        # This handles older nodes ingested before the classifier was wired.
        try:
            from core.cognitive.cognitive_typing import classify_cognitive_type

            texts: list = []
            for n in member_nodes:
                anchor = getattr(n, "anchor_json", None) or {}
                if isinstance(anchor, dict):
                    t = anchor.get("text", "") or anchor.get("canonical", "")
                    if t:
                        texts.append(t)
            if texts:
                # Combine first 3 member texts for speed; classify the result
                combined = " ".join(texts[:3])
                cognitive_type = classify_cognitive_type(combined).value
            else:
                cognitive_type = CognitiveType.FACT.value
        except Exception:
            # Safe fallback — never break invention on a classify error
            cognitive_type = CognitiveType.FACT.value

    # Galaxy ID - usually macros are within one document's galaxy.
    # If all members share same galaxy_id, propagate it.
    member_galaxies = [n.galaxy_id for n in member_nodes if n.galaxy_id]
    galaxy_id = None
    if member_galaxies and len(set(member_galaxies)) == 1:
        galaxy_id = member_galaxies[0]

    macro_id = node_repo.create_macro_node(
        graph_id=graph_id,
        v_native=mean_vector,
        vector_hash=vector_hash,
        opp_signature=opp_signature,
        level=macro_level,
        residual=residual,
        cognitive_type=cognitive_type,
        galaxy_id=galaxy_id,
    )

    # Best-effort persist normalized text representation for search & UI labels
    if session is not None:
        try:
            from encoding.representation_v2 import build_representation_v2
            from store.pg.repos.representation_repo import RepresentationRepo

            with session.begin_nested():
                repr_repo = RepresentationRepo(
                    session=session,
                    tenant_id=getattr(node_repo, "tenant_id", "default"),
                )
                repr_v2 = build_representation_v2(
                    f"{macro_title}. {macro_summary}",
                    display_text=macro_title,
                )
                repr_repo.upsert_node_representation(graph_id, macro_id, repr_v2)
        except Exception:  # nosec B110 - representation sidecar is optional
            pass

    # Set weighted CFP inheritance edges from constituent members to macro
    parents = [
        (n.node_id, float(w)) for n, w in zip(member_nodes, cfp_weights, strict=False)
    ]
    edge_repo.set_inheritance_parents(
        graph_id=graph_id,
        child_id=macro_id,
        parents=parents,
    )

    # Emit event with full diagnostics reference
    if session is not None:
        event_repo.emit(
            session=session,
            graph_id=graph_id,
            kind="INVENT_MACRO_NODE",
            payload={
                "macro_id": str(macro_id),
                "title": macro_title,
                "synthesis_origin": synthesis_origin,
                "member_ids": [str(n.node_id) for n in member_nodes],
                "weights": opp_signature.get("weights", {}),
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
    max_member_set_size: int = 32,
    **kwargs,  # Accept ignored legacy parameters
) -> InventionResult:
    """Run incremental, bounded invention over newly appended events.

    This is the runtime-safe bridge that wires invention into evolve flows.
    """
    result = InventionResult(lambda_hat=lambda_hat)

    # We still fetch state to update last_cycle_macros, but we no longer
    # need to track signature_counts natively.
    state_repo.get_or_create(graph_id=graph_id, session=session)

    try:
        latest_seq = int(event_repo.get_max_seq(session, graph_id))
    except Exception as exc:
        latest_seq = 0
        result.errors.append(f"event_cursor:{type(exc).__name__}")
    result.last_event_seq = latest_seq
    signature_snapshot: Dict[str, Dict[str, Any]] = {}

    # 1. Fetch pending inventions directly from the synchronous DB table
    try:
        candidates = node_repo.get_pending_inventions(
            graph_id=graph_id,
            min_count=min_coactivation_count,
            limit=max_macros_per_cycle * 2,
        )
    except Exception as exc:
        candidates = []
        result.errors.append(f"candidate_load:{type(exc).__name__}")

    # 2. Iterate and invent
    for data in candidates:
        if result.macros_created >= max(0, int(max_macros_per_cycle)):
            break

        signature = data.get("signature")
        members_raw = data.get("members") or []
        count = data.get("count", 0)
        clean_members = sorted(
            [
                str(node_id)
                for node_id in members_raw
                if isinstance(node_id, (str, UUID)) and str(node_id).strip()
            ]
        )
        if isinstance(signature, str) and signature.strip() and len(clean_members) >= 2:
            signature_snapshot[signature] = {
                "count": int(max(0, int(count or 0))),
                "members": clean_members,
                "last_seq": latest_seq,
                "invented": False,
            }

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
            # Already exists, just mark it invented
            try:
                node_repo.mark_invented(graph_id, signature)
            except Exception as exc:
                result.errors.append(f"mark_invented:{type(exc).__name__}")
            snapshot_entry = (
                signature_snapshot.get(signature)
                if isinstance(signature, str)
                else None
            )
            if snapshot_entry is not None:
                snapshot_entry["invented"] = True
            continue

        try:
            with session.begin_nested():
                macro_id = invent_macro(
                    graph_id=graph_id,
                    member_ids=member_ids,
                    node_repo=node_repo,
                    edge_repo=edge_repo,
                    event_repo=event_repo,
                    lambda_hat=lambda_hat,
                    coactivation_count=count,
                    skip_lambda_check=False,
                    lambda_threshold=lambda_threshold,
                    min_count=min_coactivation_count,
                    min_reduction=min_redundancy_reduction,
                )
        except IntegrityError:
            macro_id = None
            existing_macro = node_repo.get_by_vector_hash(graph_id, vector_hash)
            if existing_macro is not None:
                macro_id = existing_macro.node_id
                try:
                    node_repo.mark_invented(graph_id, signature)
                except Exception as exc:
                    result.errors.append(f"mark_invented:{type(exc).__name__}")
        except Exception as exc:
            macro_id = None
            result.errors.append(f"macro_create:{type(exc).__name__}")

        if macro_id is None:
            result.skipped_candidates += 1
            continue

        # Successfully invented! Mark it in the table.
        try:
            node_repo.mark_invented(graph_id, signature)
        except Exception as exc:
            result.errors.append(f"mark_invented:{type(exc).__name__}")
        snapshot_entry = (
            signature_snapshot.get(signature) if isinstance(signature, str) else None
        )
        if snapshot_entry is not None:
            snapshot_entry["invented"] = True

        result.macros_created += 1
        result.events_emitted += 1
        result.macro_ids.append(macro_id)

    # 3. Update legacy state table to satisfy callers expecting last_cycle_at
    state_repo.save(
        graph_id=graph_id,
        last_event_seq=latest_seq,
        signature_counts=signature_snapshot,
        last_cycle_macros=result.macros_created,
        last_cycle_at=datetime.now(timezone.utc),
        session=session,
    )

    result.signatures_tracked = 0
    return result


# =============================================================================
# Cross-galaxy synthesis → invention bridge
# =============================================================================


def invent_from_synthesis_insights(
    graph_id: str,
    *,
    session: Any,
    node_repo: NodeRepo,
    edge_repo: EdgeRepo,
    event_repo: Any,
    insights: List[Any],
    lambda_hat: float,
    lambda_threshold: float = LAMBDA_THRESHOLD,
    max_macros: int = 3,
    min_evidence: int = 2,
    min_confidence: float = 0.6,
    galaxy_count_for_cross: int = 2,
) -> InventionResult:
    """Invent macro nodes from cross-galaxy synthesis insights.

    A synthesized insight (correlation, trend, causal chain) that draws
    evidence from >= ``galaxy_count_for_cross`` distinct galaxies is a
    natural invention candidate: its evidence nodes represent a recurring
    cross-document pattern worth abstracting into a macro.

    Rules (mirror coactivation invention):
    - λ >= lambda_threshold (evolution pressure).
    - confidence >= min_confidence.
    - evidence spans >= galaxy_count_for_cross distinct galaxies.
    - bounded by max_macros per cycle.
    - idempotent: an existing macro with the same member hash is reused.

    Never raises; best effort.
    """
    result = InventionResult(lambda_hat=lambda_hat)
    if lambda_hat < lambda_threshold:
        result.skipped_candidates += 1
        return result

    def _evidence_node_ids(insight: Any) -> List[str]:
        evidence = getattr(insight, "evidence_nodes", None) or []
        node_ids: List[str] = []
        for ev in evidence:
            nid = None
            if isinstance(ev, dict):
                nid = ev.get("node_id")
            elif hasattr(ev, "node_id"):
                nid = getattr(ev, "node_id", None)
            if nid:
                node_ids.append(str(nid))
        return list(dict.fromkeys(node_ids))

    def _supporting_galaxies(insight: Any) -> List[str]:
        primary = getattr(insight, "primary_galaxy", None) or ""
        supporting = list(getattr(insight, "supporting_galaxies", None) or [])
        galaxies = set(str(g) for g in [primary] + supporting if g)
        return sorted(galaxies)

    candidates = []
    for insight in insights:
        try:
            confidence = float(getattr(insight, "confidence", 0.0) or 0.0)
            node_ids = _evidence_node_ids(insight)
            galaxies = _supporting_galaxies(insight)
            if (
                confidence < min_confidence
                or len(node_ids) < min_evidence
                or len(galaxies) < galaxy_count_for_cross
            ):
                result.skipped_candidates += 1
                continue
            candidates.append((node_ids, galaxies, confidence))
        except Exception as exc:
            result.skipped_candidates += 1
            result.errors.append(f"insight_parse:{type(exc).__name__}")
            continue

    # Deterministic order: highest confidence first, then stable hash.
    candidates.sort(key=lambda c: (-c[2], str(sorted(c[0]))))
    candidates = candidates[: max(0, int(max_macros))]

    for node_ids, galaxies, confidence in candidates:
        member_ids: List[UUID] = []
        for nid in node_ids:
            try:
                parsed = UUID(str(nid))
            except (ValueError, TypeError):
                continue
            if node_repo.get_by_id(graph_id, parsed) is None:
                continue
            member_ids.append(parsed)
        if len(member_ids) < min_evidence:
            result.skipped_candidates += 1
            continue

        vector_hash = compute_macro_hash([str(mid) for mid in member_ids])
        existing_macro = node_repo.get_by_vector_hash(graph_id, vector_hash)
        if existing_macro is not None:
            continue

        try:
            with session.begin_nested():
                macro_id = invent_macro(
                    graph_id=graph_id,
                    member_ids=member_ids,
                    node_repo=node_repo,
                    edge_repo=edge_repo,
                    event_repo=event_repo,
                    lambda_hat=lambda_hat,
                    coactivation_count=2,
                    skip_lambda_check=False,
                    lambda_threshold=lambda_threshold,
                    min_count=2,
                    min_reduction=0.0,
                )
        except IntegrityError:
            macro_id = None
        except Exception as exc:
            macro_id = None
            result.errors.append(f"synthesis_macro_create:{type(exc).__name__}")

        if macro_id is None:
            result.skipped_candidates += 1
            continue

        result.macros_created += 1
        result.events_emitted += 1
        result.macro_ids.append(macro_id)

        try:
            event_repo.emit(
                session=session,
                graph_id=graph_id,
                kind="EVOLUTION_INVENTION_SYNTHESIS",
                payload={
                    "macro_id": str(macro_id),
                    "member_ids": [str(m) for m in member_ids],
                    "lambda_hat": round(lambda_hat, 6),
                    "confidence": round(float(confidence), 6),
                    "galaxies": galaxies,
                },
            )
        except Exception as exc:
            result.errors.append(f"synthesis_event_emit:{type(exc).__name__}")

    return result


def _synthesize_for_graph(
    graph_id: str,
    session: Any,
    tenant_id: str,
    max_galaxies: int = 5,
    errors: Optional[List[str]] = None,
) -> List[Any]:
    """Run cross-galaxy synthesis over the graph's galaxies (best effort)."""
    try:
        from core.reasoning.cross_galaxy import CrossGalaxySynthesizer
        from store.pg.models_faim import NodeModel

        rows = (
            session.query(NodeModel.galaxy_id)
            .filter(
                NodeModel.tenant_id == tenant_id,
                NodeModel.graph_id == graph_id,
                NodeModel.galaxy_id.isnot(None),
                NodeModel.galaxy_id != "",
            )
            .distinct()
            .limit(max_galaxies)
            .all()
        )
        galaxy_ids = [r[0] for r in rows]
        if len(galaxy_ids) < 2:
            return []

        synthesizer = CrossGalaxySynthesizer(session, tenant_id)
        return synthesizer.synthesize(
            galaxy_ids=galaxy_ids,
            topic=None,
            max_galaxies=max_galaxies,
        )
    except Exception as exc:
        if errors is not None:
            errors.append(f"synthesis_load:{type(exc).__name__}")
        return []


def _invent_from_theories_and_clusters(
    graph_id: str,
    *,
    session: Any,
    node_repo: NodeRepo,
    edge_repo: EdgeRepo,
    event_repo: Any,
    lambda_hat: float,
    lambda_threshold: float,
    remaining_macros: int,
    result: InventionResult,
) -> None:
    """Fallback deterministic synthesis from GraphTheory & structural hub clusters."""
    if remaining_macros <= 0 or session is None or lambda_hat < lambda_threshold:
        return

    tenant_id = getattr(node_repo, "tenant_id", "default")

    def _try_create(member_ids: List[UUID], origin: str) -> bool:
        if len(member_ids) < 2:
            return False
        vhash = compute_macro_hash([str(mid) for mid in member_ids])
        if node_repo.get_by_vector_hash(graph_id, vhash) is not None:
            return False
        try:
            with session.begin_nested():
                macro_id = invent_macro(
                    graph_id=graph_id,
                    member_ids=member_ids,
                    node_repo=node_repo,
                    edge_repo=edge_repo,
                    event_repo=event_repo,
                    lambda_hat=lambda_hat,
                    coactivation_count=2,
                    skip_lambda_check=False,
                    lambda_threshold=lambda_threshold,
                    min_count=2,
                    min_reduction=0.0,
                    synthesis_origin=origin,
                )
        except IntegrityError:
            return False
        except Exception as exc:
            result.errors.append(f"cluster_macro_create:{type(exc).__name__}")
            return False
        if macro_id is None:
            return False
        result.macros_created += 1
        result.events_emitted += 1
        result.macro_ids.append(macro_id)
        return True

    # Pass A: Durable graph theories with >= 2 existing evidence nodes
    try:
        from store.pg.models_faim import GraphTheoryModel

        theories = (
            session.query(GraphTheoryModel)
            .filter(
                GraphTheoryModel.tenant_id == tenant_id,
                GraphTheoryModel.graph_id == graph_id,
            )
            .order_by(GraphTheoryModel.confidence.desc(), GraphTheoryModel.id.desc())
            .limit(remaining_macros * 3)
            .all()
        )
        for theory in theories:
            if remaining_macros <= 0:
                break
            ev_ids = list(getattr(theory, "evidence_node_ids", None) or [])
            member_ids: List[UUID] = []
            for nid in ev_ids:
                try:
                    parsed = UUID(str(nid))
                except (ValueError, TypeError):
                    continue
                if node_repo.get_by_id(graph_id, parsed) is not None:
                    member_ids.append(parsed)
                if len(member_ids) >= 6:
                    break
            ttype = str(getattr(theory, "theory_type", "theory") or "theory")
            if _try_create(member_ids, f"theory:{ttype}"):
                remaining_macros -= 1
    except Exception:  # nosec B110 - best effort theory synthesis
        pass

    # Pass B: High-connectivity structural clusters from recent edges
    if remaining_macros <= 0:
        return
    try:
        from collections import defaultdict

        from store.pg.models_faim import EdgeModel

        edges = (
            session.query(EdgeModel)
            .filter(
                EdgeModel.tenant_id == tenant_id,
                EdgeModel.graph_id == graph_id,
                EdgeModel.kind.in_(["inheritance", "hypernym", "synonym", "co_occurs"]),
            )
            .order_by(EdgeModel.weight.desc(), EdgeModel.edge_id.asc())
            .limit(300)
            .all()
        )
        adj: Dict[UUID, List[UUID]] = defaultdict(list)
        for e in edges:
            if e.src_node_id != e.dst_node_id:
                adj[e.dst_node_id].append(e.src_node_id)
                adj[e.src_node_id].append(e.dst_node_id)

        ranked_hubs = sorted(adj.items(), key=lambda kv: (-len(set(kv[1])), str(kv[0])))
        for hub_id, neighbors in ranked_hubs:
            if remaining_macros <= 0:
                break
            hub_node = node_repo.get_by_id(graph_id, hub_id)
            if hub_node is None or str(getattr(hub_node, "kind", "")) == "macro":
                continue
            unique_members: List[UUID] = [hub_id]
            for nb in neighbors:
                if (
                    nb not in unique_members
                    and node_repo.get_by_id(graph_id, nb) is not None
                ):
                    unique_members.append(nb)
                if len(unique_members) >= 5:
                    break
            if len(unique_members) >= 3:
                if _try_create(unique_members, "structural_hub"):
                    remaining_macros -= 1
    except Exception:  # nosec B110 - best effort hub cluster synthesis
        pass


def run_synthesis_invention_cycle(
    graph_id: str,
    *,
    session: Any,
    node_repo: NodeRepo,
    edge_repo: EdgeRepo,
    event_repo: Any,
    lambda_hat: float,
    lambda_threshold: float = LAMBDA_THRESHOLD,
    max_macros: int = 3,
    insights: Optional[List[Any]] = None,
) -> InventionResult:
    """Run a bounded cross-galaxy synthesis invention pass on the graph.

    When ``insights`` are provided they are used directly; otherwise the
    graph's galaxies are synthesized on the fly (best effort) and supplemented
    by durable theory/hub clusters up to ``max_macros``.
    """
    errors: List[str] = []
    explicit_insights = insights is not None
    if insights is None:
        insights = _synthesize_for_graph(
            graph_id,
            session=session,
            tenant_id=node_repo.tenant_id,
            errors=errors,
        )
    result = invent_from_synthesis_insights(
        graph_id,
        session=session,
        node_repo=node_repo,
        edge_repo=edge_repo,
        event_repo=event_repo,
        insights=insights,
        lambda_hat=lambda_hat,
        lambda_threshold=lambda_threshold,
        max_macros=max_macros,
    )
    if not explicit_insights and result.macros_created < max_macros:
        _invent_from_theories_and_clusters(
            graph_id=graph_id,
            session=session,
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            lambda_hat=lambda_hat,
            lambda_threshold=lambda_threshold,
            remaining_macros=max(0, int(max_macros) - result.macros_created),
            result=result,
        )
    result.errors.extend(errors)
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
    "invent_from_synthesis_insights",
    "run_synthesis_invention_cycle",
]
