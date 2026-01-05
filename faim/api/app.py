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

from faim.api.auth import allow_dev_mode
from faim.api.benchmarks import router as benchmarks_router
from faim.api.chat import router as chat_router
from faim.api.events import BUS, contract_chunk, gap_chunk, parse_last_event_id
from faim.api.evolution_status import get_status
from faim.api.explain import router as explain_router
from faim.api.graphs import router as graphs_router
from faim.api.keys import router as keys_router
from faim.api.models import API_PREFIX
from faim.api.watchers import start_watchers
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
    benchmarks_dir = Path(
        os.getenv("FAIM_BENCHMARKS_DIR", str(root / "Runtime" / "Benchmarks"))
    ).resolve()
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
                Path(getattr(s, "benchmarks_dir", benchmarks_dir)).mkdir(
                    parents=True, exist_ok=True
                )
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

    from faim.api.events import set_main_loop

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

from faim.api.rate_limiter import check_rate_limit

app.include_router(chat_router, prefix=API_PREFIX)
app.include_router(keys_router, prefix=API_PREFIX)
app.include_router(
    graphs_router, prefix=API_PREFIX, dependencies=[Depends(check_rate_limit)]
)  # Rate Limited
app.include_router(benchmarks_router, prefix=API_PREFIX)
app.include_router(explain_router, prefix="/api/v1")

# =============================================================================
# SECTION 4 — PRODUCT CONTRACT — UNIVERSE GRAPH ID (locked behavior)
# =============================================================================


def _is_dev_mode() -> bool:
    mode = str(getattr(settings, "mode", "dev")).strip().lower().replace("-", "_")
    return mode in ("dev", "development", "local", "core_dev", "coredev") or mode.endswith("_dev")


def _hash_user_to_graph_id(user_id: str) -> str:
    digest = hashlib.sha256(user_id.encode("utf-8", errors="strict")).hexdigest()
    return f"U:{digest[:12]}"


# -----------------------------------------------------------------------------
# DEV SIMULATION SWITCH: Force Universe policy via header OR query param
# -----------------------------------------------------------------------------


def _force_universe(request: Request) -> bool:
    """
    DEV-only helper to simulate PROD Universe graph derivation.

    Supported:
      - Header: X-FAIM-FORCE-UNIVERSE: 1|true|yes
      - Query:  ?force_universe=1|true|yes
    """
    hv = (request.headers.get("X-FAIM-FORCE-UNIVERSE") or "").strip()
    qv = (request.query_params.get("force_universe") or "").strip()
    v = hv or qv
    return v in ("1", "true", "TRUE", "yes", "YES")


def resolve_universe_graph_id(request: Request, explicit_graph_id: Optional[str]) -> str:
    """
    Contract:
      - Dev: allow explicit graph_id (query param) unless force_universe enabled
      - Prod/Universe: requires user identity header; derives U:<hash>
    """
    if _is_dev_mode() and not _force_universe(request):
        dev_gid = explicit_graph_id
        if dev_gid:
            return dev_gid
        env_gid = os.getenv("FAIM_DEV_GRAPH_ID")
        return env_gid if env_gid else "MAIN"

    user_id = request.headers.get("X-FAIM-USER") or request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail=(
                "Missing user identity header (X-FAIM-USER). "
                "Universe graph_id is derived per user in production."
            ),
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
    auth: bool = Depends(allow_dev_mode),
) -> StreamingResponse:
    # require_api_key(request) -> Replaced by Depends(verify_graph_access)
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
# SECTION 7B — EVOLUTION STATUS
# =============================================================================


@app.get(f"{API_PREFIX}/evolution/status")
async def evolution_status(
    request: Request,
    graph_id: str | None = Query(None),
    auth: bool = Depends(allow_dev_mode),
):
    # require_api_key(request)
    gid = resolve_universe_graph_id(request, graph_id)
    status = get_status(gid)
    if status is None:
        return {"graph_id": gid, "status": "idle", "runs": 0}
    status_label = "error" if status.get("last_error") else "ok"
    return {**status, "status": status_label}


# =============================================================================
# SECTION 7C — METRICS EXPORT (JSON / PROMETHEUS)
# =============================================================================


@app.get(f"{API_PREFIX}/metrics/export")
async def metrics_export(
    request: Request,
    graph_id: str | None = Query(None),
    format: str = Query("json"),
    auth: bool = Depends(allow_dev_mode),
):
    # require_api_key(request)
    gid = resolve_universe_graph_id(request, graph_id)
    try:
        from faim.engine.interface import get_metrics as _engine_get_metrics  # type: ignore

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

from faim.api.router_admin import router as admin_router
from faim.api.router_auth import router as auth_router
from faim.api.router_billing import router as billing_router
from faim.api.router_control import router as control_router
from faim.api.router_keys_v2 import router as keys_v2_router
from faim.api.router_lifecycle import router as lifecycle_router
from faim.api.router_ops import router as ops_router
from faim.api.router_realtime import router as realtime_router
from faim.api.router_storage import router as storage_router
from faim.api.router_stripe import router as stripe_router
from faim.api.router_tenant import router as tenant_router
from faim.api.router_user import router as user_router

app.include_router(control_router)
app.include_router(keys_v2_router)
app.include_router(storage_router, prefix="/api/v1")
app.include_router(lifecycle_router)
app.include_router(billing_router)
app.include_router(stripe_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(ops_router, prefix="/api")
app.include_router(realtime_router, prefix="/api/v1")
app.include_router(tenant_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")

# =============================================================================
# SECTION 10 — RATE LIMITING (Redis-backed)
# =============================================================================
try:
    from faim.api.rate_limiter import setup_rate_limiting

    setup_rate_limiting(app)
except ImportError:
    pass  # Rate limiting not available

# Add usage tracking middleware (optional, can be disabled)
try:
    from faim.api.usage_middleware import UsageTrackingMiddleware

    app.add_middleware(UsageTrackingMiddleware, enabled=True)
except Exception as e:
    print(f"[FAIM] Usage tracking middleware disabled: {e}")

# Add token tracking middleware (real-time usage tracking)
try:
    from faim.api.token_tracker import TokenTrackingMiddleware

    app.add_middleware(TokenTrackingMiddleware)
    print("[FAIM] Token tracking middleware enabled")
except Exception as e:
    print(f"[FAIM] Token tracking middleware disabled: {e}")

# Add usage SSE router for real-time updates
try:
    from faim.api.router_usage import router as usage_router

    app.include_router(usage_router, prefix="/api/v1")
    print("[FAIM] Usage SSE router mounted at /api/v1/usage")
except Exception as e:
    print(f"[FAIM] Usage router disabled: {e}")


# Basic DB session test on startup (optional, logs connection status)
@app.on_event("startup")
def _db_check():
    try:
        from faim.db import SessionLocal

        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        print("[FAIM DB] Connection successful.")
    except Exception as e:
        print(f"[FAIM DB] Connection WARNING: {e}")


# =============================================================================
# SECTION 11 — AGI FEATURES (P3+ Extensions)
# =============================================================================
# These are NEW modules that extend functionality without modifying core code.
# Each is wrapped in try/except for safety - if import fails, core app continues.

# Real-time evolution stream (SSE)
try:
    from faim.api.router_evolution_stream import router as evolution_stream_router

    app.include_router(evolution_stream_router, prefix="/api/v1")
    print("[FAIM] Evolution stream router mounted at /api/v1/evolution")
except Exception as e:
    print(f"[FAIM] Evolution stream router skipped: {e}")

# Graph filtering (topic/date/relationship)
try:
    from faim.api.graph_filters import router as graph_filters_router

    app.include_router(graph_filters_router, prefix="/api/v1")
    print("[FAIM] Graph filters router mounted at /api/v1/graphs")
except Exception as e:
    print(f"[FAIM] Graph filters router skipped: {e}")

# Batch Upload with Progress (AGI Feature #1)
try:
    from faim.api.batch_upload import router as batch_upload_router

    app.include_router(batch_upload_router, prefix="/api/v1")
    print("[FAIM] Batch upload router mounted at /api/v1/batch")
except Exception as e:
    print(f"[FAIM] Batch upload router skipped: {e}")

# Cross-document Inference (AGI Feature #2)
try:
    from faim.core.inference import router as inference_router

    app.include_router(inference_router, prefix="/api/v1")
    print("[FAIM] Inference router mounted at /api/v1/graphs")
except Exception as e:
    print(f"[FAIM] Inference router skipped: {e}")

# Semantic Clustering (AGI Feature #3)
try:
    from faim.core.clustering import router as clustering_router

    app.include_router(clustering_router, prefix="/api/v1")
    print("[FAIM] Clustering router mounted at /api/v1/graphs")
except Exception as e:
    print(f"[FAIM] Clustering router skipped: {e}")

# Hidden Insights Discovery (AGI Feature #4)
try:
    from faim.core.insights import router as insights_router

    app.include_router(insights_router, prefix="/api/v1")
    print("[FAIM] Insights router mounted at /api/v1/graphs")
except Exception as e:
    print(f"[FAIM] Insights router skipped: {e}")

# Image Understanding (AGI Feature #5)
try:
    from faim.api.image_processor import router as image_router

    app.include_router(image_router, prefix="/api/v1")
    print("[FAIM] Image processor router mounted at /api/v1/images")
except Exception as e:
    print(f"[FAIM] Image processor router skipped: {e}")

# Self-Inventing Concepts (AGI Feature #6)
try:
    from faim.core.invention import router as invention_router

    app.include_router(invention_router, prefix="/api/v1")
    print("[FAIM] Invention router mounted at /api/v1/graphs")
except Exception as e:
    print(f"[FAIM] Invention router skipped: {e}")
