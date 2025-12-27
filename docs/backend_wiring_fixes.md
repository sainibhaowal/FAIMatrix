# Backend Wiring Fixes

This list records the backend wiring fixes applied to align the runtime paths,
SSE metrics, and optional acceleration hooks.

## Storage path alignment
- `faim/storage/sqlite_store.py`: `DEFAULT_DB_PATH` now respects `FAIM_DB_PATH`
  and `FAIM_ROOT`, so the engine and API can share the same SQLite DB.
- `faim/api/state.py`: default DB path now points to the same storage path as
  the engine (Runtime/Storage), avoiding the split DB issue.

## SSE metrics + FIG watcher wiring
- `faim/api/events.py`: added `active_graph_ids()` so background tasks can
  target only live graph channels.
- `faim/api/watchers.py`:
  - FIG watcher now emits valid `fig_delta` payloads via `emit_fig_delta`.
  - Targets active graph IDs by default (Universe-compatible), with optional
    override via `FAIM_FIG_WATCH_GRAPH_ID`.
  - Added periodic metrics emission via `emit_metrics` using
    `FAIM_METRICS_SSE_INTERVAL` (default 2.5s).

## Core metrics wiring
- `faim/engine/interface.py`:
  - Uses `faim.core.metrics.compression_ratio` as a fallback when raw-byte CR
    is unavailable.
  - Optional redundancy computation via
    `FAIM_ENABLE_CORE_REDUNDANCY=1`.

## Optional GPU backend wiring
- `faim/speed/vector_bank.py`:
  - Optional P4.5 GPU backend wiring for top‑k queries via
    `FAIM_USE_GPU_BACKEND=1`.
  - GPU backend tuning via:
    - `FAIM_GPU_DEVICE` (default `cuda`)
    - `FAIM_GPU_MAX_MIRROR_BYTES` (override auto mirror budget)
    - `FAIM_GPU_STREAM_CHUNK_ROWS` (override auto stream chunk size)

## GPU auto-tuning + UI badge
- `faim/speed/gpu_backend.py`:
  - Auto mirror budget based on free VRAM.
  - Auto streaming chunk size based on VRAM + embedding dimension.
- `faim/api/app.py`: health endpoint now reports GPU status.
- `frontend/src/components/shell/TopBar.tsx`: GPU active badge + status in health menu.
