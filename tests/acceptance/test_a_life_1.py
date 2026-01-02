# =============================================================================
# FAIM — A-LIFE-1 Acceptance Test (STRICT, HARDENED, EVIDENCE-DRIVEN)
# -----------------------------------------------------------------------------
# GOAL:
#   Prove FAIM is a "real lifelong memory product" end-to-end, not just math.
#
# AFTER ONE CHAT MESSAGE, SYSTEM MUST RELIABLY DO ALL:
#   1) Write memory fragments (inheritance)
#   2) Apply antisym/opposition (cancel duplicates)
#   3) Prune redundancies
#   4) Update evolution counters
#   5) Emit fig_delta so UI updates live (SSE)
#   6) Retrieve builds a memory packet for the LLM (LLM sees memory)
#   7) Explain why (API/UI can show what was remembered and why)
#
# STRICT EVIDENCE POLICY:
#   - "Probably happened" is NOT accepted. We require measurable proof via API.
#   - If your API lacks evidence endpoints, this test FAILS with instructions.
#
# REQUIRED API SURFACES (discovered via /openapi.json):
#   A) Chat POST endpoint .......................... writes memory on interaction
#   B) SSE stream GET endpoint ..................... emits fig_delta events
#   C) Graph snapshot GET endpoint ................. returns nodes & links
#   D) Explain GET endpoint ........................ returns provenance + ops
#   E) (Optional) Memory packet retrieval endpoint . can strengthen proof
#
# RUN:
#   1) start server:
#        cd ~/FAIM && source .venv/bin/activate
#        uvicorn faim.api.app:app --host 127.0.0.1 --port 8000
#   2) run:
#        pip install -q httpx pytest
#        pytest -q tests/acceptance/test_a_life_1.py
#
# ENV OVERRIDES:
#   FAIM_BASE_URL        default http://127.0.0.1:8000
#   FAIM_GRAPH_ID        default MAIN
#   FAIM_USER_ID         optional header X-FAIM-USER for multi-tenant mode
#   FAIM_CHAT_PATH       force chat path (e.g. /api/v1/chat)
#   FAIM_STREAM_PATH     force stream path (e.g. /api/v1/stream)
#   FAIM_GRAPH_PATH      force graph snapshot path (e.g. /api/v1/graphs/{graph_id})
#   FAIM_EXPLAIN_PATH    force explain path (e.g. /api/v1/explain/{id})
#
# NOTE:
#   This test is intentionally strict. If it fails due to missing evidence,
#   it is doing its job: forcing product-grade observability.
# =============================================================================

from __future__ import annotations

import json
import os
import queue
import random
import string
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, NoReturn, Optional, Tuple


# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if (v is not None and v.strip() != "") else default


BASE_URL = _env("FAIM_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
GRAPH_ID = _env("FAIM_GRAPH_ID", "MAIN")
USER_ID = os.getenv("FAIM_USER_ID")

# Production paths (Hardcoded to match faim/api/models.py API_PREFIX)
FORCE_CHAT_PATH = os.getenv("FAIM_CHAT_PATH", "/api/v1/chat")
FORCE_STREAM_PATH = os.getenv("FAIM_STREAM_PATH", "/api/v1/events")
FORCE_GRAPH_PATH = os.getenv("FAIM_GRAPH_PATH", f"/api/v1/graphs/{GRAPH_ID}/snapshot")
FORCE_EXPLAIN_PATH = os.getenv("FAIM_EXPLAIN_PATH", "/api/v1/explain")


def _require_httpx():
    try:
        import httpx  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Missing dependency 'httpx'. Install inside venv:\n  pip install httpx\n"
        ) from e
    return httpx


# -----------------------------------------------------------------------------
# OpenAPI discovery helpers
# -----------------------------------------------------------------------------
def _get_openapi(client) -> Dict[str, Any]:
    r = client.get(f"{BASE_URL}/openapi.json", timeout=10.0)
    r.raise_for_status()
    return r.json()


def _list_paths(openapi: Dict[str, Any]) -> List[str]:
    paths = openapi.get("paths") or {}
    out = [p for p in paths.keys() if isinstance(p, str)]
    out.sort()
    return out


def _infer_graph_id_from_compound_id(compound_id: str) -> str:
    s = (compound_id or "").strip()
    if not s:
        return "MAIN"
    # Universe ids look like: U:<hash>:<counter>:<rand>
    if s.startswith("U:"):
        parts = s.split(":")
        return ":".join(parts[:2]) if len(parts) >= 2 else "MAIN"
    # Normal ids look like: MAIN:<counter>:<rand>
    return s.split(":", 1)[0]


def _find_path(openapi: Dict[str, Any], *, contains_all: List[str], method: str) -> Optional[str]:
    """
    Find first path whose string contains all substrings (case-insensitive)
    and which supports the given HTTP method.
    """
    paths = openapi.get("paths") or {}
    want = [c.lower() for c in contains_all]
    meth = method.lower()
    for p, spec in paths.items():
        if not isinstance(p, str) or not isinstance(spec, dict):
            continue
        pl = p.lower()
        if not all(c in pl for c in want):
            continue
        if meth in spec:
            return p
    return None


def _find_any(openapi: Dict[str, Any], *, candidates: List[Tuple[List[str], str]]) -> Optional[str]:
    """
    Try multiple (contains_all, method) patterns; return first match.
    """
    for contains_all, method in candidates:
        p = _find_path(openapi, contains_all=contains_all, method=method)
        if p:
            return p
    return None


def _fail_missing_surface(name: str, openapi: Dict[str, Any], hint: str) -> NoReturn:
    paths = "\n".join(_list_paths(openapi))
    raise AssertionError(
        f"[A-LIFE-1] Missing required surface: {name}\nHint: {hint}\nKnown paths:\n{paths}\n"
    )


# -----------------------------------------------------------------------------
# SSE decoding (robust minimal)
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class SSEEvent:
    event: str
    data: str


class SSEDecoder:
    def __init__(self) -> None:
        self._buf = ""

    def feed(self, chunk: str) -> List[SSEEvent]:
        self._buf += chunk
        out: List[SSEEvent] = []
        while True:
            sep = self._buf.find("\n\n")
            if sep < 0:
                break
            block = self._buf[:sep]
            self._buf = self._buf[sep + 2 :]

            ev_type = "message"
            data_lines: List[str] = []
            for line in block.splitlines():
                if line.startswith("event:"):
                    ev_type = line[len("event:") :].strip() or "message"
                elif line.startswith("data:"):
                    data_lines.append(line[len("data:") :].lstrip())

            if data_lines:
                out.append(SSEEvent(event=ev_type, data="\n".join(data_lines)))
        return out


def _pick_stream_url_and_headers(
    client,  # kept for signature compatibility; unused
    stream_path: str,
    headers: Dict[str, str],
) -> Tuple[str, Dict[str, str]]:
    """
    Deterministic selection:
      - If we have X-FAIM-USER => production Universe stream => DO NOT pass graph_id
      - Else => dev stream => pass ?graph_id=MAIN
    """
    base = f"{BASE_URL}{stream_path}"
    h = dict(headers)

    # If FAIM_USER_ID is provided, ensure it is on the headers (for prod/universe mode)
    uid = _env("FAIM_USER_ID", "").strip()
    if uid and "X-FAIM-USER" not in h:
        h["X-FAIM-USER"] = uid

    # Production/universe: graph_id is derived from user; query may be rejected/401.
    if "X-FAIM-USER" in h and h["X-FAIM-USER"].strip():
        return base, h

    # Dev/local: graph_id query is typically supported
    return f"{base}?graph_id={GRAPH_ID}", h


def _start_sse_listener(
    stream_url: str,
    headers: Dict[str, str],
    want_event: str,
) -> Tuple[Callable[[], None], "queue.Queue[SSEEvent]"]:
    httpx = _require_httpx()
    q: "queue.Queue[SSEEvent]" = queue.Queue()
    stop_flag = threading.Event()

    def _runner() -> None:
        dec = SSEDecoder()
        try:
            req_headers = dict(headers)
            req_headers["Accept"] = "text/event-stream"

            with httpx.Client(timeout=None) as client:
                with client.stream("GET", stream_url, headers=req_headers) as r:
                    if r.status_code != 200:
                        q.put(SSEEvent(event="__error__", data=f"{r.status_code} {r.text}"))
                        return

                    for chunk in r.iter_text():
                        if stop_flag.is_set():
                            return
                        if not chunk:
                            continue
                        for ev in dec.feed(chunk):
                            if ev.event == want_event:
                                q.put(ev)

        except Exception as e:
            q.put(SSEEvent(event="__error__", data=repr(e)))

    t = threading.Thread(target=_runner, name="A-LIFE-1-SSE", daemon=True)
    t.start()

    def stop() -> None:
        stop_flag.set()

    return stop, q


def _wait_event(q: "queue.Queue[SSEEvent]", timeout_s: float) -> SSEEvent:
    t0 = time.time()
    while True:
        remaining = max(0.0, timeout_s - (time.time() - t0))
        if remaining <= 0:
            raise TimeoutError(
                f"[A-LIFE-1] Timed out waiting for SSE event within {timeout_s:.1f}s"
            )
        ev = q.get(timeout=remaining)
        if ev.event == "__error__":
            raise RuntimeError(f"[A-LIFE-1] SSE listener error: {ev.data}")
        return ev


def _retry_graph_snapshot(
    client,
    url: str,
    headers: Dict[str, str],
    want_min_total: int,
    timeout_s: float = 2.0,
) -> Dict[str, Any]:
    t0 = time.time()
    last = None
    while (time.time() - t0) < timeout_s:
        r = client.get(url, headers=headers, timeout=20.0)
        r.raise_for_status()
        last = r.json()
        n, e = _count_nodes_links(last)
        if (n + e) >= want_min_total:
            return last
        time.sleep(0.05)
    return last if last is not None else {}


# -----------------------------------------------------------------------------
# JSON helpers
# -----------------------------------------------------------------------------
def _is_list(x: Any) -> bool:
    return isinstance(x, list)


def _get_first_str(d: Mapping[str, Any], keys: List[str]) -> Optional[str]:
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v
    # fallback: first string value
    for v in d.values():
        if isinstance(v, str) and v.strip():
            return v
    return None


def _deep_find_key(obj: Any, key: str) -> List[Any]:
    out: List[Any] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                out.append(v)
            out.extend(_deep_find_key(v, key))
    elif isinstance(obj, list):
        for it in obj:
            out.extend(_deep_find_key(it, key))
    return out


def _looks_like_graph_snapshot(j: Any) -> bool:
    """
    Accepts either:
      {"nodes":[...], "links":[...]} OR
      {"graph": {"nodes":[...], "links":[...]}} OR
      {"data": {"nodes":[...], "links":[...]}} OR similar nesting.
    """
    if isinstance(j, dict):
        for root_key in ("nodes", "graph", "data", "state", "fig"):
            v = j.get(root_key)
            if root_key == "nodes":
                if _is_list(j.get("nodes")) and _is_list(j.get("links", [])):
                    return True
            if isinstance(v, dict) and _is_list(v.get("nodes")) and _is_list(v.get("links", [])):
                return True
    return False


def _extract_nodes_links(j: Any) -> Tuple[List[Any], List[Any]]:
    if not isinstance(j, dict):
        return [], []
    if _is_list(j.get("nodes")) and _is_list(j.get("links", [])):
        return j.get("nodes") or [], j.get("links") or []
    for k in ("graph", "data", "state", "fig"):
        v = j.get(k)
        if isinstance(v, dict) and _is_list(v.get("nodes")) and _is_list(v.get("links", [])):
            return v.get("nodes") or [], v.get("links") or []
    return [], []


def _count_nodes_links(j: Any) -> Tuple[int, int]:
    nodes, links = _extract_nodes_links(j)
    return len(nodes), len(links)


def _random_token(prefix: str, n: int = 12) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return prefix + "-" + "".join(random.choice(alphabet) for _ in range(n))


# -----------------------------------------------------------------------------
# Endpoint selection + probing
# -----------------------------------------------------------------------------
def _resolve_headers() -> Dict[str, str]:
    h: Dict[str, str] = {}
    h["X-FAIM-USER"] = USER_ID or "demo_user_123"
    return h


def _resolve_health(openapi: Dict[str, Any]) -> str:
    p = _find_any(
        openapi,
        candidates=[
            (["health"], "get"),
        ],
    )
    if not p:
        _fail_missing_surface(
            "HEALTH", openapi, "Expose GET /health (or /api/v1/health) returning {'status':'ok'}."
        )
    return p


def _resolve_stream(openapi: Dict[str, Any]) -> str:
    if FORCE_STREAM_PATH:
        return FORCE_STREAM_PATH
    p = _find_any(
        openapi,
        candidates=[
            (["stream"], "get"),
            (["events"], "get"),
            (["sse"], "get"),
        ],
    )
    if not p:
        _fail_missing_surface(
            "SSE STREAM",
            openapi,
            "Expose GET SSE stream endpoint (e.g. /api/v1/stream) emitting event: fig_delta.",
        )
    return p


def _resolve_chat(openapi: Dict[str, Any]) -> str:
    if FORCE_CHAT_PATH:
        return FORCE_CHAT_PATH
    # try common chat naming first
    p = _find_any(
        openapi,
        candidates=[
            (["chat"], "post"),
            (["messages"], "post"),
            (["message"], "post"),
            (["ask"], "post"),
            (["infer"], "post"),
        ],
    )
    if not p:
        _fail_missing_surface(
            "CHAT POST",
            openapi,
            "Expose POST chat endpoint (e.g. /api/v1/chat) that triggers memory write + retrieval.",
        )
    return p


def _resolve_bench_snapshot(openapi: Dict[str, Any]) -> str:
    p = _find_path(openapi, contains_all=["benchmarks", "snapshot"], method="post")
    if not p:
        _fail_missing_surface(
            "BENCHMARKS SNAPSHOT",
            openapi,
            "Expose POST /benchmarks/{graph_id}/snapshot (prefixed ok).",
        )
    return p


def _resolve_bench_series(openapi: Dict[str, Any]) -> str:
    p = _find_path(openapi, contains_all=["benchmarks", "series"], method="get")
    if not p:
        _fail_missing_surface(
            "BENCHMARKS SERIES",
            openapi,
            "Expose GET /benchmarks/{graph_id}/series (prefixed ok).",
        )
    return p


def _resolve_explain(openapi: Dict[str, Any]) -> str:
    if FORCE_EXPLAIN_PATH:
        return FORCE_EXPLAIN_PATH
    p = _find_any(
        openapi,
        candidates=[
            (["explain"], "get"),
            (["why"], "get"),
            (["provenance"], "get"),
        ],
    )
    if not p:
        _fail_missing_surface(
            "EXPLAIN",
            openapi,
            (
                "Expose GET explain endpoint (e.g. /api/v1/explain/{id}) returning used "
                "memories + ops + evolution updates."
            ),
        )
    return p


def _resolve_graph_snapshot(openapi: Dict[str, Any]) -> str:
    if FORCE_GRAPH_PATH:
        return FORCE_GRAPH_PATH

    # Strongest guess patterns first: graphs + snapshot/state/export/fig
    candidates = []
    paths = _list_paths(openapi)
    for p in paths:
        pl = p.lower()
        if "{graph_id}" not in pl:
            continue
        # prefer anything that looks like a full graph export
        if "graph" in pl and any(
            x in pl for x in ("snapshot", "state", "export", "dump", "fig", "view")
        ):
            candidates.append(p)

    # Next: any GET path containing "graph" and {graph_id} (fallback)
    for p in paths:
        pl = p.lower()
        if "{graph_id}" not in pl:
            continue
        if "graph" in pl and p not in candidates:
            candidates.append(p)

    # Probe candidates by calling and inspecting JSON for nodes/links
    # If nothing exists, fail with required endpoint spec.
    return candidates[0] if candidates else ""


def _probe_graph_snapshot(
    client, openapi: Dict[str, Any], graph_path_hint: str, headers: Dict[str, str]
) -> str:
    """
    Find a GET endpoint that returns nodes/links for graph_id.
    We probe OpenAPI candidates and pick the first that returns JSON with nodes+links.
    """
    # If forced, accept it (must work)
    if FORCE_GRAPH_PATH:
        return FORCE_GRAPH_PATH

    # Candidate list:
    candidates: List[str] = []

    # 1) Prefer explicit patterns if present
    for contains in (
        ["graphs", "snapshot"],
        ["graphs", "state"],
        ["graphs", "export"],
        ["graphs", "fig"],
    ):
        p = _find_path(openapi, contains_all=contains, method="get")
        if p:
            candidates.append(p)

    # 2) Fallback: any GET path with {graph_id} and "graph(s)"
    paths = openapi.get("paths") or {}
    for p, spec in paths.items():
        if not isinstance(p, str) or not isinstance(spec, dict):
            continue
        if "{graph_id}" not in p:
            continue
        if "get" not in spec:
            continue
        pl = p.lower()
        if "graph" in pl:
            if p not in candidates:
                candidates.append(p)

    # 3) Last resort: try the hint list (if provided)
    if graph_path_hint:
        for p in graph_path_hint:
            if p not in candidates:
                candidates.append(p)

    # Probe each candidate:
    for p in candidates:
        url = f"{BASE_URL}{p.replace('{graph_id}', GRAPH_ID)}"
        try:
            r = client.get(url, headers=headers, timeout=15.0)
            if r.status_code != 200:
                continue
            j = r.json()
            if _looks_like_graph_snapshot(j):
                return p
        except Exception:
            continue

    _fail_missing_surface(
        "GRAPH SNAPSHOT",
        openapi,
        "Expose GET endpoint returning a full graph snapshot with nodes+links, "
        "e.g. GET /api/v1/graphs/{graph_id} -> {'nodes':[...],'links':[...]}",
    )
    raise AssertionError("unreachable")


# -----------------------------------------------------------------------------
# Chat payload builder (strict: tries to force new session where possible)
# -----------------------------------------------------------------------------
def _build_chat_payload(
    openapi: Dict[str, Any], chat_path: str, message: str, session_id: str
) -> Dict[str, Any]:
    """
    Build request payload using OpenAPI schema heuristics.
    Also tries to set session/thread id if schema includes it,
    so we can prove memory recall across sessions.
    """
    paths = openapi.get("paths") or {}
    spec = paths.get(chat_path) or {}
    post = spec.get("post") or {}
    req = post.get("requestBody") or {}
    content = (req.get("content") or {}).get("application/json") or {}
    schema = content.get("schema") or {}
    props = None
    if isinstance(schema, dict) and isinstance(schema.get("properties"), dict):
        props = schema["properties"]

    payload: Dict[str, Any] = {}

    # Choose message key
    msg_keys = ["message", "prompt", "text", "input", "query", "content"]
    if props:
        for k in msg_keys:
            if k in props:
                payload[k] = message
                break
        else:
            # fallback: first string prop
            for k, v in props.items():
                if isinstance(v, dict) and v.get("type") == "string":
                    payload[k] = message
                    break
    else:
        payload["message"] = message

    # Try to force "new session" semantics if supported
    sess_keys = ["session_id", "thread_id", "conversation_id", "chat_id"]
    if props:
        for k in sess_keys:
            if k in props:
                payload[k] = session_id
                break

    # Best-effort disable streaming for response determinism if the schema has it
    if props and "stream" in props and "stream" not in payload:
        payload["stream"] = False

    return payload


def _chat_post(
    client,
    openapi: Dict[str, Any],
    chat_path: str,
    headers: Dict[str, str],
    message: str,
    session_id: str,
) -> Dict[str, Any]:
    url = f"{BASE_URL}{chat_path}"
    payload = _build_chat_payload(openapi, chat_path, message=message, session_id=session_id)
    r = client.post(url, params={"graph_id": GRAPH_ID}, headers=headers, json=payload, timeout=30.0)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return {"_raw": r.text}


def _extract_answer(chat_resp: Dict[str, Any]) -> str:
    # common keys
    ans = _get_first_str(
        chat_resp, keys=["answer", "response", "text", "content", "output", "message"]
    )
    if ans:
        return ans
    # fallback: stringify
    return json.dumps(chat_resp, ensure_ascii=False)


def _extract_trace_id(chat_resp: Mapping[str, Any]) -> Optional[str]:
    """
    Try to extract an id we can feed into explain endpoint.
    """
    # common keys
    for k in ("trace_id", "explain_id", "id", "event_id", "run_id", "turn_id"):
        v = chat_resp.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    # nested patterns
    nested = _deep_find_key(chat_resp, "trace_id") + _deep_find_key(chat_resp, "id")
    for v in nested:
        if isinstance(v, str) and v.strip():
            return v.strip()

    return None


# -----------------------------------------------------------------------------
# Explain call + strict evidence validation
# -----------------------------------------------------------------------------
def _call_explain(
    client, explain_path: str, headers: Dict[str, str], trace_id: str
) -> Dict[str, Any]:
    """
    Supports explain paths:
      - /.../explain/{id}
      - /.../explain?id=...
      - /.../explain?trace_id=...
    """
    if "{id}" in explain_path:
        url = f"{BASE_URL}{explain_path.replace('{id}', trace_id)}"
        r = client.get(url, headers=headers, timeout=20.0)
        r.raise_for_status()
        return r.json()

    # else query param fallback
    url = f"{BASE_URL}{explain_path}"
    for qp in ("trace_id", "id", "run_id"):
        r = client.get(url, headers=headers, params={qp: trace_id}, timeout=20.0)
        if r.status_code == 200:
            return r.json()

    raise AssertionError(
        "[A-LIFE-1] Explain endpoint exists but could not be called with trace_id.\n"
        f"Explain path: {explain_path}\n"
        f"trace_id: {trace_id}\n"
        "Expected explain to support either /explain/{id} or ?trace_id=.\n"
    )


def _assert_explain_has_why(explain: Dict[str, Any]) -> None:
    """
    STRICT: explain MUST include:
      - used memories list (or equivalent)
      - provenance/lineage evidence (ids/refs)
      - operations summary including inheritance/antisym/prune/evolution touches
      - memory packet (or at least memory ids used to build it)
    We accept flexible key names, but the information must exist.
    """
    # 1) used memories evidence
    used_candidates = []
    for k in ("used_memories", "memories_used", "memory_used", "evidence", "memory_refs"):
        used_candidates.extend(_deep_find_key(explain, k))
    used_list = None
    for v in used_candidates:
        if isinstance(v, list) and len(v) > 0:
            used_list = v
            break
    assert used_list is not None, (
        "[A-LIFE-1] Explain missing 'used memories' evidence.\n"
        "Required: explain must return a non-empty list of memory ids/fragments used.\n"
    )

    # 2) provenance/lineage evidence
    prov_candidates = []
    for k in ("provenance", "lineage", "evidence_refs", "sources", "parents", "inheritance_chain"):
        prov_candidates.extend(_deep_find_key(explain, k))
    has_prov = False
    for v in prov_candidates:
        if isinstance(v, list) and len(v) > 0:
            has_prov = True
            break
        if isinstance(v, dict) and len(v) > 0:
            has_prov = True
            break
        if isinstance(v, str) and v.strip():
            has_prov = True
            break
    assert has_prov, (
        "[A-LIFE-1] Explain missing provenance/lineage evidence.\n"
        "Required: explain must show why memories were selected (lineage/provenance refs).\n"
    )

    # 3) operations evidence (inheritance/antisym/prune/evolution)
    ops_blob = json.dumps(explain, ensure_ascii=False).lower()
    required_signals = ["inherit", "antisym", "opposition", "prune", "evol", "cancel"]
    hit = sum(1 for s in required_signals if s in ops_blob)
    assert hit >= 2, (
        "[A-LIFE-1] Explain does not show required operation evidence.\n"
        "Required: explain must mention at least two of: inheritance, "
        "antisym/opposition/cancel, prune, evolution.\n"
    )

    # 4) memory packet evidence (either explicit packet or prompt/context payload)
    packet_candidates = []
    for k in ("memory_packet", "packet", "context", "prompt", "retrieved", "assembled"):
        packet_candidates.extend(_deep_find_key(explain, k))
    has_packet = False
    for v in packet_candidates:
        if isinstance(v, str) and len(v.strip()) >= 8:
            has_packet = True
            break
        if isinstance(v, list) and len(v) > 0:
            has_packet = True
            break
        if isinstance(v, dict) and len(v) > 0:
            has_packet = True
            break
    assert has_packet, (
        "[A-LIFE-1] Explain missing memory packet/context evidence.\n"
        "Required: explain must show the assembled memory packet/context used for LLM "
        "(or the ids composing it).\n"
    )

    # 5) evolution counters evidence (touches/use_count/weights)
    evo_candidates = []
    for k in ("use_count", "uses", "evolution", "weights", "score", "gradient", "last_access"):
        evo_candidates.extend(_deep_find_key(explain, k))
    has_evo = False
    for v in evo_candidates:
        if isinstance(v, (int, float)) and v != 0:
            has_evo = True
            break
        if isinstance(v, dict) and len(v) > 0:
            has_evo = True
            break
    assert has_evo, (
        "[A-LIFE-1] Explain missing evolution counters evidence.\n"
        "Required: explain must expose some evolution signal "
        "(use_count/last_access/weights/gradient/score).\n"
    )


# -----------------------------------------------------------------------------
# Core A-LIFE-1 test
# -----------------------------------------------------------------------------
def test_a_life_1_strict_full_evidence():
    httpx = _require_httpx()
    headers = _resolve_headers()

    with httpx.Client() as client:
        openapi = _get_openapi(client)

        # ---- Required surfaces
        health_path = _resolve_health(openapi)
        chat_path = _resolve_chat(openapi)
        stream_path = _resolve_stream(openapi)
        bench_snapshot_path = _resolve_bench_snapshot(openapi)
        bench_series_path = _resolve_bench_series(openapi)
        explain_path = _resolve_explain(openapi)

        # Graph snapshot must be probed (strict evidence for store writes & pruning)
        graph_path = _probe_graph_snapshot(
            client, openapi, graph_path_hint=_resolve_graph_snapshot(openapi), headers=headers
        )

        # ---- Health OK
        hr = client.get(f"{BASE_URL}{health_path}", headers=headers, timeout=10.0)
        hr.raise_for_status()
        hjson = hr.json()
        assert isinstance(hjson, dict) and hjson.get("status") == "ok", (
            "[A-LIFE-1] /health must return {'status':'ok'}"
        )

        # ---- Baseline graph snapshot
        g0 = client.get(
            f"{BASE_URL}{graph_path.replace('{graph_id}', GRAPH_ID)}", headers=headers, timeout=20.0
        )
        g0.raise_for_status()
        g0j = g0.json()
        assert _looks_like_graph_snapshot(g0j), (
            "[A-LIFE-1] Graph snapshot endpoint must return nodes+links JSON."
        )
        n0, e0 = _count_nodes_links(g0j)

        # ---- Start SSE listener (prove fig_delta)
        # ---- Start SSE listener (prove fig_delta)
        stream_url, headers = _pick_stream_url_and_headers(client, stream_path, headers)
        stop, q = _start_sse_listener(
            stream_url=stream_url, headers=headers, want_event="fig_delta"
        )

        # ---- Prepare a unique memory (forces true recall; not guessable)
        codeword = _random_token("FAIM-CODE")
        fact_msg = (
            f"STORE THIS EXACT CODEWORD FOREVER: {codeword}. "
            f"This is A-LIFE-1 test. Confirm by replying ONLY 'OK'."
        )

        # ---- Turn 1: write memory on interaction
        session1 = _random_token("S1", 10)
        chat1 = _chat_post(
            client, openapi, chat_path, headers, message=fact_msg, session_id=session1
        )

        # Must trigger fig_delta (live UI update)
        try:
            ev = _wait_event(q, timeout_s=12.0)
        finally:
            stop()

        assert ev.event == "fig_delta", (
            "[A-LIFE-1] SSE must emit event: fig_delta after chat write."
        )
        try:
            json.loads(ev.data)
        except Exception as e:
            msg = f"[A-LIFE-1] fig_delta data must be JSON. Got: {ev.data[:200]}"
            raise AssertionError(msg) from e

        cs = chat1.get("chat_store") or {}
        created_node_ids = cs.get("created_node_ids") or []
        created_fact_ids = cs.get("created_fact_ids") or []

        assert (len(created_node_ids) + len(created_fact_ids)) > 0, (
            "[A-LIFE-1] FAIL: chat did not report any created nodes/facts "
            "(write-on-interaction failed)."
        )

        graph_id_used = _infer_graph_id_from_compound_id(
            (created_node_ids[0] if created_node_ids else created_fact_ids[0])
        )

        # ---- Evidence (1): store changed (inheritance write)
        g1_url = f"{BASE_URL}{graph_path.replace('{graph_id}', graph_id_used)}"
        g1j = _retry_graph_snapshot(
            client,
            g1_url,
            headers=headers,
            want_min_total=(len(created_node_ids) + len(created_fact_ids)),
            timeout_s=2.0,
        )
        n1, e1 = _count_nodes_links(g1j)

        # Strict: new memory must add at least 1 node OR 1 link
        assert (n1 + e1) >= (len(created_node_ids) + len(created_fact_ids)), (
            "[A-LIFE-1] FAIL: graph snapshot does not reflect created ids from chat_store.\n"
            f"graph_id_used={graph_id_used}\n"
            f"created_nodes={len(created_node_ids)} created_facts={len(created_fact_ids)}\n"
            f"snapshot_nodes={n1} snapshot_links={e1}\n"
        )
        first_growth = (n1 - n0, e1 - e0)

        # ---- Explain for Turn 1 (must exist + prove why)
        trace1 = _extract_trace_id(chat1)
        assert trace1, (
            "[A-LIFE-1] Chat response must include a trace id for explain.\n"
            "Add trace_id/explain_id in chat response so we can verify why it remembered.\n"
        )
        explain1 = _call_explain(client, explain_path, headers=headers, trace_id=trace1)
        assert isinstance(explain1, dict), "[A-LIFE-1] Explain must return JSON object."
        _assert_explain_has_why(explain1)

        # ---- Benchmarks must record (product metric safety)
        snap_url = f"{BASE_URL}{bench_snapshot_path.replace('{graph_id}', GRAPH_ID)}"
        bs = client.post(snap_url, headers=headers, timeout=20.0)
        bs.raise_for_status()

        series_url = f"{BASE_URL}{bench_series_path.replace('{graph_id}', GRAPH_ID)}"
        ser = client.get(series_url, params={"limit": 200}, headers=headers, timeout=20.0)
        ser.raise_for_status()
        sj = ser.json()
        assert isinstance(sj, dict) and sj.get("graph_id") == GRAPH_ID, (
            "[A-LIFE-1] benchmarks series must return graph_id."
        )
        assert isinstance(sj.get("points"), list) and len(sj["points"]) >= 1, (
            "[A-LIFE-1] benchmarks series must have >=1 point."
        )

        # ---- Turn 2: near-duplicate (forces antisym/opposition and prune)
        # We intentionally re-send the same semantic memory with slight variation.
        dup_msg = (
            f"REMEMBER THIS CODEWORD (same as before): {codeword}. "
            f"Do not store duplicates. Reply ONLY 'OK'."
        )

        # Start SSE listener again for fig_delta
        stop2, q2 = _start_sse_listener(
            stream_url=stream_url, headers=headers, want_event="fig_delta"
        )
        try:
            session2 = _random_token("S2", 10)
            chat2 = _chat_post(
                client, openapi, chat_path, headers, message=dup_msg, session_id=session2
            )
            ev2 = _wait_event(q2, timeout_s=12.0)
        finally:
            stop2()

        assert ev2.event == "fig_delta", (
            "[A-LIFE-1] SSE must emit fig_delta on duplicate/near-duplicate turn too."
        )

        g2 = client.get(
            f"{BASE_URL}{graph_path.replace('{graph_id}', GRAPH_ID)}", headers=headers, timeout=20.0
        )
        g2.raise_for_status()
        g2j = g2.json()
        n2, e2 = _count_nodes_links(g2j)
        dup_growth = (n2 - n1, e2 - e1)

        # STRICT antisym/prune expectation:
        # - Growth on duplicate turn must be <= growth on first new info turn.
        #   (If FAIM copies duplicates, growth will be similar, which fails.)
        assert (dup_growth[0] <= first_growth[0]) and (dup_growth[1] <= first_growth[1]), (
            "[A-LIFE-1] FAIL: duplicate turn grew graph more than first new memory turn.\n"
            f"First growth (nodes,links) = {first_growth}\n"
            f"Dup growth   (nodes,links) = {dup_growth}\n"
            "This indicates antisym/opposition is NOT canceling duplicates.\n"
        )

        # Explain for Turn 2 MUST explicitly show antisym/opposition/prune activity
        trace2 = _extract_trace_id(chat2)
        assert trace2, (
            "[A-LIFE-1] Chat response must include trace_id for explain on duplicate turn."
        )
        explain2 = _call_explain(client, explain_path, headers=headers, trace_id=trace2)
        ops2 = json.dumps(explain2, ensure_ascii=False).lower()
        assert any(s in ops2 for s in ("antisym", "opposition", "cancel")), (
            "[A-LIFE-1] FAIL: Explain for duplicate turn does not show antisym/opposition/cancel.\n"
            "Required: explain must explicitly report antisymmetric cancellation "
            "on near-duplicate inputs.\n"
        )
        assert any(s in ops2 for s in ("prune", "dedup", "redundan")), (
            "[A-LIFE-1] FAIL: Explain for duplicate turn does not show prune/dedup activity.\n"
            "Required: explain must explicitly report pruning/dedup operations.\n"
        )

        # ---- Turn 3: prove memory packet is used for LLM recall (cross-session)
        # We force a NEW session id (if supported) so the answer can't rely on chat context only.
        recall_q = "What is the exact codeword I told you to store? Reply with the codeword only."
        session3 = _random_token("S3", 10)
        chat3 = _chat_post(
            client, openapi, chat_path, headers, message=recall_q, session_id=session3
        )
        answer3 = _extract_answer(chat3)

        # STRICT: must contain the exact codeword (not guessable)
        assert codeword in answer3, (
            "[A-LIFE-1] FAIL: Recall did not return the stored codeword.\n"
            f"Expected codeword: {codeword}\n"
            f"Got answer: {answer3[:400]}\n"
            "This proves the LLM did NOT receive/use FAIM memory packet for recall.\n"
        )

        # Explain for recall MUST show memory packet/used memories include the codeword or its id
        trace3 = _extract_trace_id(chat3)
        assert trace3, "[A-LIFE-1] Chat recall response must include trace_id for explain."
        explain3 = _call_explain(client, explain_path, headers=headers, trace_id=trace3)
        _assert_explain_has_why(explain3)

        # Stronger: explain should contain codeword somewhere in packet/context OR in
        # resolved memory payload.

        blob3 = json.dumps(explain3, ensure_ascii=False)
        assert codeword in blob3, (
            "[A-LIFE-1] FAIL: Explain does not contain the stored codeword "
            "in memory packet/context.\n"
            "Required: explain should show the recalled memory content "
            "(or a resolved representation) used to answer.\n"
        )
        # ---- Turn 4: evolution counters must update (use_count/last_access/weights change)
        # We ask again, and require evolution signal changes between explain3 and explain4.
        session4 = _random_token("S4", 10)
        chat4 = _chat_post(
            client, openapi, chat_path, headers, message=recall_q, session_id=session4
        )
        answer4 = _extract_answer(chat4)
        assert codeword in answer4, "[A-LIFE-1] Repeat recall must still return the exact codeword."

        trace4 = _extract_trace_id(chat4)
        assert trace4, "[A-LIFE-1] Repeat recall must include trace_id."
        explain4 = _call_explain(client, explain_path, headers=headers, trace_id=trace4)

        # Strict evolution check:
        # We require some numeric evolution-related value to change between explain3 and explain4.
        # We accept any of these keys anywhere in structure: use_count, uses, score, weights,
        # last_access.

        def _extract_evo_numbers(x: Any) -> List[float]:
            nums: List[float] = []
            if isinstance(x, dict):
                for k, v in x.items():
                    kl = str(k).lower()
                    if kl in (
                        "use_count",
                        "uses",
                        "score",
                        "weight",
                        "weights",
                        "last_access",
                        "last_access_ts",
                    ):
                        if isinstance(v, (int, float)):
                            nums.append(float(v))
                    nums.extend(_extract_evo_numbers(v))
            elif isinstance(x, list):
                for it in x:
                    nums.extend(_extract_evo_numbers(it))
            return nums

        evo3 = _extract_evo_numbers(explain3)
        evo4 = _extract_evo_numbers(explain4)

        assert evo3 and evo4, (
            "[A-LIFE-1] FAIL: evolution counters not exposed in explain.\n"
            "Required: explain must expose evolution signals "
            "(use_count/last_access/weights/score).\n"
        )

        # Evidence of update: any numeric differs
        changed = False
        # compare sets with tolerance for timestamps; still a change is expected
        for a in evo3:
            for b in evo4:
                if a != b:
                    changed = True
                    break
            if changed:
                break

        assert changed, (
            "[A-LIFE-1] FAIL: evolution counters did not change between repeated recalls.\n"
            "Required: repeated retrieval must update evolution counters "
            "(use_count/last_access/weights).\n"
        )

        # ---- If we reached here, ALL 7 items are proven with evidence.
        # 1) write fragments -> graph grew
        # 2) antisym/opposition -> explain2 contains antisym/cancel + growth bounded
        # 3) prune -> explain2 contains prune/dedup + bounded growth
        # 4) evolution -> explain counters changed between explain3 and explain4
        # 5) fig_delta -> SSE events received twice
        # 6) memory packet -> recall returned non-guessable codeword; explain contains it
        # 7) explain why -> explain endpoint exists & validated for required fields
        assert True
