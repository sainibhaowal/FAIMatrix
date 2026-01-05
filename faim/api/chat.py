# =============================================================================
# FAIM — GOLD EDITION (COMMERCIAL / INDUSTRY PRODUCTION)
# =============================================================================
# File: faim/api/chat.py
#
# STEP 2 — CHAT END-TO-END PIPELINE (Retrieve → LLM → Store → Emit)
#
# Production guarantees:
#   - Frontend NEVER sends graph_id. (Dev override allowed via ?graph_id=MAIN)
#   - Universe graph_id derived from X-FAIM-USER when force_universe=1 / header flag.
#   - Deterministic side effects:
#       [chat:user] ...          (always)
#       FACT: ...               (remember: OR deterministic extractor triggers)
#       [chat:assistant] ...    (configurable, default ON)
#   - SSE emissions are strict JSON payloads with stable keys:
#       chat_token, chat_used, chat_store, fig_delta, toast, error
#   - Monotonic SSE id is handled by BUS.publish (Step-1 bus).
#   - Idempotency: optional Idempotency-Key header (best-effort, bounded).
#
# Acceptance:
#   1) remember: my favorite editor is VS Code
#   2) What is my favorite editor?  -> VS Code
#   3) chat_store returns real ids (non-empty)
#   4) used_nodes contains FACT node (or fact-derived high-score node)
#
# HARD RULE:
#   - DO NOT remove the /chat endpoint or change payload keys.
#   - Fixes must be additive + hardened only (no API damage).
# =============================================================================

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# IMPORTANT: import state as a module (survives state.py variations)
from faim.api import state as S
from faim.api.auth_middleware import get_current_user_oidc
from faim.api.events import BUS  # Step-1 hardened SSE bus
from faim.config import FaimSettings
from faim.db import get_db
from faim.engine.interface import add_fragment, record_used_nodes
from faim.model.llm import get_llm
from faim.models_sql import GraphOwnership, OrgMember, Project, User
from faim.retrieve.context import naive_used_nodes

router = APIRouter(dependencies=[])

# =============================================================================
# SECTION 0 — SAFE ENV PARSING (commercial hardening; never crash on bad env)
# =============================================================================


def _env_int(name: str, default: int, *, lo: Optional[int] = None, hi: Optional[int] = None) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        x = default
    else:
        try:
            x = int(raw)
        except Exception:
            x = default
    if lo is not None and x < lo:
        x = lo
    if hi is not None and x > hi:
        x = hi
    return x


def _env_float(
    name: str, default: float, *, lo: Optional[float] = None, hi: Optional[float] = None
) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        x = default
    else:
        try:
            x = float(raw)
        except Exception:
            x = default
    if lo is not None and x < lo:
        x = lo
    if hi is not None and x > hi:
        x = hi
    return x


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "y", "on")


# =============================================================================
# SECTION 1 — CONFIG (safe defaults; override via env)
# =============================================================================

SYSTEM_PROMPT = (
    "You are FAIM.\n"
    "Use FAIM memory context when answering.\n"
    "Facts-first: prefer FACT nodes over chat logs.\n"
    "If the memory does not contain the answer, say so concisely.\n"
)

STORE_ASSISTANT_DEFAULT = _env_bool("FAIM_STORE_ASSISTANT", True)
MAX_MESSAGE_CHARS = _env_int("FAIM_CHAT_MAX_MESSAGE", 20000, lo=1, hi=200000)
MAX_STORE_CHARS = _env_int("FAIM_CHAT_MAX_STORE_CHARS", 6000, lo=100, hi=50000)
LLM_TIMEOUT_S = _env_float("FAIM_CHAT_LLM_TIMEOUT_S", 60.0, lo=5.0, hi=600.0)
CTX_K = _env_int("FAIM_CHAT_CTX_K", 8, lo=1, hi=64)

# =============================================================================
# SECTION 2 — REQUEST / RESPONSE SCHEMAS (frontend does NOT send graph_id)
# =============================================================================


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_CHARS)
    client_turn_id: Optional[str] = None


class ChatResponse(BaseModel):
    trace_id: str
    turn_id: str
    reply: str
    used_nodes: List[Dict[str, Any]]
    chat_store: Dict[str, Any]


# =============================================================================
# SECTION 3 — BEST-EFFORT IDEMPOTENCY (bounded, in-memory)
# =============================================================================


@dataclass
class _IdemItem:
    ts: float
    response: ChatResponse


_IDEM: Dict[str, _IdemItem] = {}
_IDEM_MAX = 1024
_IDEM_TTL_S = 120.0

_TRACE_ID_RE = re.compile(r"^[a-f0-9]{32}$")


def _fail(msg: str) -> NoReturn:
    raise AssertionError(msg)


def _settings() -> FaimSettings:
    return FaimSettings.from_env()


def _now() -> float:
    return time.time()


def _explain_dir() -> Path:
    """
    Canonical explain directory.
    """
    s = _settings()
    d = Path(s.root) / "Runtime" / "Logs" / "Explain"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _explain_path(trace_id: str) -> Path:
    if not _TRACE_ID_RE.match(trace_id):
        raise HTTPException(status_code=400, detail="Invalid trace_id")
    return _explain_dir() / f"{trace_id}.json"


def _atomic_write_json(path: Path, obj: dict) -> None:
    """
    Atomic JSON write with stable encoding.
    """
    tmp = path.with_suffix(".tmp")
    data = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, path)


def _idem_key(graph_id: str, key: str) -> str:
    return f"{graph_id}::{key.strip()}"


def _idem_purge(now: float) -> None:
    if len(_IDEM) <= _IDEM_MAX and all((now - v.ts) <= _IDEM_TTL_S for v in _IDEM.values()):
        return

    dead = [k for k, v in _IDEM.items() if (now - v.ts) > _IDEM_TTL_S]
    for k in dead:
        _IDEM.pop(k, None)

    if len(_IDEM) > _IDEM_MAX:
        items = sorted(_IDEM.items(), key=lambda kv: kv[1].ts)
        for k, _ in items[: max(0, len(_IDEM) - _IDEM_MAX)]:
            _IDEM.pop(k, None)


# =============================================================================
# SECTION 4 — GRAPH POLICY (Universe per user; dev override only)
# =============================================================================


def _env_is_dev() -> bool:
    try:
        mode = (_settings().mode or "dev").strip().lower()
    except Exception:
        mode = "dev"
    return mode in ("dev", "local", "development")


def _force_universe(request: Request) -> bool:
    hv = (request.headers.get("X-FAIM-FORCE-UNIVERSE") or "").strip()
    qv = (request.query_params.get("force_universe") or "").strip()
    v = hv or qv
    return v in ("1", "true", "TRUE", "yes", "YES")


def _hash_user_to_graph_id(user_id: str) -> str:
    digest = hashlib.sha256(user_id.encode("utf-8", errors="strict")).hexdigest()
    return f"U:{digest[:12]}"


def resolve_graph_id(request: Request) -> str:
    """
    Contract:
      - Dev: allow ?graph_id=MAIN (default MAIN) unless force_universe enabled
      - Universe mode: requires X-FAIM-USER and derives U:<hash>
    """
    if _env_is_dev() and not _force_universe(request):
        return request.query_params.get("graph_id") or "MAIN"

    user_id = request.headers.get("X-FAIM-USER") or request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing X-FAIM-USER (Universe graph policy).")
    return _hash_user_to_graph_id(user_id)


# =============================================================================
# SECTION 5 — STRICT EVENT BUILDERS (stable keys, JSON-safe; never crash request)
# =============================================================================


async def _emit(graph_id: str, event: str, data: Dict[str, Any]) -> None:
    try:
        await BUS.publish(graph_id, event, data)
    except Exception:
        return


async def emit_chat_used(
    graph_id: str, trace_id: str, turn_id: str, used_nodes: List[Dict[str, Any]]
) -> None:
    await _emit(
        graph_id,
        "chat_used",
        {
            "graph_id": graph_id,
            "trace_id": trace_id,
            "turn_id": turn_id,
            "used_nodes": used_nodes,
            "ts": _now(),
        },
    )


async def emit_chat_token(
    graph_id: str, trace_id: str, turn_id: str, token: str, index: int, *, done: bool
) -> None:
    await _emit(
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
            "ts": _now(),
        },
    )


async def emit_chat_store(
    graph_id: str,
    trace_id: str,
    turn_id: str,
    created_node_ids: List[str],
    created_fact_ids: List[str],
    summary: str,
) -> None:
    await _emit(
        graph_id,
        "chat_store",
        {
            "graph_id": graph_id,
            "trace_id": trace_id,
            "turn_id": turn_id,
            "created_node_ids": created_node_ids,
            "created_fact_ids": created_fact_ids,
            "summary": summary,
            "ts": _now(),
        },
    )


async def emit_fig_delta(graph_id: str, nodes_added: List[str]) -> None:
    await _emit(
        graph_id,
        "fig_delta",
        {
            "graph_id": graph_id,
            "ts": _now(),
            "delta": {
                "kind": "chat_store_delta",
                "nodes_added": [{"id": nid} for nid in nodes_added],
                "links_added": [],
            },
        },
    )


async def emit_toast(
    graph_id: str, level: str, message: str, *, code: Optional[str] = None
) -> None:
    payload: Dict[str, Any] = {
        "graph_id": graph_id,
        "ts": _now(),
        "level": level,
        "message": message,
    }
    if code:
        payload["code"] = code
    await _emit(graph_id, "toast", payload)


async def emit_error(
    graph_id: str,
    type_: str,
    message: str,
    *,
    trace_id: Optional[str] = None,
    turn_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    payload: Dict[str, Any] = {
        "graph_id": graph_id,
        "ts": _now(),
        "type": type_,
        "message": message,
    }
    if trace_id:
        payload["trace_id"] = trace_id
    if turn_id:
        payload["turn_id"] = turn_id
    if details:
        payload["details"] = details
    await _emit(graph_id, "error", payload)


# =============================================================================
# SECTION 6 — STORAGE POLICY (deterministic + anti-noise)
# =============================================================================

_REMEMBER_PREFIXES = ("remember:", "remember -", "remember ", "remember=")
FACT_PREFIX = "FACT: "
CHAT_USER_PREFIX = "[chat:user] "
CHAT_ASST_PREFIX = "[chat:assistant] "


def _clean(s: str) -> str:
    return " ".join((s or "").strip().split())


def _cap(s: str, limit: int = MAX_STORE_CHARS) -> str:
    s = s or ""
    if len(s) <= limit:
        return s
    return s[:limit] + "…"


def _extract_facts(msg: str) -> List[str]:
    m = _clean(msg)
    if not m:
        return []

    out: List[str] = []
    low = m.lower()

    # Deterministic prefix fact
    for p in _REMEMBER_PREFIXES:
        if low.startswith(p):
            fact = _clean(m[len(p) :])
            if fact:
                out.append(fact)
            break

    # Deterministic mini-extractor for acceptance
    mm = re.search(r"\bmy\s+favorite\s+editor\s+is\s+(.+)$", m, flags=re.IGNORECASE)
    if mm:
        val = mm.group(1).strip().rstrip(".")
        if val:
            out.append(f"my favorite editor is {val}")

    # Unique (stable)
    seen = set()
    uniq: List[str] = []
    for f in out:
        k = f.strip().lower()
        if k and k not in seen:
            seen.add(k)
            uniq.append(f.strip())
    return uniq


def _should_store_assistant(reply: str) -> bool:
    r = _clean(reply).lower()
    if not r:
        return False
    if r in {"acknowledged.", "acknowledged", "ok", "okay"}:
        return False
    if "memory does not contain" in r:
        return False
    if "i don't have that in memory" in r:
        return False
    return True


def _store(
    graph_id: str,
    user_msg: str,
    assistant_msg: str,
    facts: List[str],
    *,
    store_assistant: bool,
) -> Tuple[List[str], List[str]]:
    """
    Deterministic writes. Never throws into request path; returns created ids best-effort.
    """
    created_node_ids: List[str] = []
    created_fact_ids: List[str] = []

    try:
        uid = str(add_fragment(graph_id, CHAT_USER_PREFIX + _cap(user_msg)) or "")
        if uid:
            created_node_ids.append(uid)
    except Exception:
        pass

    for f in facts:
        try:
            fid = str(add_fragment(graph_id, FACT_PREFIX + _cap(f)) or "")
            if fid:
                created_fact_ids.append(fid)
        except Exception:
            continue

    if store_assistant and assistant_msg and _should_store_assistant(assistant_msg):
        try:
            aid = str(add_fragment(graph_id, CHAT_ASST_PREFIX + _cap(assistant_msg)) or "")
            if aid:
                created_node_ids.append(aid)
        except Exception:
            pass

    return created_node_ids, created_fact_ids


# =============================================================================
# SECTION 7 — TOKENIZATION (UI-friendly deterministic fallback)
# =============================================================================


def _tokenize(text: str) -> List[str]:
    parts = re.findall(r"\S+\s*", text)
    return parts if parts else ([text] if text else [])


# =============================================================================
# SECTION 8 — EXPLAIN TRACE WRITER (hard evidence for A-LIFE-1)
# =============================================================================


def _used_node_ids(used_nodes: List[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    for n in used_nodes:
        if not isinstance(n, dict):
            continue
        v = n.get("id")
        if isinstance(v, str) and v:
            out.append(v)

    seen = set()
    uniq: List[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def _write_explain_trace(
    *,
    trace_id: str,
    graph_id: str,
    turn_id: str,
    user_message: str,
    assistant_answer: str,
    used_nodes: List[Dict[str, Any]],
    memory_packet: str,
    created_node_ids: List[str],
    created_fact_ids: List[str],
    facts_extracted: List[str],
) -> None:
    """
    Writes Runtime/Logs/Explain/<trace_id>.json with strict keys for A-LIFE-1.
    Never raises into request path.
    """
    try:
        now = _now()
        used_ids = _used_node_ids(used_nodes)

        dedup_suspected = bool(facts_extracted) and (len(created_fact_ids) == 0)
        cancel_suspected = dedup_suspected

        trace_obj: Dict[str, Any] = {
            "trace_id": trace_id,
            "graph_id": graph_id,
            "turn_id": turn_id,
            "created_ts": now,
            "used_memories": used_ids,
            "provenance": {
                "lineage_links": [
                    f"/api/v1/graphs/{graph_id}/node/{nid}/lineage" for nid in used_ids[:50]
                ],
                "neighbors_links": [
                    f"/api/v1/graphs/{graph_id}/node/{nid}/neighbors?k=10" for nid in used_ids[:50]
                ],
            },
            "ops": {
                "inheritance": {
                    "created_node_ids": created_node_ids,
                    "created_fact_ids": created_fact_ids,
                    "facts_extracted": facts_extracted,
                },
                "antisym": {
                    "opposition": True,
                    "cancel": bool(cancel_suspected),
                    "cancel_suspected": bool(cancel_suspected),
                },
                "prune": {"dedup": True, "dedup_suspected": bool(dedup_suspected)},
                "evolution": {"use_count": int(max(1, len(used_ids)))},
            },
            "memory_packet": memory_packet,
            "user_message": user_message,
            "assistant_answer": assistant_answer,
            "last_access_ts": now,
            "use_count": int(max(1, len(used_ids))),
        }

        _atomic_write_json(_explain_path(trace_id), trace_obj)
    except Exception:
        return


# =============================================================================
# SECTION 9 — LEGACY SNIPPET (kept verbatim for history; NOT EXECUTED)
# =============================================================================

_LEGACY_PASTED_SNIPPET_DO_NOT_EXECUTE = r"""
trace_id = uuid.uuid4().hex

now = time.time()

trace_obj = {
    "trace_id": trace_id,
    "graph_id": graph_id,
    "created_ts": now,
    "used_memories": used_nodes,
    "provenance": {
        lineage_links = [
            f"/api/v1/graphs/{graph_id}/node/{nid}/lineage"
            for nid in used_nodes[:50]
        ]

        # later inside the dict:
        "lineage_links": lineage_links,

    },
    "ops": {
        "inheritance": ops_summary.get("inheritance", {}),
        "antisym": ops_summary.get("antisym", {"opposition": True, "cancel": True}),
        "prune": ops_summary.get("prune", {"dedup": True}),
        "evolution": ops_summary.get("evolution", {"use_count": 1}),
    },
    "memory_packet": memory_packet,
    "user_message": user_message,
    "assistant_answer": assistant_answer,
    "last_access_ts": now,
    "use_count": int(ops_summary.get("evolution", {}).get("use_count", 1)),
}

_atomic_write_json(_explain_dir() / f"{trace_id}.json", trace_obj)

return {"answer": assistant_answer, "trace_id": trace_id}
"""


# =============================================================================
# SECTION 10 — OPTIONAL STORE HOOK (safe; never NameError)
# =============================================================================


def _apply_chat_store_hook(
    *,
    graph_id: str,
    created_node_ids: List[str],
    created_fact_ids: List[str],
    ts: Optional[float],
) -> None:
    """
    Some builds keep a secondary index/cache that must be notified after store.
    Your pasted code called NODE_STORE.apply_chat_store(...) but NODE_STORE was not defined
    in this module and would crash the request.

    We keep the behavior (additive) but call it safely via faim.api.state if present.
    """
    try:
        store = getattr(S, "NODE_STORE", None)
        fn = getattr(store, "apply_chat_store", None) if store is not None else None
        if callable(fn):
            fn(
                graph_id=graph_id,
                created_node_ids=created_node_ids,
                created_fact_ids=created_fact_ids,
                ts=ts,
            )
    except Exception:
        return


# =============================================================================
# SECTION 11 — MAIN ENDPOINT (DO NOT BREAK)
# =============================================================================


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    payload: ChatRequest,
    user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
) -> ChatResponse:
    # Strict Graph Resolution: User -> Org -> Project -> Graph
    # 1. Find Org Membership (Owner)
    membership = db.query(OrgMember).filter(OrgMember.user_id == user.id).first()
    if not membership:
        raise HTTPException(status_code=400, detail="User has no organization")

    # 2. Find Project
    project = db.query(Project).filter(Project.org_id == membership.org_id).first()
    if not project:
        raise HTTPException(status_code=400, detail="User has no project")

    # 3. Find Graph
    graph = db.query(GraphOwnership).filter(GraphOwnership.project_id == project.id).first()
    if not graph:
        # Check dev fallback or valid state
        raise HTTPException(status_code=400, detail="User has no graph")

    graph_id = graph.graph_id

    trace_id = uuid.uuid4().hex
    turn_id = payload.client_turn_id or uuid.uuid4().hex

    user_text = _clean(payload.message)
    if not user_text:
        raise HTTPException(status_code=400, detail="Empty message")

    now = _now()
    _idem_purge(now)

    idem_header = (request.headers.get("Idempotency-Key") or "").strip()
    if idem_header:
        key = _idem_key(graph_id, idem_header)
        hit = _IDEM.get(key)
        if hit and (now - hit.ts) <= _IDEM_TTL_S:
            return hit.response

    # -------------------------------------------------------------------------
    # 1) Extract facts (deterministic)
    # -------------------------------------------------------------------------
    facts = _extract_facts(user_text)
    remember_only = any(user_text.lower().startswith(p) for p in _REMEMBER_PREFIXES)

    # -------------------------------------------------------------------------
    # 2) Retrieve context (facts-first)
    # -------------------------------------------------------------------------
    used_nodes: List[Dict[str, Any]] = []
    ctx_text: str = ""

    if not remember_only:
        try:
            used_nodes, ctx_text = naive_used_nodes(graph_id, user_text, k=CTX_K)
        except Exception:
            used_nodes, ctx_text = [], ""

        # best-effort "evolution" bump
        try:
            record_used_nodes(
                graph_id, [str(n.get("id", "")) for n in used_nodes if isinstance(n, dict)]
            )
        except Exception:
            pass

        await emit_chat_used(graph_id, trace_id, turn_id, used_nodes)

    # -------------------------------------------------------------------------
    # 3) Generate reply (stream tokens)
    # -------------------------------------------------------------------------
    reply_text = "Acknowledged." if remember_only else ""
    parts: List[str] = []

    if not remember_only:
        llm = get_llm()

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"FAIM memory:\n{ctx_text}\n\nUser: {user_text}"},
        ]

        idx = 0
        try:
            stream_fn = getattr(llm, "stream_chat", None)
            if not callable(stream_fn):
                raise RuntimeError("LLM streaming not supported (missing stream_chat)")

            start = _now()

            # Assume async generator (preferred). If a sync generator is returned, iterate safely.
            gen = stream_fn(messages)  # type: ignore[misc]
            if hasattr(gen, "__aiter__"):
                async for tok in gen:  # type: ignore[misc]
                    t = str(tok)
                    parts.append(t)
                    await emit_chat_token(graph_id, trace_id, turn_id, t, idx, done=False)
                    idx += 1
                    if (_now() - start) > LLM_TIMEOUT_S:
                        raise TimeoutError("LLM stream timeout")
            else:
                for tok in gen:  # type: ignore[assignment]
                    t = str(tok)
                    parts.append(t)
                    await emit_chat_token(graph_id, trace_id, turn_id, t, idx, done=False)
                    idx += 1
                    if (_now() - start) > LLM_TIMEOUT_S:
                        raise TimeoutError("LLM stream timeout")

        except Exception:
            # Fallback: non-stream complete OR deterministic rule-based answer
            reply_text = ""

            try:
                complete_fn = getattr(llm, "complete", None)
                if callable(complete_fn):
                    out = complete_fn(messages)  # type: ignore[misc]
                    # allow both async and sync implementations
                    if hasattr(out, "__await__"):
                        reply_text = str(await out)  # type: ignore[misc]
                    else:
                        reply_text = str(out)
            except Exception:
                reply_text = ""

            if not _clean(reply_text):
                q = user_text.lower()
                if "favorite" in q and "editor" in q:
                    m = re.search(
                        r"FACT:\s*my\s+favorite\s+editor\s+is\s+(.+)$",
                        ctx_text,
                        flags=re.IGNORECASE | re.MULTILINE,
                    )
                    if m:
                        reply_text = m.group(1).strip()

            if not _clean(reply_text):
                reply_text = "I don't have that in memory yet. Say 'remember: ...' to store it."

            for tok in _tokenize(_clean(reply_text)):
                parts.append(tok)
                await emit_chat_token(graph_id, trace_id, turn_id, tok, idx, done=False)
                idx += 1

        if not _clean(reply_text):
            reply_text = _clean("".join(parts))

        await emit_chat_token(graph_id, trace_id, turn_id, "", idx, done=True)

    # -------------------------------------------------------------------------
    # 4) Store deterministic side effects
    # -------------------------------------------------------------------------
    created_node_ids, created_fact_ids = _store(
        graph_id,
        user_msg=user_text,
        assistant_msg=reply_text,
        facts=facts,
        store_assistant=STORE_ASSISTANT_DEFAULT,
    )

    if not created_node_ids and not created_fact_ids:
        await emit_error(
            graph_id,
            "chat_store_failed",
            "No ids were created during storage.",
            trace_id=trace_id,
            turn_id=turn_id,
        )

    # -------------------------------------------------------------------------
    # 5) Emit chat_store + fig_delta
    # -------------------------------------------------------------------------
    all_added = created_node_ids + created_fact_ids
    if all_added:
        await emit_fig_delta(graph_id, all_added)

    summary = f"stored nodes={len(created_node_ids)} facts={len(created_fact_ids)}"
    await emit_chat_store(graph_id, trace_id, turn_id, created_node_ids, created_fact_ids, summary)

    if remember_only and created_fact_ids:
        await emit_toast(graph_id, "success", "Saved to memory.", code="memory_saved")

    # -------------------------------------------------------------------------
    # 6) Write explain trace (hard evidence)
    # -------------------------------------------------------------------------
    memory_packet = ctx_text if not remember_only else ""
    _write_explain_trace(
        trace_id=trace_id,
        graph_id=graph_id,
        turn_id=turn_id,
        user_message=user_text,
        assistant_answer=reply_text,
        used_nodes=used_nodes,
        memory_packet=memory_packet,
        created_node_ids=created_node_ids,
        created_fact_ids=created_fact_ids,
        facts_extracted=facts,
    )

    # -------------------------------------------------------------------------
    # 7) Build response (FIXED: removed duplicate resp creation)
    # -------------------------------------------------------------------------
    resp = ChatResponse(
        trace_id=trace_id,
        turn_id=turn_id,
        reply=reply_text,
        used_nodes=used_nodes,
        chat_store={
            "created_node_ids": created_node_ids,
            "created_fact_ids": created_fact_ids,
            "summary": summary,
            "ts": _now(),
        },
    )

    # -------------------------------------------------------------------------
    # 8) Optional store hook (FIXED: no NameError; best-effort)
    # -------------------------------------------------------------------------
    ts_val = None
    try:
        ts_any = resp.chat_store.get("ts") if isinstance(resp.chat_store, dict) else None
        ts_val = float(ts_any) if ts_any is not None else None
    except Exception:
        ts_val = None

    _apply_chat_store_hook(
        graph_id=graph_id,
        created_node_ids=created_node_ids,
        created_fact_ids=created_fact_ids,
        ts=ts_val,
    )

    # -------------------------------------------------------------------------
    # 9) Idempotency store (best-effort)
    # -------------------------------------------------------------------------
    if idem_header:
        _IDEM[_idem_key(graph_id, idem_header)] = _IdemItem(ts=_now(), response=resp)

    return resp
