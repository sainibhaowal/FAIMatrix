# =============================================================================
# FAIM — GOLD EDITION (COMMERCIAL / INDUSTRY PRODUCTION)
# =============================================================================
# File: faim/api/app.py
#
# PURPOSE (LOCKED CONTRACT)
#   - Product Contract Lock: Universe graph_id per user (frontend never types it)
#   - SSE Hardening: strict JSON, keepalive ping, bounded queues, reconnect safety
#   - Pylance-safe typing + correct watcher startup (no awaiting None)
#
# HARD RULES
#   - Do NOT remove endpoints or change their paths.
#   - Fixes must be additive + hardened only (no API damage).
#   - Startup must never crash if watchers fail (best-effort).
# =============================================================================

from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path
from typing import Any, Callable, Optional, cast

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

from faim.api.services.benchmarks import router as benchmarks_router
from faim.api.services.events import BUS, contract_chunk, gap_chunk, parse_last_event_id
from faim.api.services.graphs import router as graphs_router
from faim.api.services.models import API_PREFIX
from faim.api.services.watchers import start_watchers
from faim.config import FaimSettings

# =============================================================================
# SECTION 0 — SETTINGS LOADER (Pylance-safe + backwards compatible)
# =============================================================================


def build_settings() -> FaimSettings:
    """
    Builds FaimSettings in a way that survives constructor signature differences.

    Your project may expose:
      - FaimSettings.from_env()   (preferred)
      - OR a required-args constructor:
          FaimSettings(
            mode: str, root: Path, cache_dir: Path, benchmarks_dir: Path, uploads_dir: Path
        )


    This builder:
      - keeps repo-root stable
      - ensures runtime dirs exist
      - never raises in import-time (we fall back in a safe way)
    """
    default_root = Path(__file__).resolve().parents[2]  # .../FAIM
    root = Path(os.getenv("FAIM_ROOT", str(default_root))).resolve()

    mode = os.getenv("FAIM_MODE", os.getenv("ENV", "dev")).strip().lower()

    cache_dir = Path(os.getenv("FAIM_CACHE_DIR", str(root / "Runtime" / "Cache"))).resolve()
    benchmarks_dir = Path(os.getenv("FAIM_BENCHMARKS_DIR", str(root / "Runtime" / "Benchmarks"))).resolve()
    uploads_dir = Path(os.getenv("FAIM_UPLOADS_DIR", str(root / "Runtime" / "Uploads"))).resolve()

    cache_dir.mkdir(parents=True, exist_ok=True)
    benchmarks_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # Prefer from_env if present; otherwise use ctor.
    from_env_any: Any = getattr(FaimSettings, "from_env", None)
    if callable(from_env_any):
        try:
            from_env = cast(Callable[[], FaimSettings], from_env_any)
            s = from_env()

            # Best-effort ensure dirs even if from_env doesn't create them
            try:
                Path(getattr(s, "cache_dir", cache_dir)).mkdir(parents=True, exist_ok=True)
                Path(getattr(s, "benchmarks_dir", benchmarks_dir)).mkdir(parents=True, exist_ok=True)
                Path(getattr(s, "uploads_dir", uploads_dir)).mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

            return s
        except Exception:
            # fall through to ctor
            pass

    return FaimSettings(
        mode=mode,
        root=root,
        cache_dir=cache_dir,
        benchmarks_dir=benchmarks_dir,
        uploads_dir=uploads_dir,
    )


# FIXED: use ONE settings source (no duplicate conflicting instantiation)
settings = build_settings()

# =============================================================================
# SECTION 1 — FASTAPI APP (contract stable)
# =============================================================================

app = FastAPI(title="FAIM API", version="1.0.0")


# Capture event loop for sync-to-async SSE event dispatch
@app.on_event("startup")
async def startup_event():
    import asyncio

    from faim.api.services.events import set_main_loop

    set_main_loop(asyncio.get_running_loop())


# =============================================================================
# SECTION 2 — CORS (hardened + tolerant of multiple settings shapes)
# =============================================================================


def _as_list(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v if x is not None]
    # allow comma-separated env style
    s = str(v).strip()
    if not s:
        return []
    if "," in s:
        return [x.strip() for x in s.split(",") if x.strip()]
    return [s]


cors_origins = _as_list(getattr(settings, "CORS_ORIGINS", None))
if not cors_origins:
    cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# SECTION 3 — ROUTERS (do not change paths)
# =============================================================================

from faim.api.middleware.rate_limiter import check_rate_limit
from faim.api.routers.memories import router as memories_router

app.include_router(memories_router, prefix=API_PREFIX)  # Memory management
app.include_router(graphs_router, prefix=API_PREFIX, dependencies=[Depends(check_rate_limit)])  # Rate Limited
app.include_router(benchmarks_router, prefix=API_PREFIX)


# =============================================================================
# SECTION 4 — PRODUCT CONTRACT — UNIVERSE GRAPH ID (locked behavior)
# =============================================================================


# -----------------------------------------------------------------------------
# UNIVERSE GRAPH ID RESOLUTION (STRICT PRODUCTION)
# -----------------------------------------------------------------------------


def _hash_user_to_graph_id(user_id: str) -> str:
    digest = hashlib.sha256(user_id.encode("utf-8", errors="strict")).hexdigest()
    return f"U:{digest[:12]}"


def resolve_universe_graph_id(request: Request, explicit_graph_id: Optional[str]) -> str:
    """
    Contract (Strict Production):
      - Universes are ALWAYS derived from the User ID.
      - Requires strict 'X-FAIM-USER' identity header.
    """
    user_id = request.headers.get("X-FAIM-USER") or request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail=("Missing user identity header (X-FAIM-USER). Universe graph_id is derived per user in production."),
        )
    return _hash_user_to_graph_id(str(user_id))


# =============================================================================
# SECTION 5 — STARTUP (WATCHERS — DO NOT AWAIT; BEST-EFFORT)
# =============================================================================


@app.on_event("startup")
def _startup() -> None:
    """
    start_watchers(loop) -> None (per your code)
    - Must never crash app startup if watchers fail.
    - Must not 'await' a None-returning function.
    """
    try:
        # Works in uvicorn; safe fallback is get_event_loop in older contexts
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        # Start watchers best-effort; never raise
        start_watchers(loop)

        # Wire core events to API BUS (P3 Evolution)
        try:
            from faim.api.services.events import emit_evolution_sync
            from faim.core.events import subscribe_evolution_event

            subscribe_evolution_event(emit_evolution_sync)
        except Exception as e:
            print(f"[FAIM STARTUP] Failed to wire evolution events: {e}")
    except Exception as exc:
        # Minimal visibility; do not leak secrets; do not crash startup
        print(f"[FAIM STARTUP] watchers_failed: {type(exc).__name__}: {exc}")


# =============================================================================
# SECTION 6 — SSE STREAM (HARDENED; stable endpoint)
# =============================================================================


@app.get(f"{API_PREFIX}/stream")
async def stream(
    request: Request,
    graph_id: Optional[str] = None,
) -> StreamingResponse:
    # Strict Resolution
    gid = resolve_universe_graph_id(request, graph_id)

    keepalive = int(getattr(settings, "SSE_KEEPALIVE_SECONDS", 15) or 15)
    keepalive = max(5, min(120, keepalive))

    # parse_last_event_id expects headers dict; keep compatibility
    last_id = parse_last_event_id(dict(request.headers))

    # Initial contract (client boot payload)
    initial = contract_chunk(gid, universe_label="Universe")
    gap = gap_chunk(gid, last_id) if last_id is not None else None

    async def gen():
        async def disconnected() -> bool:
            try:
                return await request.is_disconnected()
            except Exception:
                return True

        # BUS.stream is the source-of-truth for SSE framing/hardening
        async for chunk in BUS.stream(
            gid,
            last_event_id=last_id,
            keepalive_seconds=keepalive,
            disconnected=disconnected,
            send_initial=initial,
            gap_event=gap,
        ):
            yield chunk

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "Content-Type": "text/event-stream",
    }
    return StreamingResponse(gen(), headers=headers, media_type="text/event-stream")


# =============================================================================
# SECTION 7 — HEALTH (stable)
# =============================================================================


@app.get(f"{API_PREFIX}/health")
async def health():
    enabled = os.getenv("FAIM_USE_GPU_BACKEND", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "y",
        "on",
    )
    device = (os.getenv("FAIM_GPU_DEVICE") or "cuda").strip() or "cuda"
    available = False
    mem_free = None
    mem_total = None
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():  # type: ignore[union-attr]
            available = True
            try:
                free, total = torch.cuda.mem_get_info(device)  # type: ignore[arg-type]
            except Exception:
                free, total = torch.cuda.mem_get_info()  # type: ignore[assignment]
            mem_free = int(free)
            mem_total = int(total)
    except Exception:
        pass

    return {
        "status": "ok",
        "mode": getattr(settings, "mode", "unknown"),
        "gpu": {
            "enabled": enabled,
            "available": available,
            "device": device,
            "mem_free_bytes": mem_free,
            "mem_total_bytes": mem_total,
        },
    }


# =============================================================================
# SECTION 7B — EVOLUTION STATUS (REMOVED - use SSE events instead)


# =============================================================================
# SECTION 7C — METRICS EXPORT (JSON / PROMETHEUS)
# =============================================================================


@app.get(f"{API_PREFIX}/metrics/export")
async def metrics_export(
    request: Request,
    graph_id: str | None = Query(None),
    format: str = Query("json"),
):
    gid = resolve_universe_graph_id(request, graph_id)
    try:
        from faim.api.adapters.interface import get_metrics as _engine_get_metrics  # type: ignore

        m = _engine_get_metrics(gid) or {}
    except Exception:
        m = {}

    if format.lower() in ("prom", "prometheus", "text"):

        def _line(name: str, value: float) -> str:
            return f'{name}{{graph_id="{gid}"}} {value}'

        lines = [
            _line("faim_node_count", float(m.get("node_count", 0))),
            _line("faim_edge_count", float(m.get("edge_count", 0))),
            _line("faim_compression_ratio", float(m.get("compression_ratio", 0.0))),
            _line("faim_redundancy", float(m.get("redundancy", 0.0))),
            _line("faim_drift", float(m.get("drift", 0.0))),
            _line("faim_retrieve_p50_ms", float(m.get("retrieve_p50_ms", 0.0))),
            _line("faim_retrieve_p95_ms", float(m.get("retrieve_p95_ms", 0.0))),
            _line("faim_raw_bytes", float(m.get("raw_bytes", 0.0))),
            _line("faim_vector_bytes", float(m.get("faim_bytes", 0.0))),
        ]
        return PlainTextResponse("\n".join(lines) + "\n")

    return JSONResponse({"graph_id": gid, "metrics": m})


# =============================================================================
# SECTION 8 — GLOBAL ERROR HANDLER (minimal leakage)
# =============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # keep minimal, do not leak secrets
    print(f"[FAIM ERROR] {type(exc).__name__}: {exc}")
    return JSONResponse(status_code=500, content={"error": "internal_server_error"})


# =============================================================================
# SECTION 9 — CONTROL PLANE & DB (Phase 1)
# =============================================================================

# from faim.api.routers.admin import router as admin_router
from faim.api.auth.keys import router as keys_v2_router
from faim.api.auth.user import router as user_router
from faim.api.routers.auth import router as auth_router
from faim.api.routers.billing import router as billing_router
from faim.api.routers.control import router as control_router
from faim.api.routers.journal import router as journal_router
from faim.api.routers.ops import router as ops_router
from faim.api.routers.storage import router as storage_router
from faim.api.routers.stripe import router as stripe_router


app.include_router(control_router)
app.include_router(journal_router, prefix="/api/v1")
app.include_router(keys_v2_router, prefix="/api/v1")
app.include_router(storage_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api")
app.include_router(stripe_router, prefix="/api")
# app.include_router(admin_router, prefix="/api")  # DISABLED for strict isolation
app.include_router(ops_router, prefix="/api")

app.include_router(user_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")

# =============================================================================
# SECTION 10 — RATE LIMITING (Redis-backed)
# =============================================================================
try:
    from faim.api.middleware.rate_limiter import setup_rate_limiting

    setup_rate_limiting(app)
except ImportError:
    pass  # Rate limiting not available

# Add usage tracking middleware (optional, can be disabled)
try:
    from faim.api.middleware.usage_middleware import UsageTrackingMiddleware

    app.add_middleware(UsageTrackingMiddleware, enabled=True)
except Exception as e:
    print(f"[FAIM] Usage tracking middleware disabled: {e}")

# Token tracking middleware removed - replaced with usage_service.py

# Add usage SSE router for real-time updates
try:
    from faim.api.routers.usage import router as usage_router

    app.include_router(usage_router, prefix="/api/v1")
    print("[FAIM] Usage SSE router mounted at /api/v1/usage")
except Exception as e:
    print(f"[FAIM] Usage router disabled: {e}")


# Basic DB session test on startup (optional, logs connection status)
@app.on_event("startup")
def _db_check():
    try:
        from faim.config.database import SessionLocal, init_db

        # Create tables if not exist (critical for recovery after wipe)
        init_db()

        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        print("[FAIM DB] Connection successful. Tables initialized.")
    except Exception as e:
        print(f"[FAIM DB] Connection WARNING: {e}")


# =============================================================================
# SECTION 11 — AGI FEATURES (P3+ Extensions)
# =============================================================================
# These are NEW modules that extend functionality without modifying core code.
# Each is wrapped in try/except for safety - if import fails, core app continues.

# Real-time evolution stream (SSE)
# Real-time evolution stream (SSE) - REMOVED (Redundant: uses main EventBus now)

# Graph filtering (topic/date/relationship)
try:
    from faim.api.services.graph_filters import router as graph_filters_router

    app.include_router(graph_filters_router, prefix="/api/v1")
    print("[FAIM] Graph filters router mounted at /api/v1/graphs")
except Exception as e:
    print(f"[FAIM] Graph filters router skipped: {e}")

# Batch Upload with Progress (AGI Feature #1)
try:
    from faim.api.services.batch_upload import router as batch_upload_router

    app.include_router(batch_upload_router, prefix="/api/v1")
    print("[FAIM] Batch upload router mounted at /api/v1/batch")
except Exception as e:
    print(f"[FAIM] Batch upload router skipped: {e}")

# Cross-document Inference (AGI Feature #2)
try:
    from faim.analytics.inference import router as inference_router

    app.include_router(inference_router, prefix="/api/v1")
    print("[FAIM] Inference router mounted at /api/v1/graphs")
except Exception as e:
    print(f"[FAIM] Inference router skipped: {e}")

# Semantic Clustering (AGI Feature #3)
try:
    from faim.analytics.clustering import router as clustering_router

    app.include_router(clustering_router, prefix="/api/v1")
    print("[FAIM] Clustering router mounted at /api/v1/graphs")
except Exception as e:
    print(f"[FAIM] Clustering router skipped: {e}")

# Hidden Insights Discovery (AGI Feature #4)
try:
    from faim.analytics.insights import router as insights_router

    app.include_router(insights_router, prefix="/api/v1")
    print("[FAIM] Insights router mounted at /api/v1/graphs")
except Exception as e:
    print(f"[FAIM] Insights router skipped: {e}")

# Image Understanding (AGI Feature #5) - REMOVED (requires LLM API)

# Self-Inventing Concepts (AGI Feature #6)
try:
    from faim.core.invention import router as invention_router

    app.include_router(invention_router, prefix="/api/v1")
    print("[FAIM] Invention router mounted at /api/v1/graphs")
except Exception as e:
    print(f"[FAIM] Invention router skipped: {e}")
