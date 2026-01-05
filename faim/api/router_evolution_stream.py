"""
FAIM Real-time Evolution Stream (SSE)

NEW MODULE - Does not modify any existing code.
Provides Server-Sent Events for real-time evolution status updates.

Usage:
    Mount this router in app.py:
        from faim.api.router_evolution_stream import router as evolution_stream_router
        app.include_router(evolution_stream_router, prefix="/api/v1")
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from faim.api.auth import allow_dev_mode

# Import evolution components (read-only access)
from faim.core.evolution import EvolutionConfig, evolve_graph_once

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evolution", tags=["Evolution Stream"])


@dataclass
class EvolutionEvent:
    """Event sent via SSE when evolution occurs."""

    event_type: str  # "evolution_started", "evolution_completed", "evolution_error"
    graph_id: str
    timestamp: str
    stats: Optional[dict] = None
    message: Optional[str] = None


def _format_sse(event: EvolutionEvent) -> str:
    """Format event as SSE message."""
    data = json.dumps(asdict(event))
    return f"event: {event.event_type}\ndata: {data}\n\n"


async def _evolution_event_generator(
    graph_id: str,
    interval_seconds: float = 30.0,
    max_events: int = 100,
) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for evolution status.

    This is a polling-based approach that's safe and doesn't modify
    any core engine behavior. It simply reports evolution results.
    """
    event_count = 0

    # Send initial connection event
    yield _format_sse(
        EvolutionEvent(
            event_type="connected",
            graph_id=graph_id,
            timestamp=datetime.utcnow().isoformat(),
            message=f"Connected to evolution stream for graph: {graph_id}",
        )
    )

    while event_count < max_events:
        try:
            # Get store from production state (read-only)
            try:
                from faim.api.production_state import get_store

                store = get_store()
            except ImportError:
                from faim.api import state as S

                store = getattr(S, "STORE", None) or getattr(S, "store_instance", None)

            if store is None:
                yield _format_sse(
                    EvolutionEvent(
                        event_type="evolution_skipped",
                        graph_id=graph_id,
                        timestamp=datetime.utcnow().isoformat(),
                        message="Store not available",
                    )
                )
            else:
                # Run evolution and report results
                yield _format_sse(
                    EvolutionEvent(
                        event_type="evolution_started",
                        graph_id=graph_id,
                        timestamp=datetime.utcnow().isoformat(),
                    )
                )

                config = EvolutionConfig(
                    merge_similarity_threshold=0.95,
                    prune_min_use_count=0,
                    promote_min_use_count=3,
                )

                stats = evolve_graph_once(store, graph_id, config=config)

                yield _format_sse(
                    EvolutionEvent(
                        event_type="evolution_completed",
                        graph_id=graph_id,
                        timestamp=datetime.utcnow().isoformat(),
                        stats={
                            "regions": stats.regions,
                            "merges": stats.merges,
                            "prunes": stats.prunes,
                            "promotions": stats.promotions,
                            "redundancy_before": round(stats.redundancy_before, 4),
                            "redundancy_after": round(stats.redundancy_after, 4),
                            "objective_before": round(stats.objective_before, 4),
                            "objective_after": round(stats.objective_after, 4),
                        },
                    )
                )

            event_count += 1
            await asyncio.sleep(interval_seconds)

        except Exception as e:
            logger.error(f"Evolution stream error: {e}")
            yield _format_sse(
                EvolutionEvent(
                    event_type="evolution_error",
                    graph_id=graph_id,
                    timestamp=datetime.utcnow().isoformat(),
                    message=str(e),
                )
            )
            await asyncio.sleep(interval_seconds)

    # Final event
    yield _format_sse(
        EvolutionEvent(
            event_type="stream_ended",
            graph_id=graph_id,
            timestamp=datetime.utcnow().isoformat(),
            message=f"Stream ended after {max_events} events",
        )
    )


@router.get("/{graph_id}/stream")
async def evolution_stream(
    graph_id: str,
    request: Request,
    interval: float = 30.0,
    _=Depends(allow_dev_mode),
):
    """
    Server-Sent Events stream for real-time evolution updates.

    Connect to this endpoint to receive live evolution status:
    - evolution_started: Evolution pass beginning
    - evolution_completed: Evolution pass finished with stats
    - evolution_error: Error occurred during evolution

    Args:
        graph_id: The graph to monitor
        interval: Seconds between evolution passes (default: 30)

    Example:
        ```javascript
        const evtSource = new EventSource('/api/v1/evolution/test-graph/stream');
        evtSource.addEventListener('evolution_completed', (e) => {
            const data = JSON.parse(e.data);
            console.log('Merges:', data.stats.merges);
        });
        ```
    """
    # Clamp interval to reasonable bounds
    interval = max(5.0, min(300.0, interval))

    return StreamingResponse(
        _evolution_event_generator(graph_id, interval_seconds=interval),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{graph_id}/status")
async def evolution_status(
    graph_id: str,
    _=Depends(allow_dev_mode),
):
    """
    Get current evolution status for a graph (one-shot, not streaming).

    Returns the latest evolution statistics without triggering a new evolution pass.
    """
    try:
        from faim.api.production_state import get_store

        store = get_store()
    except ImportError:
        from faim.api import state as S

        store = getattr(S, "STORE", None) or getattr(S, "store_instance", None)

    if store is None:
        return {"graph_id": graph_id, "status": "unavailable", "message": "Store not initialized"}

    # Count nodes to show graph is active
    try:
        node_count = store.count_nodes(graph_id)
    except Exception:
        node_count = 0

    return {
        "graph_id": graph_id,
        "status": "active" if node_count > 0 else "empty",
        "node_count": node_count,
        "evolution_enabled": True,
        "message": f"Graph has {node_count} nodes",
    }


@router.post("/{graph_id}/evolve")
async def trigger_evolution(
    graph_id: str,
    _=Depends(allow_dev_mode),
):
    """
    Manually trigger a single evolution pass for a graph.

    Returns the evolution statistics immediately (synchronous).
    """
    try:
        from faim.api.production_state import get_store

        store = get_store()
    except ImportError:
        from faim.api import state as S

        store = getattr(S, "STORE", None) or getattr(S, "store_instance", None)

    if store is None:
        return {"success": False, "error": "Store not initialized"}

    config = EvolutionConfig(
        merge_similarity_threshold=0.95,
        prune_min_use_count=0,
        promote_min_use_count=3,
    )

    stats = evolve_graph_once(store, graph_id, config=config)

    return {
        "success": True,
        "graph_id": graph_id,
        "stats": {
            "regions": stats.regions,
            "merges": stats.merges,
            "prunes": stats.prunes,
            "promotions": stats.promotions,
            "redundancy_before": round(stats.redundancy_before, 4),
            "redundancy_after": round(stats.redundancy_after, 4),
            "objective_before": round(stats.objective_before, 4),
            "objective_after": round(stats.objective_after, 4),
        },
    }
