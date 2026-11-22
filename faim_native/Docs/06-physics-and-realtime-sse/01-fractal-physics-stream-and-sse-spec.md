# Fractal Physics Telemetry Stream & Real-Time SSE Spec

## 1. Scope
Documents the mathematical invariants, telemetry time-series endpoint, real-time SSE streaming contract, and frontend chart/timeline consumers across:
- **Fractal Physics Core**: `faim_native/core/metrics/fractal_physics.py`
- **Physics Stream API**: `faim_native/api/routers/evolve.py` (`GET /api/v1/evolve/physics/stream`, `_build_physics_stream`)
- **SSE & Journal API**: `faim_native/api/routers/events.py`, `faim_native/store/pg/repos/event_repo.py`
- **Next.js Streaming Proxy**: `frontend/src/app/api/v1/stream/route.ts`
- **Frontend Chart & Live Consumer**: `frontend/src/components/evolution/EvolutionPhysicsChart.tsx`, `frontend/src/app/(admin)/dashboard/evolution/page.tsx`

---

## 2. Deterministic Fractal Invariants (`fractal_physics.py`)
FAIM computes deterministic graph diagnostics without ML models or randomness (scaling constant $\phi = \frac{1+\sqrt{5}}{2}$, $s = 1/\phi$):
- **Fractal Dimension ($\hat{D}$)**: Multi-scale box-covering dimension across $\epsilon \in \{0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0\}$.
- **Entropy ($\hat{H}$)**: 20-bin histogram Shannon entropy of representation distribution.
- **Evolution Pressure ($\hat{\lambda}$)**: Weighted pressure over novelty, redundancy, and entropy (`lambda_weights = (0.50, 0.30, 0.20)`).
- **Redundancy ($R$) & Novelty ($N$)**: Structural duplication vs. novel surface rate (with effective novelty adjustment `_effective_novelty_n(R, N_raw, H)` in `evolve.py`).
- **Energy ($E$)**: Lyapunov stability potential derived from $R$, $1 - N$, and $\hat{\lambda}$.
- **Compression Ratio ($CR$)**: Ratio of compressed macro/merged representation relative to raw atom volume.

---

## 3. Physics Stream API (`GET /api/v1/evolve/physics/stream`)
`_build_physics_stream` builds chronological `PhysicsStreamPoint` telemetry from journal events (`DIAGNOSTICS_SNAPSHOT`, `EVOLUTION_COMPLETE`, `EVOLUTION_SKIPPED`, `EVOLUTION_INVENTION_SUMMARY`, `EVOLUTION_INVENTION_SYNTHESIS_SUMMARY`, `INVENT_MACRO_NODE`) plus the latest `GraphDiagnosticsCacheModel` row (`LIVE_CACHE` when newer or changed).

### Response Payload (`PhysicsStreamResponse`)
- **`points[]`**: Chronological frames containing `seq`, UTC ISO-8601 `ts`, `label` (`v<ver>` or `#<seq>`), `cycle_version`, `action` (`INVENT` | `MERGE` | `CYCLE` | `CONVERGED` | `SNAPSHOT` | `LIVE_CACHE`), all 7 invariants, and `nodes_count` / `macros_count` / `merges_count` / `edges_count`.
- **`current` & `deltas`**: Latest invariant values paired with cycle-to-cycle $\Delta$ from the preceding frame.
- **`thresholds`**: `tau_R: 0.15`, `tau_N: 0.25`, `tau_E: 0.55`, `lambda_critical: 0.05`, `d_hat_target: 2.0`.
- **`evals`**:
  - `regime`: `HIGH_PRESSURE_BIFURCATION` ($\hat{\lambda} > 0.20$), `REDUNDANCY_COMPRESSION` ($R > 0.20$), `INVENTION_READY` ($\hat{\lambda} \ge 0.05$ and `macro_total == 0`), or `LYAPUNOV_CONVERGENT`.
  - `lyapunov_stable`: `pressure_lambda <= 0.25`.
  - `manifold_health_score` ($0..100\%$) and `invention_readiness` ($0..100\%$).

### `EvolutionPhysicsChart.tsx`
- Renders the System Regime banner, 7 interactive KPI cards with $\Delta$ indicators and threshold bars, multi-series Recharts `AreaChart` with reference threshold lines ($\tau_R, \tau_E, \lambda_{\text{crit}}$), crosshair tooltip, and "Live Telemetry Frames" table.

---

## 4. Real-Time SSE Streaming & Tail API

### Backend Event Journal & SSE (`events.py` & `event_repo.py`)
- **`GET /api/v1/events`**:
  - Supports `tail=true` (`EventRepo.list_tail`), `after_seq`, `limit`, and comma-separated `kinds` filtering (`EventRepo.get_by_seq(..., kinds=...)`).
  - Handles FastAPI `Query(...)` parameter objects safely when invoked directly in unit tests.
- **`GET /api/v1/events/stream`** (`_event_generator`):
  - Enforces strict `tenant_id` scoping (`Depends(get_tenant_id)`).
  - Supports **`after_seq=-1` tail mode**: resolves current `EventRepo.get_max_seq(session, graph_id)` and immediately emits an `event: ready` handshake frame with `{graph_id, tenant_id, last_seq, ts}`.
  - Emits each new event as `id: <seq>`, `event: <kind>`, `data: {seq, id, kind, ts, payload}` and sends `event: ping` heartbeats every `HEARTBEAT_INTERVAL_SECONDS` (`15s`).

### Next.js Proxy & Frontend Consumer
- **`frontend/src/app/api/v1/stream/route.ts`**: Node.js streaming passthrough (`TransformStream`) forwarding `graph_id`, `after_seq` (including `-1`), `Authorization`, `X-FAIM-USER`, and `X-FAIM-KEY` headers to `/api/v1/events/stream`.
- **`frontend/src/app/(admin)/dashboard/evolution/page.tsx`**: `connectSse` maintains a persistent `AbortController`-managed `fetch` reader to `/api/v1/stream?graph_id=...&after_seq=<lastSeq>`, appending live events to the timeline (`MAX_TIMELINE_EVENTS = 260`) and refreshing flow + physics telemetry automatically when `ready` or mutation/evolve events arrive (with 5s `pollOnce` fallback when disconnected).
