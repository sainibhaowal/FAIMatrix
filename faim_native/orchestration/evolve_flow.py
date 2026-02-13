"""FAIM-Native Orchestration: Evolve Flow.

Pure wiring layer for evolution operations.

Calls core.dynamics.evolution_native.evolve_once() and returns
MetricsSnapshot in Stage-4.1.1 contract format.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from .ingest_flow import FAIMProfile, PersistMode

logger = logging.getLogger(__name__)


# =============================================================================
# Types
# =============================================================================


@dataclass(frozen=True)
class EvolveResult:
    """Result returned by run_evolve.

    Attributes:
        status: "completed" or "error"
        graph_version: Graph version after evolution
        merges: Number of merge operations
        prunes: Number of prune operations
        inventions: Number of self-invention macro creations
        diagnostics: MetricsSnapshot in Stage-4.1.1 format
        events_emitted: List of event types emitted
        latency_ms: Total latency in milliseconds
        error: Error message if status is "error"
    """

    status: str
    graph_version: int
    merges: int
    prunes: int
    inventions: int
    diagnostics: Optional[Dict[str, Any]]  # MetricsSnapshot.to_dict()
    events_emitted: List[str]
    latency_ms: int
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for API response."""
        return {
            "status": self.status,
            "graph_version": self.graph_version,
            "merges": self.merges,
            "prunes": self.prunes,
            "inventions": self.inventions,
            "diagnostics": self.diagnostics,
            "events_emitted": self.events_emitted,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


# =============================================================================
# Event Emission
# =============================================================================


def _emit_event(
    event_type: str,
    graph_id: str,
    payload: Dict[str, Any],
    event_repo: Optional[Any] = None,
    session: Optional[Any] = None,
) -> None:
    """Emit event for UI/API consumption."""
    datetime.now(timezone.utc).isoformat()

    logger.info(f"[Event] {event_type}: {payload}")

    if event_repo is not None and session is not None:
        try:
            event_repo.emit(session, graph_id, event_type, payload)
        except Exception as e:
            logger.warning(f"Failed to persist event: {e}")


# =============================================================================
# Main Evolve Function
# =============================================================================


def run_evolve(
    graph_id: str,
    *,
    tenant_id: str = "default",
    session: Optional[Session] = None,
    profile: Union[FAIMProfile, str] = FAIMProfile.STRICT,
    persist_mode: Union[PersistMode, str] = PersistMode.RELAXED,
    node_repo: Optional[Any] = None,
    edge_repo: Optional[Any] = None,
    event_repo: Optional[Any] = None,
    gv_repo: Optional[Any] = None,
) -> EvolveResult:
    """Run one evolution cycle on graph.

    This calls core.dynamics.evolution_native.evolve_once() which:
    1. Computes fractal diagnostics (D/H/λ)
    2. Emits DIAGNOSTICS_SNAPSHOT event
    3. Performs merge operations (based on redundancy)
    4. Performs prune operations (based on policy)
    5. Emits EVOLUTION_COMPLETE event

    Uses lock manager to prevent concurrent evolution on the same graph.

    Args:
        graph_id: Target graph identifier.
        profile: STRICT (deterministic) or FAST (may use approximations).
        persist_mode: STRICT (wait for commit) or RELAXED (async).
        node_repo: Node repository.
        edge_repo: Edge repository.
        event_repo: Event repository.
        gv_repo: Graph version repository.

    Returns:
        EvolveResult with diagnostics in MetricsSnapshot format.
    """
    start_time = time.time()
    events_emitted: List[str] = []

    # Normalize profile
    if isinstance(profile, str):
        profile = FAIMProfile(profile.lower())
    if isinstance(persist_mode, str):
        persist_mode = PersistMode(persist_mode.lower())

    logger.info(f"[Evolve] Starting: graph={graph_id}, profile={profile.value}")
    # =========================================================================
    # Initialize repositories if not provided
    # =========================================================================
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.graph_version_repo import GraphVersionRepo
    from store.pg.repos.node_repo import NodeRepo
    from store.pg.session import get_session

    # If session is provided, we use it (typical for worker or transaction-wrapped calls)
    # If not, we open a new one
    own_session = False
    if session is None:
        # Reuse an existing repo-backed session when caller provided repos.
        session = (
            getattr(node_repo, "session", None)
            or getattr(edge_repo, "session", None)
            or getattr(event_repo, "session", None)
            or getattr(gv_repo, "session", None)
        )
        if session is None:
            session = get_session()
            own_session = True

    try:
        if node_repo is None:
            node_repo = NodeRepo(session, tenant_id=tenant_id)
        if edge_repo is None:
            edge_repo = EdgeRepo(session, tenant_id=tenant_id)
        if event_repo is None:
            event_repo = EventRepo(session, tenant_id=tenant_id)
        if gv_repo is None:
            gv_repo = GraphVersionRepo(session, tenant_id=tenant_id)

        # Acquire lock to prevent concurrent evolution on same graph
        from cache.locks import evolve_lock

        with evolve_lock(graph_id) as lock_acquired:
            if not lock_acquired:
                logger.warning(f"[Evolve] Could not acquire lock for graph {graph_id}")
                return EvolveResult(
                    status="error",
                    graph_version=0,
                    merges=0,
                    prunes=0,
                    inventions=0,
                    diagnostics=None,
                    events_emitted=[],
                    latency_ms=int((time.time() - start_time) * 1000),
                    error="Could not acquire evolution lock (another evolution in progress)",
                )

            try:
                # =====================================================================
                # STEP 0: Emit EVOLUTION_START
                # =====================================================================
                _emit_event(
                    "EVOLUTION_START",
                    graph_id,
                    {
                        "profile": profile.value,
                        "persist_mode": persist_mode.value,
                        "tenant_id": tenant_id,
                    },
                    event_repo,
                    session=session,
                )
                events_emitted.append("EVOLUTION_START")

                # =====================================================================
                # STEP 1: Call evolution_native.evolve_once
                # =====================================================================
                from core.dynamics.evolution_native import evolve_once

                result = evolve_once(
                    graph_id=graph_id,
                    node_repo=node_repo,
                    edge_repo=edge_repo,
                    event_repo=event_repo,
                    graph_version_repo=gv_repo,
                )

                # evolve_once already emits DIAGNOSTICS_SNAPSHOT and EVOLUTION_COMPLETE
                events_emitted.append("DIAGNOSTICS_SNAPSHOT")
                events_emitted.append("EVOLUTION_COMPLETE")

                logger.info(
                    f"[Evolve] Complete: {result.merges} merges, "
                    f"{result.prunes} prunes, version={result.graph_version}"
                )

                # =====================================================================
                # STEP 2: Convert diagnostics to MetricsSnapshot format
                # =====================================================================
                diagnostics_dict = None

                if result.diagnostics is not None:
                    try:
                        # Get graph hash for MetricsSnapshot
                        graph_hash = ""
                        if gv_repo is not None:
                            try:
                                gv = gv_repo.get(None, graph_id)
                                graph_hash = getattr(gv, "graph_hash", "")
                            except Exception:  # nosec B110 - graceful fallback
                                pass

                        # Convert FractalDiagnostics to MetricsSnapshot
                        snapshot = result.diagnostics.to_metrics_snapshot(graph_hash)
                        diagnostics_dict = snapshot.to_dict()
                    except Exception as e:
                        logger.warning(f"Failed to convert diagnostics: {e}")

                # Commit if we own the session
                if own_session:
                    session.commit()

                # =====================================================================
                # STEP 3: Build result
                # =====================================================================
                latency_ms = int((time.time() - start_time) * 1000)

                return EvolveResult(
                    status="completed",
                    graph_version=result.graph_version,
                    merges=result.merges,
                    prunes=result.prunes,
                    inventions=result.inventions,
                    diagnostics=diagnostics_dict,
                    events_emitted=events_emitted,
                    latency_ms=latency_ms,
                )

            except Exception as e:
                if own_session:
                    session.rollback()
                logger.error(f"[Evolve] Error: {e}")
                latency_ms = int((time.time() - start_time) * 1000)

                _emit_event(
                    "EVOLUTION_ERROR",
                    graph_id,
                    {
                        "error": str(e),
                    },
                    event_repo,
                )
                events_emitted.append("EVOLUTION_ERROR")

                return EvolveResult(
                    status="error",
                    graph_version=0,
                    merges=0,
                    prunes=0,
                    inventions=0,
                    diagnostics=None,
                    events_emitted=events_emitted,
                    latency_ms=latency_ms,
                    error=str(e),
                )
    finally:
        if own_session:
            session.close()


# =============================================================================
# Batch Evolution
# =============================================================================


def run_evolve_batch(
    graph_id: str,
    cycles: int = 1,
    *,
    profile: Union[FAIMProfile, str] = FAIMProfile.STRICT,
    persist_mode: Union[PersistMode, str] = PersistMode.RELAXED,
    node_repo: Optional[Any] = None,
    edge_repo: Optional[Any] = None,
    event_repo: Optional[Any] = None,
    gv_repo: Optional[Any] = None,
) -> List[EvolveResult]:
    """Run multiple evolution cycles.

    Args:
        graph_id: Target graph identifier.
        cycles: Number of evolution cycles to run.
        profile: Execution profile.
        persist_mode: Durability mode.
        node_repo, edge_repo, event_repo, gv_repo: Repositories.

    Returns:
        List of EvolveResult, one per cycle.
    """
    results = []

    for i in range(cycles):
        logger.info(f"[Evolve] Cycle {i + 1}/{cycles}")
        result = run_evolve(
            graph_id=graph_id,
            profile=profile,
            persist_mode=persist_mode,
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            gv_repo=gv_repo,
        )
        results.append(result)

        if result.status == "error":
            logger.warning(f"[Evolve] Stopping after error in cycle {i + 1}")
            break

    return results


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "EvolveResult",
    "run_evolve",
    "run_evolve_batch",
]
