# faim/api/watchers.py
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from faim.api import state as S
from faim.api.events import BUS, emit_fig_delta, emit_metrics
from faim.api.evolution_status import update_status
from faim.config import FaimSettings
from faim.core.evolution import evolve_graph_once

# ======================================================================
# PATHS (stable, correct for systemd + dev)
# ======================================================================
settings = FaimSettings.from_env()

FIG_CACHE = settings.cache_dir / "fig_cache.json"
FIG_CACHE.parent.mkdir(parents=True, exist_ok=True)

DEFAULT_GRAPH = os.getenv("FAIM_DEFAULT_GRAPH", "MAIN")
FIG_WATCH_GRAPH_ID = (os.getenv("FAIM_FIG_WATCH_GRAPH_ID") or "").strip()
METRICS_INTERVAL_SEC = float(os.getenv("FAIM_METRICS_SSE_INTERVAL", "2.5"))
EVOLUTION_INTERVAL_SEC = float(os.getenv("FAIM_EVOLUTION_INTERVAL", "60"))


# ======================================================================
# HELPERS FOR DIFFING NODES + LINKS
# ======================================================================
def _nid(n: Dict[str, Any]) -> str:
    """
    Extract stable node id from the graph-cache node structure.
    Must match the FIG UI.
    """
    return str(n.get("id") or n.get("uid") or n.get("_id") or n.get("label") or "unknown")


def _link_key(link: Dict[str, Any]) -> str:
    """
    Convert a link into a stable comparable key.
    """
    s = link.get("source")
    t = link.get("target")

    if isinstance(s, dict):
        s = s.get("id", s)
    if isinstance(t, dict):
        t = t.get("id", t)

    return f"{s}-{t}"


def _link_endpoints(link: Dict[str, Any]) -> tuple[str, str]:
    s = link.get("source")
    t = link.get("target")

    if isinstance(s, dict):
        s = s.get("id", s)
    if isinstance(t, dict):
        t = t.get("id", t)

    return str(s), str(t)


def compute_diff(prev: Dict[str, Any], cur: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute structural diff:
        added nodes, removed nodes, updated nodes
        added links, removed links, updated links
    """
    # Ensure structure
    prev_nodes = prev.get("nodes", [])
    prev_links = prev.get("links", [])
    cur_nodes = cur.get("nodes", [])
    cur_links = cur.get("links", [])

    # -----------------------
    # NODE DIFF
    # -----------------------
    pn = {_nid(n): n for n in prev_nodes}
    cn = {_nid(n): n for n in cur_nodes}

    add_nodes = []
    upd_nodes = []
    del_nodes = []

    for k, n in cn.items():
        if k not in pn:
            add_nodes.append(n)
        else:
            # check if something changed
            old = pn[k]
            if any(n.get(field) != old.get(field) for field in n.keys()):
                upd_nodes.append(n)

    for k in pn.keys():
        if k not in cn:
            del_nodes.append(k)

    # -----------------------
    # LINK DIFF
    # -----------------------
    pl = {_link_key(link): link for link in prev_links}
    cl = {_link_key(link): link for link in cur_links}

    add_links: list[dict] = []
    del_links: list[dict] = []
    upd_links: list[dict] = []

    for key, link in cl.items():
        if key not in pl:
            add_links.append(link)
        else:
            old = pl[key]
            if any(link.get(field) != old.get(field) for field in link.keys()):
                upd_links.append(link)

    for key, link in pl.items():
        if key not in cl:
            del_links.append(link)

    return {
        "add_nodes": add_nodes,
        "upd_nodes": upd_nodes,
        "del_nodes": del_nodes,
        "add_links": add_links,
        "upd_links": upd_links,
        "del_links": del_links,
    }


# ======================================================================
# WATCH LOOP (runs forever, checks FIG cache)
# ======================================================================
async def _watch_fig(graph_id: Optional[str], path: Path, interval: float = 0.5) -> None:
    """
    Watches fig_cache.json file for changes and emits diffs via SSE.
    Runs as a non-blocking asyncio task.
    """
    last_mtime = 0.0
    previous_state: Dict[str, Any] = {"nodes": [], "links": []}

    path.parent.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            if path.exists():
                mtime = path.stat().st_mtime
                if mtime != last_mtime:
                    last_mtime = mtime
                    text = path.read_text(encoding="utf-8") or "{}"

                    try:
                        current_state = json.loads(text)
                    except json.JSONDecodeError:
                        current_state = {"nodes": [], "links": []}

                    current_state.setdefault("nodes", [])
                    current_state.setdefault("links", [])

                    diff = compute_diff(previous_state, current_state)

                    previous_state = current_state

                    delta = {
                        "nodes_added": [{"id": _nid(n)} for n in diff.get("add_nodes", [])],
                        "nodes_removed": [{"id": str(n)} for n in diff.get("del_nodes", [])],
                        "links_added": [
                            {"source": s, "target": t}
                            for s, t in (_link_endpoints(l) for l in diff.get("add_links", []))
                        ],
                        "links_removed": [
                            {"source": s, "target": t}
                            for s, t in (_link_endpoints(l) for l in diff.get("del_links", []))
                        ],
                    }

                    targets = [graph_id] if graph_id else []
                    if not targets:
                        try:
                            targets = await BUS.active_graph_ids()
                        except Exception:
                            targets = []
                    if not targets and DEFAULT_GRAPH:
                        targets = [DEFAULT_GRAPH]

                    for gid in targets:
                        await emit_fig_delta(gid, delta)

        except Exception as e:
            # Do not stop watcher — just log and continue
            print(f"[FAIM Watcher] Error: {e}")

        await asyncio.sleep(interval)


async def _watch_metrics(interval: float = 2.5) -> None:
    while True:
        try:
            graph_ids = await BUS.active_graph_ids()
            if not graph_ids:
                await asyncio.sleep(interval)
                continue

            try:
                from faim.engine.interface import get_metrics as _engine_get_metrics  # type: ignore
            except Exception:
                _engine_get_metrics = None

            if _engine_get_metrics is not None:
                for gid in graph_ids:
                    try:
                        cards = _engine_get_metrics(gid) or {}
                        await emit_metrics(gid, cards)
                    except Exception:
                        continue
        except Exception as e:
            print(f"[FAIM Watcher] metrics_error: {e}")

        await asyncio.sleep(interval)


def _evolution_enabled() -> bool:
    return os.getenv("FAIM_EVOLUTION_SCHEDULER", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "y",
        "on",
    )


def _evolution_log_path() -> Path:
    p = settings.root / "Runtime" / "Logs" / "evolution.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _log_evolution(line: str) -> None:
    try:
        _evolution_log_path().open("a", encoding="utf-8").write(line + "\n")
    except Exception:
        pass


async def _watch_evolution(interval: float = 60.0) -> None:
    while True:
        if not _evolution_enabled():
            await asyncio.sleep(max(5.0, interval))
            continue
        try:
            graph_ids = await BUS.active_graph_ids()
            if not graph_ids:
                await asyncio.sleep(interval)
                continue
            for gid in graph_ids:
                started = time.time()
                try:
                    stats = evolve_graph_once(S.NODE_STORE, S._gid(gid))
                    duration_ms = (time.time() - started) * 1000.0
                    update_status(
                        gid,
                        stats=stats.__dict__,
                        duration_ms=duration_ms,
                        error=None,
                    )
                    _log_evolution(
                        f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} "
                        f"graph_id={gid} merges={stats.merges} prunes={stats.prunes} "
                        f"promotions={stats.promotions} duration_ms={duration_ms:.1f}"
                    )
                except Exception as exc:
                    duration_ms = (time.time() - started) * 1000.0
                    update_status(gid, stats=None, duration_ms=duration_ms, error=str(exc))
                    _log_evolution(
                        f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} "
                        f"graph_id={gid} error={type(exc).__name__}: {exc}"
                    )
        except Exception as e:
            _log_evolution(
                f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} "
                f"evolution_scheduler_error={type(e).__name__}: {e}"
            )
        await asyncio.sleep(interval)


# ======================================================================
# START WATCHERS (called from app.py startup event)
# ======================================================================
def start_watchers(loop: asyncio.AbstractEventLoop):
    """
    Launches background watcher task.
    Keeps FIG 3D UI always in sync.
    """
    fig_graph_id = FIG_WATCH_GRAPH_ID or None
    loop.create_task(_watch_fig(fig_graph_id, FIG_CACHE))
    loop.create_task(_watch_metrics(max(1.0, METRICS_INTERVAL_SEC)))
    loop.create_task(_watch_evolution(max(10.0, EVOLUTION_INTERVAL_SEC)))
    label = fig_graph_id or "active_graphs"
    print(f"[FAIM] FIG watcher started for graph '{label}' at {FIG_CACHE}")
