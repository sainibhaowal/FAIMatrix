from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class EvolutionStatus:
    graph_id: str
    last_run_ts: Optional[float] = None
    last_duration_ms: Optional[float] = None
    last_error: Optional[str] = None
    runs: int = 0
    last_stats: Optional[Dict[str, Any]] = None


_lock = threading.Lock()
_status: Dict[str, EvolutionStatus] = {}


def update_status(
    graph_id: str,
    *,
    stats: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[float] = None,
    error: Optional[str] = None,
) -> EvolutionStatus:
    with _lock:
        cur = _status.get(graph_id) or EvolutionStatus(graph_id=graph_id)
        cur.last_run_ts = time.time()
        cur.last_duration_ms = duration_ms
        cur.last_error = error
        cur.runs = int(cur.runs) + 1
        cur.last_stats = stats
        _status[graph_id] = cur
        return cur


def get_status(graph_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        cur = _status.get(graph_id)
        return asdict(cur) if cur else None


def get_all_status() -> Dict[str, Dict[str, Any]]:
    with _lock:
        return {gid: asdict(st) for gid, st in _status.items()}
