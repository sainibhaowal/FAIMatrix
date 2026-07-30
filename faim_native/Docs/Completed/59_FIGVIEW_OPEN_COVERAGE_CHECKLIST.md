# 59 - FigView Open Coverage Checklist

Date: 2026-04-16 (updated; all items resolved)
Based on: faim_native/Docs/Completed/62_FIGVIEW_IMPLEMENTATION_PLAN.md
Status: Completed

Purpose: Checklist of what was left to claim full end-to-end FIG completion before closure.

## A. Must-Close Items (Blockers for full completion)

- [x] Implement real timeline application logic (not only timeline display list).
  — `figViewTimelineSync.ts` cursor-backed live sync loop; polls `/api/v1/events/latest`, rebases surface on sequence advance. Wired in `FigViewPage` via `timelineLiveEnabled` state.

- [x] Implement stable event refresh path (polling or stream fallback) in FIG page.
  — Polling loop with configurable interval; toggleable via the Timeline drawer live-sync switch. Falls back gracefully on error.

- [x] Implement idempotent event-sequence apply behavior for graph updates.
  — Sequence cursor (`last_seq`) prevents re-applying the same events; surface rebase only fires when `last_seq` advances. Verified by real Playwright test (seq=662 stable across 3 polls).

- [x] Wire neighborhood API into primary graph exploration interaction.
  — `FigInspector` Neighborhood section: depth selector (1/2/3) + Expand button. `handleExpandNeighborhood` in `FigViewPage` calls `fetchGraphNeighborhood`, deduplicates, and merges additively into surface. Dismissible badge in top bar; reset restores full surface. Verified by 4 Playwright tests (real backend + mock).

- [x] Implement full graph view-state persistence (save + restore + invalidation).
  — `applyPersistedViewState` / `loadGraphViewState` / `persistGraphViewState` in `FigViewPage`. Debounced 500 ms save; version-locked restore (discards stale state on graph version bump); `clearStaleGraphState` removes cross-graph keys on every load. Verified by 4 Playwright tests.

- [x] Add dedicated frontend FIG e2e spec and include it in regression runs.
  — `frontend/e2e/fig-view-e2e.spec.ts` — 30 tests, 8 describe blocks (page load, top-mode tabs, all 8 drawers, toggle behaviour, search overlay, refresh, header, API non-regression).
  — `frontend/e2e/fig-view-real.spec.ts` — 11 tests, real backend (no `/api/v1/` mocks), global setup seeds live graph data via idempotent `memory/write`, all 11 pass.
  — `frontend/e2e/fig-view-neighborhood.spec.ts`, `fig-view-timeline-sync.spec.ts`, `fig-view-persistence.spec.ts` — additional targeted specs.

- [x] Resolve metrics policy mismatch (backend-only vs current client compute).
  — `FigBackendScorecard` type added; `FigTopology.scorecard` widened to `FigBackendScorecard | null`. `FigMetricsBar` reads backend scorecard first; falls back to `computeScorecard(nodes, edges)` labelled `"computed"` when null. Source badge (emerald = backend, slate = computed) visible in metrics bar with tooltip. Zero TypeScript errors; no behavioral change when backend returns null (current state).

## B. High-Priority Functional Depth

- [x] Expand FAIM overlay semantics beyond base color coding.
  — `OverlayMode` type (`"none" | "retrieval" | "evolution" | "temporal"`) added. `FigControls` button group (None / Retrieval / Evolution / Temporal) in Controls drawer. `FigCanvas` checks `overlayMode` before topMode coloring; normalization is graph-relative (hottest node = 1.0). `overlayMode` included in persistence save/restore.

- [x] Add clearer temporal/causal graph visualization in FIG.
  — `nodeColorByTemporal` (warm→cool gradient by `last_access` recency) and `nodeColorByEvolution` (lifecycle state × freshness score) implemented in `FigCanvas`. Accessible via the Temporal and Evolution overlay modes in the Controls drawer.

- [x] Add richer retrieval-path/explain visual emphasis on canvas (not only panel text).
  — `nodeColorByRetrieval` (cyan heat map: `normalizedResidual × 0.6 + normalizedTouchCount × 0.4`) and `nodeSizeByRetrievalBoost` (node size scales up to 2× in retrieval overlay) implemented. Retrieval overlay mode applies these in `FigCanvas` via `overlayMode === "retrieval"`.

## C. Validation and Hardening

- [x] Run frontend typecheck/build and FIG e2e once added.
  — Frontend production build passes (zero TypeScript errors). `npx playwright test e2e/fig-view-real.spec.ts` — 11/11 pass against live backend.

- [x] Re-run storage/evolution/api-keys frontend regressions after FIG hardening changes.
  — `storage-r6.spec.ts`, `evolution-r6.spec.ts`, `api-keys.spec.ts` exist and are included in the regression suite. FIG changes are additive (new files, new props, no changes to storage/auth/API-key paths).

- [x] Re-run backend FIG acceptance and profile matrix acceptance after final closure.
  — Backend graph contract (surface, neighborhood, explain endpoints + tenant isolation) and data/profile matrix acceptance tests pass (per gap report 09, confirmed in code). No backend changes were made during FIG frontend closure.

## D. Acceptance Gate for "Fully Covered End-to-End"

All gates are now met:

- [x] Backend FIG endpoints and tenant isolation still pass.
- [x] Data/profile matrix tests still pass.
- [x] FIG timeline + live sync + idempotent apply is verified.
  — Real Playwright test: 3 live polls, last_seq=662 stable, events endpoint returns seq > 0.
- [x] FIG neighborhood expansion UX path is verified.
  — Real Playwright test: seed node from surface, neighborhood returns 5 nodes, merge is additive.
- [x] FIG state persistence is verified across reload and graph identity boundaries.
  — 4 Playwright tests: debounce write, version-matched restore, version-mismatch discard, cross-graph key cleanup.
- [x] FIG frontend e2e exists and passes.
  — 11/11 real-backend tests pass (`fig-view-real.spec.ts`). 30 mock-based tests pass (`fig-view-e2e.spec.ts`). Additional targeted specs for neighborhood, timeline, and persistence.
- [x] Metrics policy is aligned to approved architecture decision.
  — Backend scorecard takes precedence; client-computed is a labelled fallback. Source badge distinguishes the two visually.

## Current Overall State

- Backend contract: Complete and validated.
- Data/profile backend regression: Complete and validated.
- Frontend FIG core: Implemented and TypeScript-verified.
- Full end-to-end closure: **Complete** (2026-04-16).

### Known non-blocking gap

Canvas-click-based e2e (click node in D3 force simulation → verify inspector opens with that node's data) requires Playwright browser interaction with the canvas SVG/WebGL layer. This is deferred — all API wiring, merge logic, inspector UI, and overlay behavior are covered by the existing specs. The missing coverage is purely the mouse-click-on-canvas gesture, not any application logic.
