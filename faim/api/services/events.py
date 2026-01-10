# =============================================================================
# FAIM — GOLD EDITION (COMMERCIAL / PRODUCTION)
# =============================================================================
# File: faim/api/events.py
#
# Guarantees:
#   - SSE is RFC compliant and ALWAYS JSON in data: line (single-encoded)
#   - Per-graph broadcast channels (Universe graph per user)
#   - keepalive ping every N seconds (event: ping)
#   - bounded per-subscriber queues (drop-oldest) => no memory leaks
#   - reconnect safety via monotonic id + bounded replay ring
#   - STRICT EVENT SCHEMAS for production UI wiring:
#       fig_delta, chat_token, chat_used, chat_store, metrics, toast, error
#
# Step-3 enforcement:
#   - ANY publish() of a product event is schema-validated
#   - Schema violation => emits structured 'error' event (never leaks broken payload)
# =============================================================================

from __future__ import annotations

import asyncio
import json
import math
import time
from collections import deque
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Deque, Optional, TypeAlias

# =============================================================================
# HARD LIMITS (DOS-SAFE)
# =============================================================================
DEFAULT_KEEPALIVE_SECONDS = 15
DEFAULT_SUBSCRIBER_QUEUE_MAX = 256
DEFAULT_REPLAY_MAX = 4096
MAX_EVENT_BYTES = 256_000

# event-level sanity limits
MAX_USED_NODES = 64
MAX_TOKEN_LEN = 4096
MAX_MESSAGE_LEN = 8000
MAX_IDS = 512

DisconnectFn: TypeAlias = Callable[[], Awaitable[bool]]

# Product events allowed to pass validation.
ALLOWED_EVENTS: set[str] = {
    "fig_delta",
    "chat_token",
    "chat_used",
    "chat_store",
    "metrics",
    "toast",
    "error",
    "evolution",
    "invention",
    "cluster_updated",
    "inference_found",
    "insight_discovered",
}
# Internal stream-only events that may bypass validation.
INTERNAL_EVENTS: set[str] = {"ping", "contract", "gap"}


# =============================================================================
# SSE EVENT MODEL
# =============================================================================
@dataclass(frozen=True)
class SseEvent:
    event: str
    data: dict[str, Any]
    id: Optional[int] = None
    retry_ms: Optional[int] = None


def _json_dumps(obj: Any) -> str:
    return json.dumps(
        obj,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def format_sse(ev: SseEvent) -> bytes:
    payload = ev.data if isinstance(ev.data, dict) else {"value": ev.data}
    data_line = _json_dumps(payload)

    lines: list[str] = []
    if ev.id is not None:
        lines.append(f"id: {ev.id}")
    if ev.event:
        lines.append(f"event: {ev.event}")
    if ev.retry_ms is not None:
        lines.append(f"retry: {int(ev.retry_ms)}")

    # STRICT: JSON once only
    lines.append(f"data: {data_line}")
    lines.append("")  # end event

    chunk = ("\n".join(lines) + "\n").encode("utf-8", errors="strict")
    if len(chunk) > MAX_EVENT_BYTES:
        err = SseEvent(
            event="error",
            data={
                "graph_id": payload.get("graph_id", ""),
                "ts": time.time(),
                "type": "sse_payload_too_large",
                "message": "SSE event exceeded MAX_EVENT_BYTES",
                "details": {"bytes": len(chunk), "max_bytes": MAX_EVENT_BYTES},
            },
            id=ev.id,
        )
        return (
            "\n".join(
                [
                    f"id: {err.id}" if err.id is not None else "",
                    "event: error",
                    f"data: {_json_dumps(err.data)}",
                    "",
                    "",
                ]
            )
        ).encode("utf-8", errors="strict")
    return chunk


# =============================================================================
# STEP 3 — STRICT EVENT SCHEMAS (RUNTIME VALIDATION)
# =============================================================================
def _is_str(x: Any) -> bool:
    return isinstance(x, str)


def _is_int(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _is_bool(x: Any) -> bool:
    return isinstance(x, bool)


def _is_dict(x: Any) -> bool:
    return isinstance(x, dict)


def _is_list(x: Any) -> bool:
    return isinstance(x, list)


def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _is_finite_num(x: Any) -> bool:
    if not _is_num(x):
        return False
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def _require_keys(obj: dict[str, Any], required: set[str]) -> None:
    missing = required.difference(obj.keys())
    if missing:
        raise ValueError(f"missing keys: {sorted(missing)}")


def _forbid_extra(obj: dict[str, Any], allowed: set[str]) -> None:
    extra = set(obj.keys()).difference(allowed)
    if extra:
        raise ValueError(f"extra keys not allowed: {sorted(extra)}")


def _validate_chat_used_node(n: dict[str, Any]) -> None:
    """
    COMMERCIAL CONTRACT:
      used_nodes item MUST have:
        id:str, label:str, payload:str, degree:int, score:number (finite, never null)
      Optional: kind:str, why:str, galaxy:str
    """
    allowed = {"id", "label", "payload", "degree", "score", "kind", "why", "galaxy"}
    _require_keys(n, {"id", "label", "payload", "degree", "score"})
    _forbid_extra(n, allowed)

    if not _is_str(n["id"]) or not n["id"]:
        raise ValueError("chat_used.used_nodes[].id must be non-empty str")
    if not _is_str(n["label"]):
        raise ValueError("chat_used.used_nodes[].label must be str")
    if not _is_str(n["payload"]):
        raise ValueError("chat_used.used_nodes[].payload must be str")
    if not _is_int(n["degree"]):
        raise ValueError("chat_used.used_nodes[].degree must be int")
    # IMPORTANT: score cannot be None/null
    if not _is_finite_num(n["score"]):
        raise ValueError("chat_used.used_nodes[].score must be finite number (never null)")

    if "kind" in n and not _is_str(n["kind"]):
        raise ValueError("chat_used.used_nodes[].kind must be str")
    if "why" in n and not _is_str(n["why"]):
        raise ValueError("chat_used.used_nodes[].why must be str")
    if "galaxy" in n and not _is_str(n["galaxy"]):
        raise ValueError("chat_used.used_nodes[].galaxy must be str")


def validate_event(event: str, data: dict[str, Any]) -> None:
    """
    Strict schema validation (production).
    If this throws, publish() will emit a structured 'error' instead.
    """
    if not _is_dict(data):
        raise ValueError("data must be object/dict")

    if event not in ALLOWED_EVENTS and event not in INTERNAL_EVENTS:
        raise ValueError(f"unknown event type: {event}")

    if event == "fig_delta":
        allowed = {"graph_id", "ts", "delta"}
        _require_keys(data, {"graph_id", "ts", "delta"})
        _forbid_extra(data, allowed)
        if not _is_str(data["graph_id"]):
            raise ValueError("graph_id must be str")
        if not _is_finite_num(data["ts"]):
            raise ValueError("ts must be finite number")
        if not _is_dict(data["delta"]):
            raise ValueError("delta must be object")

    elif event == "chat_token":
        allowed = {"graph_id", "trace_id", "turn_id", "role", "token", "index", "done", "ts"}
        _require_keys(data, {"graph_id", "trace_id", "turn_id", "role", "token", "index", "ts"})
        _forbid_extra(data, allowed)
        if not _is_str(data["graph_id"]):
            raise ValueError("graph_id must be str")
        if not _is_str(data["trace_id"]):
            raise ValueError("trace_id must be str")
        if not _is_str(data["turn_id"]):
            raise ValueError("turn_id must be str")
        if data["role"] not in ("assistant", "system"):
            raise ValueError("role must be 'assistant'|'system'")
        if not _is_str(data["token"]):
            raise ValueError("token must be str")
        if len(data["token"]) > MAX_TOKEN_LEN:
            raise ValueError("token too long")
        if not _is_int(data["index"]):
            raise ValueError("index must be int")
        if "done" in data and not _is_bool(data["done"]):
            raise ValueError("done must be bool")
        if not _is_finite_num(data["ts"]):
            raise ValueError("ts must be finite number")

    elif event == "chat_used":
        allowed = {"graph_id", "trace_id", "turn_id", "used_nodes", "ts"}
        _require_keys(data, {"graph_id", "trace_id", "turn_id", "used_nodes", "ts"})
        _forbid_extra(data, allowed)
        if not _is_str(data["graph_id"]):
            raise ValueError("graph_id must be str")
        if not _is_str(data["trace_id"]):
            raise ValueError("trace_id must be str")
        if not _is_str(data["turn_id"]):
            raise ValueError("turn_id must be str")
        if not _is_list(data["used_nodes"]):
            raise ValueError("used_nodes must be list")
        if len(data["used_nodes"]) > MAX_USED_NODES:
            raise ValueError("used_nodes too large")
        for n in data["used_nodes"]:
            if not _is_dict(n):
                raise ValueError("each used_node must be object")
            _validate_chat_used_node(n)
        if not _is_finite_num(data["ts"]):
            raise ValueError("ts must be finite number")

    elif event == "chat_store":
        allowed = {
            "graph_id",
            "trace_id",
            "turn_id",
            "created_node_ids",
            "created_fact_ids",
            "summary",
            "ts",
        }
        _require_keys(
            data,
            {
                "graph_id",
                "trace_id",
                "turn_id",
                "created_node_ids",
                "created_fact_ids",
                "summary",
                "ts",
            },
        )
        _forbid_extra(data, allowed)
        if not _is_str(data["graph_id"]):
            raise ValueError("graph_id must be str")
        if not _is_str(data["trace_id"]):
            raise ValueError("trace_id must be str")
        if not _is_str(data["turn_id"]):
            raise ValueError("turn_id must be str")
        if not _is_list(data["created_node_ids"]):
            raise ValueError("created_node_ids must be list")
        if not _is_list(data["created_fact_ids"]):
            raise ValueError("created_fact_ids must be list")
        if len(data["created_node_ids"]) > MAX_IDS or len(data["created_fact_ids"]) > MAX_IDS:
            raise ValueError("too many created ids")
        if not all(_is_str(x) for x in data["created_node_ids"]):
            raise ValueError("created_node_ids must be list[str]")
        if not all(_is_str(x) for x in data["created_fact_ids"]):
            raise ValueError("created_fact_ids must be list[str]")
        if not _is_str(data["summary"]) or len(data["summary"]) > MAX_MESSAGE_LEN:
            raise ValueError("summary must be str (bounded)")
        if not _is_finite_num(data["ts"]):
            raise ValueError("ts must be finite number")

    elif event == "metrics":
        allowed = {"graph_id", "ts", "cards"}
        _require_keys(data, {"graph_id", "ts", "cards"})
        _forbid_extra(data, allowed)
        if not _is_str(data["graph_id"]):
            raise ValueError("graph_id must be str")
        if not _is_finite_num(data["ts"]):
            raise ValueError("ts must be finite number")
        if not _is_dict(data["cards"]):
            raise ValueError("cards must be object")

    elif event == "toast":
        allowed = {"graph_id", "ts", "level", "message", "code"}
        _require_keys(data, {"graph_id", "ts", "level", "message"})
        _forbid_extra(data, allowed)
        if not _is_str(data["graph_id"]):
            raise ValueError("graph_id must be str")
        if not _is_finite_num(data["ts"]):
            raise ValueError("ts must be finite number")
        if data["level"] not in ("info", "success", "warning", "error"):
            raise ValueError("level invalid")
        if not _is_str(data["message"]) or len(data["message"]) > MAX_MESSAGE_LEN:
            raise ValueError("message must be str (bounded)")
        if "code" in data and not _is_str(data["code"]):
            raise ValueError("code must be str")

    elif event == "error":
        allowed = {"graph_id", "ts", "type", "message", "trace_id", "turn_id", "details"}
        _require_keys(data, {"graph_id", "ts", "type", "message"})
        _forbid_extra(data, allowed)
        if not _is_str(data["graph_id"]):
            raise ValueError("graph_id must be str")
        if not _is_finite_num(data["ts"]):
            raise ValueError("ts must be finite number")
        if not _is_str(data["type"]):
            raise ValueError("type must be str")
        if not _is_str(data["message"]) or len(data["message"]) > MAX_MESSAGE_LEN:
            raise ValueError("message must be str (bounded)")
        if "trace_id" in data and not _is_str(data["trace_id"]):
            raise ValueError("trace_id must be str")
        if "turn_id" in data and not _is_str(data["turn_id"]):
            raise ValueError("turn_id must be str")
        if "details" in data and not _is_dict(data["details"]):
            raise ValueError("details must be object")

    elif event == "evolution":
        allowed = {"graph_id", "ts", "type", "data"}
        _require_keys(data, {"graph_id", "ts", "type", "data"})
        # _forbid_extra(data, allowed) # Optional: allow extra
        if not _is_str(data["graph_id"]):
            raise ValueError("graph_id must be str")
        if not _is_str(data["type"]):
            raise ValueError("type must be str")
        if not _is_dict(data["data"]):
            raise ValueError("data must be dict")

    elif event == "invention":
        allowed = {"graph_id", "ts", "type", "data"}
        _require_keys(data, {"graph_id", "ts", "type", "data"})
        if not _is_str(data["graph_id"]):
            raise ValueError("graph_id must be str")
        if not _is_str(data["type"]):
            raise ValueError("type must be str")
        if not _is_dict(data["data"]):
            raise ValueError("data must be dict")

    # INTERNAL events validation is intentionally minimal.
    elif event in INTERNAL_EVENTS:
        return


def _schema_error_payload(graph_id: str, event: str, exc: Exception) -> dict[str, Any]:
    return {
        "graph_id": graph_id,
        "ts": time.time(),
        "type": "event_schema_violation",
        "message": f"{event}: {exc}",
        "details": {"event": event},
    }


# =============================================================================
# GRAPH CHANNEL (per graph_id) — RAW BYTES BROADCAST
# =============================================================================
class GraphChannel:
    def __init__(
        self,
        graph_id: str,
        *,
        subscriber_queue_max: int = DEFAULT_SUBSCRIBER_QUEUE_MAX,
        replay_max: int = DEFAULT_REPLAY_MAX,
    ) -> None:
        self.graph_id = graph_id
        self._subscriber_queue_max = max(8, int(subscriber_queue_max))
        self._replay_max = max(0, int(replay_max))

        self._lock = asyncio.Lock()
        self._subscribers: set[asyncio.Queue[bytes]] = set()

        self._next_id = 1
        self._replay: Deque[tuple[int, bytes]] = deque(maxlen=self._replay_max)

        self.published_total = 0
        self.dropped_messages_total = 0

    def _alloc_id(self) -> int:
        eid = self._next_id
        self._next_id += 1
        return eid

    async def publish_raw(self, event: str, data: dict[str, Any]) -> int:
        """
        RAW publish — does NOT validate. (Validation is enforced by EventBus.publish.)
        """
        async with self._lock:
            eid = self._alloc_id()
            chunk = format_sse(SseEvent(event=event, data=data, id=eid))

            if self._replay_max > 0:
                self._replay.append((eid, chunk))

            self.published_total += 1

            for q in list(self._subscribers):
                if q.full():
                    try:
                        _ = q.get_nowait()  # drop oldest
                        self.dropped_messages_total += 1
                    except asyncio.QueueEmpty:
                        pass
                try:
                    q.put_nowait(chunk)
                except asyncio.QueueFull:
                    self.dropped_messages_total += 1

            return eid

    async def _subscribe_queue(self) -> asyncio.Queue[bytes]:
        q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=self._subscriber_queue_max)
        async with self._lock:
            self._subscribers.add(q)
        return q

    async def _unsubscribe_queue(self, q: asyncio.Queue[bytes]) -> None:
        async with self._lock:
            self._subscribers.discard(q)

    async def replay_since(self, last_event_id: int) -> list[bytes]:
        async with self._lock:
            if not self._replay:
                return []
            oldest_id = self._replay[0][0]
            newest_id = self._replay[-1][0]
            if last_event_id < oldest_id - 1:
                return []  # gap too large
            if last_event_id >= newest_id:
                return []
            return [chunk for (eid, chunk) in self._replay if eid > last_event_id]

    async def stream(
        self,
        *,
        last_event_id: Optional[int],
        keepalive_seconds: int,
        disconnected: Optional[DisconnectFn] = None,
        send_initial: Optional[bytes] = None,
        gap_event: Optional[bytes] = None,
    ) -> AsyncGenerator[bytes, None]:
        q = await self._subscribe_queue()
        try:
            if send_initial is not None:
                yield send_initial

            if last_event_id is not None:
                replay_chunks = await self.replay_since(last_event_id)
                if not replay_chunks and gap_event is not None:
                    yield gap_event
                else:
                    for ch in replay_chunks:
                        yield ch

            while True:
                if disconnected is not None:
                    try:
                        if await disconnected():
                            return
                    except Exception:
                        pass

                try:
                    ch = await asyncio.wait_for(q.get(), timeout=float(keepalive_seconds))
                    yield ch
                except asyncio.TimeoutError:
                    yield format_sse(SseEvent(event="ping", data={"ts": time.time(), "graph_id": self.graph_id}))
        finally:
            await self._unsubscribe_queue(q)


class EventBus:
    def __init__(
        self,
        *,
        subscriber_queue_max: int = DEFAULT_SUBSCRIBER_QUEUE_MAX,
        replay_max: int = DEFAULT_REPLAY_MAX,
    ) -> None:
        self._subscriber_queue_max = subscriber_queue_max
        self._replay_max = replay_max
        self._lock = asyncio.Lock()
        self._channels: dict[str, GraphChannel] = {}

    async def channel(self, graph_id: str) -> GraphChannel:
        async with self._lock:
            ch = self._channels.get(graph_id)
            if ch is None:
                ch = GraphChannel(
                    graph_id,
                    subscriber_queue_max=self._subscriber_queue_max,
                    replay_max=self._replay_max,
                )
                self._channels[graph_id] = ch
            return ch

    async def active_graph_ids(self) -> list[str]:
        async with self._lock:
            return list(self._channels.keys())

    async def _publish_raw(self, graph_id: str, event: str, data: dict[str, Any]) -> int:
        ch = await self.channel(graph_id)
        return await ch.publish_raw(event, data)

    async def publish(self, graph_id: str, event: str, data: dict[str, Any]) -> int:
        """
        COMMERCIAL ENFORCEMENT:
          - validate schema for all product events
          - on violation => emit structured 'error' event (and DO NOT emit the broken event)
        """
        if event in INTERNAL_EVENTS:
            return await self._publish_raw(graph_id, event, data)

        try:
            validate_event(event, data)
            return await self._publish_raw(graph_id, event, data)
        except Exception as e:
            err = _schema_error_payload(graph_id, event, e)
            # validate error itself (must never fail)
            try:
                validate_event("error", err)
            except Exception:
                # last-resort minimal error payload
                err = {
                    "graph_id": graph_id,
                    "ts": time.time(),
                    "type": "event_schema_violation",
                    "message": "schema error",
                }
            return await self._publish_raw(graph_id, "error", err)

    async def stream(
        self,
        graph_id: str,
        *,
        last_event_id: Optional[int],
        keepalive_seconds: int,
        disconnected: Optional[DisconnectFn] = None,
        send_initial: Optional[bytes] = None,
        gap_event: Optional[bytes] = None,
    ) -> AsyncGenerator[bytes, None]:
        ch = await self.channel(graph_id)
        async for chunk in ch.stream(
            last_event_id=last_event_id,
            keepalive_seconds=keepalive_seconds,
            disconnected=disconnected,
            send_initial=send_initial,
            gap_event=gap_event,
        ):
            yield chunk


BUS = EventBus()


# =============================================================================
# STREAM HELPERS
# =============================================================================
def parse_last_event_id(headers: dict[str, str]) -> Optional[int]:
    raw = headers.get("last-event-id") or headers.get("Last-Event-ID")
    if not raw:
        return None
    try:
        v = int(raw.strip())
        return v if v >= 0 else None
    except Exception:
        return None


def contract_chunk(graph_id: str, *, universe_label: str = "Universe") -> bytes:
    return format_sse(
        SseEvent(
            event="contract",
            id=0,
            data={
                "universe": {"graph_id": graph_id, "label": universe_label},
                "galaxies": [],
                "policy": {
                    "graph_id_is_user_universe": True,
                    "frontend_never_prompts_for_graph_id": True,
                    "galaxies_are_clusters_not_graphs": True,
                },
            },
        )
    )


def gap_chunk(graph_id: str, last_event_id: int) -> bytes:
    return format_sse(
        SseEvent(
            event="gap",
            data={
                "type": "replay_gap",
                "graph_id": graph_id,
                "last_event_id": last_event_id,
                "action": "client_should_resync_state",
            },
        )
    )


async def emit_evolution(graph_id: str, type_: str, data: dict[str, Any]) -> int:
    return await BUS.publish(
        graph_id, "evolution", {"graph_id": graph_id, "ts": time.time(), "type": type_, "data": data}
    )


async def emit_invention(graph_id: str, type_: str, data: dict[str, Any]) -> int:
    return await BUS.publish(
        graph_id, "invention", {"graph_id": graph_id, "ts": time.time(), "type": type_, "data": data}
    )


# =============================================================================
# EMIT HELPERS (ALWAYS VALIDATED VIA BUS.publish)
# =============================================================================
async def emit_fig_delta(graph_id: str, delta: dict[str, Any]) -> int:
    return await BUS.publish(graph_id, "fig_delta", {"graph_id": graph_id, "ts": time.time(), "delta": delta})


async def emit_chat_token(
    graph_id: str, trace_id: str, turn_id: str, token: str, index: int, *, done: bool = False
) -> int:
    return await BUS.publish(
        graph_id,
        "chat_token",
        {
            "graph_id": graph_id,
            "trace_id": trace_id,
            "turn_id": turn_id,
            "role": "assistant",
            "token": token,
            "index": int(index),
            "done": bool(done),
            "ts": time.time(),
        },
    )


async def emit_chat_used(graph_id: str, trace_id: str, turn_id: str, used_nodes: list[dict[str, Any]]) -> int:
    return await BUS.publish(
        graph_id,
        "chat_used",
        {
            "graph_id": graph_id,
            "trace_id": trace_id,
            "turn_id": turn_id,
            "used_nodes": used_nodes,
            "ts": time.time(),
        },
    )


async def emit_chat_store(
    graph_id: str,
    trace_id: str,
    turn_id: str,
    created_node_ids: list[str],
    created_fact_ids: list[str],
    summary: str,
) -> int:
    return await BUS.publish(
        graph_id,
        "chat_store",
        {
            "graph_id": graph_id,
            "trace_id": trace_id,
            "turn_id": turn_id,
            "created_node_ids": created_node_ids,
            "created_fact_ids": created_fact_ids,
            "summary": summary,
            "ts": time.time(),
        },
    )


async def emit_metrics(graph_id: str, cards: dict[str, Any]) -> int:
    return await BUS.publish(graph_id, "metrics", {"graph_id": graph_id, "ts": time.time(), "cards": cards})


async def emit_toast(graph_id: str, level: str, message: str, *, code: Optional[str] = None) -> int:
    payload = {"graph_id": graph_id, "ts": time.time(), "level": level, "message": message}
    if code is not None:
        payload["code"] = code
    return await BUS.publish(graph_id, "toast", payload)


async def emit_error(
    graph_id: str,
    type_: str,
    message: str,
    *,
    trace_id: Optional[str] = None,
    turn_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> int:
    payload: dict[str, Any] = {
        "graph_id": graph_id,
        "ts": time.time(),
        "type": type_,
        "message": message,
    }
    if trace_id is not None:
        payload["trace_id"] = trace_id
    if turn_id is not None:
        payload["turn_id"] = turn_id
    if details is not None:
        payload["details"] = details
    return await BUS.publish(graph_id, "error", payload)


# =============================================================================
# SYNC-TO-ASYNC DISPATCHER FOR ENGINE EVENTS
# =============================================================================
_main_loop = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Called by startup event to capture the main event loop."""
    global _main_loop
    _main_loop = loop


def emit_fig_delta_sync(graph_id: str, node_id: str, timestamp: float) -> None:
    """
    Sync wrapper to emit fig_delta events from the engine layer.
    Uses run_coroutine_threadsafe to safely dispatch to the async BUS.
    """
    global _main_loop
    if _main_loop is None or not _main_loop.is_running():
        return

    delta = {
        "kind": "node_added",
        "nodes_added": [{"id": node_id}],
        "nodes_removed": [],
        "links_added": [],
        "links_removed": [],
    }

    try:
        asyncio.run_coroutine_threadsafe(
            emit_fig_delta(graph_id, delta),
            _main_loop,
        )
    except Exception:
        pass


def emit_evolution_sync(graph_id: str, payload: dict) -> None:
    global _main_loop
    if _main_loop is None or not _main_loop.is_running():
        return
    # payload from core is {"type": ..., ...data}
    # split it
    evt_type = payload.get("type", "UNKNOWN")
    # rest is data
    data = {k: v for k, v in payload.items() if k != "type"}

    try:
        asyncio.run_coroutine_threadsafe(
            emit_evolution(graph_id, evt_type, data),
            _main_loop,
        )
    except Exception:
        pass


def emit_invention_sync(graph_id: str, payload: dict) -> None:
    global _main_loop
    if _main_loop is None or not _main_loop.is_running():
        return
    evt_type = payload.get("type", "UNKNOWN")
    data = {k: v for k, v in payload.items() if k != "type"}

    try:
        asyncio.run_coroutine_threadsafe(
            emit_invention(graph_id, evt_type, data),
            _main_loop,
        )
    except Exception:
        pass


# Subscribe to core events on module load
try:
    from faim.core.events import (
        subscribe_cluster_updated,
        subscribe_evolution_event,
        subscribe_inference_found,
        subscribe_insight_discovered,
        subscribe_invention_event,
        subscribe_node_created,
    )

    subscribe_node_created(emit_fig_delta_sync)
    subscribe_evolution_event(emit_evolution_sync)
    subscribe_invention_event(emit_invention_sync)

    # Analytics events - sync wrappers
    def emit_cluster_updated_sync(graph_id: str, clusters: list) -> None:
        global _main_loop
        if _main_loop is None or not _main_loop.is_running():
            return
        try:
            asyncio.run_coroutine_threadsafe(
                BUS.publish(graph_id, "cluster_updated", {"clusters": clusters}),
                _main_loop,
            )
        except Exception:
            pass

    def emit_inference_found_sync(graph_id: str, inferences: list) -> None:
        global _main_loop
        if _main_loop is None or not _main_loop.is_running():
            return
        try:
            asyncio.run_coroutine_threadsafe(
                BUS.publish(graph_id, "inference_found", {"inferences": inferences}),
                _main_loop,
            )
        except Exception:
            pass

    def emit_insight_discovered_sync(graph_id: str, insights: list) -> None:
        global _main_loop
        if _main_loop is None or not _main_loop.is_running():
            return
        try:
            asyncio.run_coroutine_threadsafe(
                BUS.publish(graph_id, "insight_discovered", {"insights": insights}),
                _main_loop,
            )
        except Exception:
            pass

    subscribe_cluster_updated(emit_cluster_updated_sync)
    subscribe_inference_found(emit_inference_found_sync)
    subscribe_insight_discovered(emit_insight_discovered_sync)

except ImportError:
    pass
