# 02_FigView_Implementation_Plan.md

Date: 2026-03-22 | Last verified: 2026-04-17
Status: Implementation complete. Checkboxes updated to reflect actual code state.
Scope: Production-safe execution strategy for delivering Fig View in FAIM without breaking existing behavior.

## 1. Execution Strategy

Recommended strategy: backend contract first, then vertical slices front-to-back.

Not recommended:

1. frontend-first without stable graph contracts
2. backend-only for too long without rendering validation

Recommended sequence:

1. verify codebase and freeze scope
2. define graph API contract
3. implement minimal backend graph router
4. build live frontend skeleton against real data
5. layer interaction, inspector, overlays, and hardening incrementally

Why this is safest:

1. current graph page is placeholder-only
2. current backend pieces exist but are fragmented across multiple routers
3. tenant isolation and graph version consistency are easier to protect when the aggregate contract is defined first

## 1.1 Closed-Scope Decisions For Previously Open Items

The following items are now explicitly in scope for the plan so nothing is left undefined:

1. v1 includes a bounded recent-history timeline control
2. v1 includes similarity controls as exploration filters, not truth mutation
3. v1 uses a strict safe node-title fallback strategy
4. v1 includes a formal display-state taxonomy:
   - active
   - historical
   - compressed
   - deduplicated
   - pruned
   - cold
   - deactivated
5. v1 includes graph-state persistence locally per user/session
6. v1 includes deterministic next/previous relevant memory ordering
7. v1 includes graph-distance categories in inspector and relation panels
8. v1 includes graph-topology quality summaries
9. v1 includes self-organization signals from graph perspective
10. v1 includes contextual links to relevant detail pages where safe
11. golden equation is backend-verification-only, not a frontend-computed metric

## 2. Repo Audit and Verified Touchpoints

This section folds the repository audit into the plan so the package remains two documents only.

### 2.1 Frontend touchpoints

Verified current files:

1. `frontend/src/app/(app)/dashboard/graph/page.tsx`
2. `frontend/src/app/(app)/dashboard/storage/page.tsx`
3. `frontend/src/app/(app)/dashboard/evolution/page.tsx`
4. `frontend/src/app/(app)/dashboard/api-keys/page.tsx`
5. `frontend/src/components/layout/Sidebar/SidebarNav.tsx`
6. `frontend/src/components/layout/Breadcrumbs.tsx`
7. `frontend/src/components/layout/FaimShell.tsx`
8. `frontend/src/contexts/UserContext.tsx`
9. `frontend/src/types/api.ts`
10. `frontend/package.json`

Expected new frontend files — status:

1. ✅ `frontend/src/components/graph/FigViewPage.tsx` — main page, state management, drawer UI, polling, neighborhood, explain
2. ✅ `frontend/src/components/graph/FigCanvas.tsx` — 3D force-graph, layout modes, overlay modes, node/edge coloring
3. ✅ `frontend/src/components/graph/FigControls.tsx` — camera, lock, mode buttons, overlay selector, similarity
4. ✅ `frontend/src/components/graph/FigLegend.tsx` — 8 node states, edge kinds, visibility toggles
5. ✅ `frontend/src/components/graph/FigInspector.tsx` — identity, provenance, parents/children, opposition, explain, neighborhood
6. ✅ `frontend/src/components/graph/FigFloatingCard.tsx` — hover card via Portal, viewport-aware positioning
7. ✅ `frontend/src/components/graph/FigMetricsBar.tsx` — node/edge counts, D/H/λ, backend/computed source badge
8. ❌ `frontend/src/components/graph/FigEmptyState.tsx` — not a separate file; empty state inline in FigViewPage
9. ❌ `frontend/src/components/graph/FigErrorState.tsx` — not a separate file; error state inline in FigViewPage
10. ❌ `frontend/src/components/graph/FigTimeline.tsx` — not a separate file; timeline drawer inline in FigViewPage
11. ✅ `frontend/src/lib/figViewApi.ts` — fetchGraphSurface, fetchGraphLatestEvent, fetchGraphNeighborhood, fetchGraphExplain
12. ✅ `frontend/src/lib/figViewGraphTransform.ts` — node index, adjacency, parent/child helpers, scorecard compute
13. ✅ `frontend/src/lib/figViewLayout.ts` — layout configs, all color functions, OverlayMode type
14. ✅ `frontend/src/lib/figViewSafety.ts` — safeNodeTitle, nodeStateClass, persistGraphViewState, loadGraphViewState
15. ✅ `frontend/src/types/figView.ts` — all FIG types including FigNeighborhoodExpansion, FigBackendScorecard

Also created (not in original plan):
- ✅ `frontend/src/lib/figViewTimelineSync.ts` — timeline sync state, idempotent merge, cursor, rebase detection

### 2.2 Backend touchpoints

Verified current files: all present and unchanged.

Expected new backend files — status:

1. ✅ `faim_native/api/routers/graph.py` — GET /surface, GET /neighborhood, POST /paths/explain, tenant-safe, hard bounds
2. ✅ `tests/acceptance/test_AT_fig_graph_api_surface.py` — API surface contract tests
3. ✅ `tests/acceptance/test_AT_fig_graph_tenant_isolation.py` — auth enforcement, cross-tenant denial
4. ✅ `tests/unit/test_fig_graph_mapping.py` — mapping functions, path helpers, clamping

### 2.3 Current route and API compatibility review points

Frontend routes — all protected and unbroken: ✅
Backend APIs — all protected and unbroken: ✅

### 2.4 Auth and tenant safety review points

- [x] `UserContext` graph binding remains session-safe — graphId from session, never hardcoded
- [x] no hardcoded graph ids — verified in FigViewPage
- [x] no graph loading without authenticated tenant context
- [x] graph router uses existing `FAIMContext`
- [x] no cross-tenant graph access by query parameter manipulation — _resolve_graph_id enforces this

### 2.5 Observability and logging review points

- [x] graph endpoint timing — request_id in all backend responses
- [x] error logging with request id
- [x] safe graph and tenant logging — email/id fragments only
- [x] no sensitive payload logging
- [x] event refresh failure visibility — polling errors logged, sync status badge in UI

## 3. Implementation Phases

## Phase 0: Scope Freeze and Baseline

Goal:

1. confirm current repo baseline
2. confirm no unrelated refactor enters FIG work
3. confirm exact scope for v1

Checklist:

- [x] inspect current graph page placeholder
- [x] inspect current frontend shell and graph route wiring
- [x] inspect current graph-related backend endpoints
- [x] confirm no dedicated graph router exists
- [x] confirm current test baseline
- [x] confirm no schema migration is needed for first pass unless proven

Validation:

- [x] current graph route still placeholder-only (was; now replaced with FigViewPage)
- [x] storage and evolution pages still behave normally

Acceptance gate:

- [x] scope approved
- [x] no unresolved ambiguity about ownership of graph data

## Phase 1: Graph API Contract

Authoritative spec (request/response, limits, semantics): `frontend/Docs/03_Phase1_FIG_Graph_API_Contract.md`.

Goal:

1. define a dedicated aggregate graph API for FIG without breaking existing APIs

Planned new endpoints:

1. `GET /api/v1/graph/surface` ✅
2. `GET /api/v1/graph/neighborhood` ✅
3. `POST /api/v1/graph/paths/explain` ✅

Checklist:

- [x] define request limits — SURFACE_NODE_MIN/MAX, SURFACE_EDGE_MIN/MAX, TIMELINE_MIN/MAX
- [x] define response shape
- [x] define snapshot/version semantics
- [x] define deterministic ordering rules
- [x] define error contract
- [x] define additive-only compatibility rule
- [x] define timeline window semantics
- [x] define similarity-control semantics
- [x] define node title fallback field strategy
- [x] define graph display-state mapping contract
- [x] define relation-distance field policy
- [x] define graph-topology summary payload policy
- [x] define safe deep-link policy

Validation:

- [x] contract covers graph load
- [x] contract covers node expansion
- [x] contract covers relation explanation
- [x] contract does not require breaking Storage, Memory, or Evolution contracts

Acceptance gate:

- [x] contract approved before backend coding

## Phase 2: Backend Graph Router

Goal:

1. implement the minimum backend surface needed for live FIG

Files:

1. ✅ `faim_native/api/routers/graph.py` created
2. ✅ `faim_native/api/routers/__init__.py` updated
3. ✅ `faim_native/api/app.py` updated

Checklist:

- [x] implement graph surface
- [x] implement graph neighborhood
- [x] implement path explanation
- [x] apply hard server-side bounds — SURFACE_NODE: 1-200, SURFACE_EDGE: 1-1000, TIMELINE: 1-500
- [x] ensure deterministic ordering
- [x] ensure graph_id is tenant-safe — _resolve_graph_id validates and rejects empty/mismatched
- [x] include recent-history timeline payload support for bounded recent event windows
- [x] include enough relation metadata to support similarity and distance display where available
- [x] include node display-state fields where backend truth exists or can be safely derived
- [x] include graph-topology summary fields if contract-approved for surface response

Validation:

- [x] graph surface returns nodes, edges, snapshot, and metrics safely
- [x] neighborhood expands from selected node only within tenant graph
- [x] explain returns safe relation summary or no-path response
- [x] no backend field is guessed when unavailable
- [x] absent advanced metrics degrade safely rather than fabricate values

Acceptance gate:

- [x] backend routes compile and pass new contract tests

## Phase 3: Backend Tests and Non-Regression

Goal:

1. prove the new graph router is safe and non-breaking

New tests:

1. ✅ `tests/acceptance/test_AT_fig_graph_api_surface.py`
2. ✅ `tests/acceptance/test_AT_fig_graph_tenant_isolation.py`
3. ✅ `tests/unit/test_fig_graph_mapping.py`

Existing tests to re-run:

1. ✅ `tests/acceptance/test_AT_P1_storage_api_surface.py`
2. ✅ `tests/acceptance/test_AT_PD_storage_auth_tenant_isolation.py`
3. ✅ `tests/acceptance/test_AT_profile_persist_storage_matrix.py`
4. ✅ `tests/acceptance/test_AT_profile_persist_evolve_matrix.py`

Checklist:

- [x] surface contract test
- [x] neighborhood contract test
- [x] explain contract test
- [x] cross-tenant denial test
- [x] bounds validation test
- [x] re-run critical non-regression backend tests

Acceptance gate:

- [x] no backend regression introduced

## Phase 4: Frontend Live Skeleton

Goal:

1. replace placeholder graph route with real data loading and safe state handling

Files:

1. ✅ `frontend/src/app/(app)/dashboard/graph/page.tsx` updated — imports and renders FigViewPage
2. ✅ `frontend/src/components/graph/FigViewPage.tsx` created
3. ✅ `frontend/src/lib/figViewApi.ts` created
4. ✅ `frontend/src/types/figView.ts` created
5. ✅ `frontend/src/lib/figViewSafety.ts` created

Checklist:

- [x] remove placeholder-only UI
- [x] bind route to authenticated graph id — from session.graphId via UserContext
- [x] load graph surface from backend
- [x] support loading state — spinner while fetching
- [x] support empty state — inline empty state when 0 nodes
- [x] support error state — inline error state with retry button
- [x] support degraded state — classifyResponse handles consistent_read: false
- [x] implement safe node-title fallback strategy — safeNodeTitle in figViewSafety.ts
- [x] implement graph-state local persistence rules — debounced save, version-locked restore, stale-guard

Validation:

- [x] route works inside existing shell
- [x] no hardcoded universe ids
- [x] graph cannot silently load from wrong tenant context
- [x] stale persisted state never restores into the wrong graph — version guard in loadGraphViewState

Acceptance gate:

- [x] real graph data is rendered in a minimal but usable skeleton

## Phase 5: Canvas, Layout, and Core Controls

Goal:

1. deliver elite graph navigation without unstable behavior

Files:

1. ✅ `frontend/src/components/graph/FigCanvas.tsx` created
2. ✅ `frontend/src/components/graph/FigControls.tsx` created
3. ✅ `frontend/src/lib/figViewLayout.ts` created

Checklist:

- [x] implement Explore mode
- [x] implement Analyze mode
- [x] implement Lineage mode
- [x] implement fit graph
- [x] implement center on selection
- [x] implement reset camera
- [x] implement zoom controls
- [x] implement lock/unlock behavior
- [x] implement scroll zoom
- [x] implement timeline toggle/button entry point
- [x] implement similarity controls entry point

Validation:

- [x] same graph version renders stably
- [x] switching layout does not lose selection
- [x] lock/unlock behavior is predictable
- [x] timeline interaction does not destabilize the graph scene
- [x] similarity control changes view filtering only, not backend truth

Acceptance gate:

- [x] graph exploration feels stable and intentional

## Phase 6: Inspector, Hover Cards, and Relation Exploration

Goal:

1. make graph objects inspectable and explainable

Files:

1. ✅ `frontend/src/components/graph/FigInspector.tsx` created
2. ✅ `frontend/src/components/graph/FigFloatingCard.tsx` created
3. ✅ `frontend/src/components/graph/FigRelationPanel.tsx` created
4. ✅ `frontend/src/lib/figViewGraphTransform.ts` created

Checklist:

- [x] hover card — FigFloatingCard, Portal-rendered, viewport-aware
- [x] node click selection — selectedNodeId state
- [x] pinned selection — explain relation has pinned + selected node pair
- [x] parent/child section — parents and children with node_id links
- [x] provenance section — raw_id, block_id, storage deep link
- [x] conflict/opposition section — opposition edges listed with peer node
- [x] explain relation section — path find between pinned and selected, hop list
- [x] next relevant memory navigation — ← Prev button cycles through `getRelevantNeighborOrder()` list with position indicator (`FigInspector.tsx`)
- [x] previous relevant memory navigation — → Next button cycles through `getRelevantNeighborOrder()` list; navIdx resets on node change (`FigInspector.tsx`)
- [x] graph-distance display — relation_distance badge in explain result
- [x] display-state badges — state badge inline with color per node
- [x] safe deep links where relevant — storage provenance link in inspector
- [x] redundancy/novelty/energy/confidence/salience cards where available — Novelty (residual [0-1]), Redundancy signal (touch_count), Recency (last_access) shown as color-coded "Memory Signals" cards in inspector. Energy/confidence/salience omitted — not exposed per node by backend.

Validation:

- [x] node detail matches backend truth
- [x] hover card remains safe and light
- [x] provenance never leaks beyond tenant graph
- [x] next/previous relevant memory ordering is deterministic — sort key: edge weight DESC → kind priority (inheritance < opposition) → lexicographic node_id. Same graph state → same order. (`getRelevantNeighborOrder` in `figViewGraphTransform.ts`)
- [x] state badges do not guess unavailable backend states

Acceptance gate:

- [x] a user can answer "what is this node and why is it here"

## Phase 7: Legend, Filters, Search, and Metrics

Goal:

1. make dense graph exploration usable at scale

Files:

1. ✅ `frontend/src/components/graph/FigLegend.tsx` created
2. ✅ `frontend/src/components/graph/FigMetricsBar.tsx` created
3. ✅ `frontend/src/components/graph/FigSearch.tsx` created (not in original plan but implemented)

Checklist:

- [x] legend for nodes and edges — 8 node states + edge kinds with visibility toggles
- [x] node-type filters — hidden node kinds state in FigViewPage
- [x] edge-type filters — hidden edge kinds state in FigViewPage
- [x] retrieval/activity filters if available — retrieval overlay mode in FigControls
- [x] search input — FigSearch overlay, "/" shortcut, type-to-filter, result count
- [x] metrics display for `D`, `H`, `lambda` — FigMetricsBar with backend/computed source badge
- [x] graph version and event sequence visibility — snapshot version + last_seq in FigMetricsBar
- [x] timeline control — timeline drawer with live-sync toggle
- [x] similarity threshold controls — similarity mode in FigControls
- [x] topology quality summary — dedicated panel in FigControls drawer: D/H/λ with color-coded health, self-org signals (active ratio, compression rate, macro ratio, opposition density), node lifecycle breakdown bar chart
- [x] self-organization signal summary — active ratio, macro node %, compression rate, opposition density computed from `FigNode.level` + `display.state` + `topology.edge_counts_by_kind` (backend-authoritative data)
- [x] display-state legend — all 8 states with colors in FigLegend

Validation:

- [x] metrics are sourced from backend scorecard when available; client-computed labelled fallback when null
- [x] missing values show `N/A`
- [x] filter toggles do not mutate backend truth
- [x] golden equation — backend scorecard takes precedence; client-computed is a labelled "computed" fallback derived from backend-authoritative node/edge data. D/H/λ now color-coded in FigMetricsBar (cyan/violet/emerald health indicators)

Acceptance gate:

- [x] graph can be interpreted without developer tooling

## Phase 8: Overlays and FAIM-Specific Graph Signals

Goal:

1. show FAIM graph semantics, not just topology

Checklist:

- [x] inheritance emphasis — lineage mode depth-based coloring + cyan edge color for inheritance
- [x] opposition emphasis — red edge color for opposition + opposition section in inspector
- [x] dedup indicators — deduplicated node state color
- [x] prune/historical indicators if backend-backed — pruned/historical node state colors
- [x] macro emergence indicators — node level-based sizing (higher level = larger node)
- [x] retrieval path indicators — heat-map overlay ✅; explain path now drawn on canvas in amber-400 with directional particles for path edges (`FigCanvas.tsx` — `explainPath` prop, `linkDirectionalParticles`)
- [x] recent evolution change overlay — evolution overlay mode (lifecycle state × freshness)
- [x] historical/cold/deactivated visual treatment — all 8 node states have distinct colors + descriptions in FigLegend
- [x] compression and merge distinction — compressed (blue-400) vs deduplicated (violet-400) visually distinct in all modes; lifecycle banners in FigInspector explain each state; FigLegend has per-state descriptions
- [x] prune-effect and prune-candidate handling policy — pruned nodes show red-400 + "Pruned node" banner in inspector; lifecycle breakdown in FigControls quality panel; FigLegend explains "terminal" semantics
- [x] graph causality hints from recent event flow — new "Causality" overlay mode: heat map by combined last_access recency × touch_count frequency (`nodeColorByCausality` in figViewLayout.ts)

Validation:

- [x] overlays use real event and graph data
- [x] FIG does not duplicate the Evolution page workflow
- [x] historical-state visuals degrade safely when not supported

Acceptance gate:

- [x] graph-side FAIM concepts are visually understandable

## Phase 9: Event Sync, Timeline, and State Persistence

Goal:

1. keep FIG current without instability

Checklist:

- [x] integrate `events/latest` — fetchGraphLatestEvent in figViewApi.ts
- [x] integrate event stream or polling fallback — 2-4s polling loop in FigViewPage
- [x] apply events idempotently by sequence — normalizeTimelineEvents deduplicates by seq; mergeTimelineResponse merges by seq
- [x] preserve selection where possible — selectedNodeId persisted
- [x] preserve graph view state if appropriate — debounced save to localStorage, version-locked restore
- [x] implement bounded timeline stepping — "Step mode" toggle in timeline drawer: Prev/Next buttons cycle through events with position indicator; current event shows seq, kind, ts, payload_keys in detail card; list rows are clickable in step mode. (Note: true historical graph state reconstruction requires backend time-travel API — not yet available. This stepping navigates the event log visually.)
- [x] align persisted view state with graph identity — version guard discards stale state on graph version bump

Validation:

- [x] no duplicate event application
- [x] reconnect or fallback does not corrupt view
- [x] timeline only operates on supported bounded recent history

Acceptance gate:

- [x] live graph updates remain stable

## Phase 10: Frontend Tests and Release Hardening

Goal:

1. prove FIG does not break the rest of FAIM

New frontend tests:

1. ✅ `frontend/e2e/fig-view-e2e.spec.ts` — 30 tests, 8 describe blocks, all non-canvas UI
2. ✅ `frontend/e2e/fig-view-real.spec.ts` — 11 tests, real backend (no mocks), 11/11 passing
3. ✅ `frontend/e2e/fig-view-neighborhood.spec.ts` — neighborhood API wiring
4. ✅ `frontend/e2e/fig-view-persistence.spec.ts` — view-state save/restore
5. ✅ `frontend/e2e/fig-view-timeline-sync.spec.ts` — live sync polling

Existing frontend tests to protect:

1. ✅ `frontend/e2e/storage-r6.spec.ts`
2. ✅ `frontend/e2e/evolution-r6.spec.ts`
3. ✅ `frontend/e2e/api-keys.spec.ts`
4. `frontend/tests/e2e/ui0.spec.ts` — verify still present

Checklist:

- [x] graph page loads
- [x] empty state works
- [x] hover card works
- [x] inspector works
- [x] layout switching works
- [x] fit/center/reset works
- [x] auth-expired or unauth state works safely
- [x] rate-limit state works safely
- [x] re-run existing frontend regressions

Acceptance gate:

- [x] no critical frontend regression

## 4. Risk Register

All risks mitigated per original plan. No new risks introduced.

## 5. What Must Not Break

Absolute non-regression targets — all verified:

- [x] storage upload/list/provenance unchanged
- [x] memory get/search/provenance unchanged
- [x] query unchanged
- [x] evolve status and events unchanged
- [x] auth and API key behavior unchanged
- [x] no sensitive logging introduced
- [x] persisted graph view state never crosses graph boundaries — clearStaleGraphState + version guard
- [x] timeline mode never degrades current event APIs or evolution page behavior

## 6. Validation Commands

Backend:

- [x] `python3 -m compileall faim_native tests`
- [x] `PYTHONPATH=.:faim_native pytest -q tests/acceptance/test_AT_P1_storage_api_surface.py tests/acceptance/test_AT_PD_storage_auth_tenant_isolation.py`
- [x] `PYTHONPATH=.:faim_native pytest -q tests/acceptance/test_AT_profile_persist_storage_matrix.py tests/acceptance/test_AT_profile_persist_evolve_matrix.py`
- [x] `PYTHONPATH=.:faim_native pytest -q tests/acceptance/test_AT_fig_graph_api_surface.py tests/acceptance/test_AT_fig_graph_tenant_isolation.py`

Frontend:

- [x] `cd frontend && npm run typecheck` — zero TypeScript errors
- [x] `cd frontend && npm run build` — production build passes
- [x] `cd frontend && npx playwright test e2e/storage-r6.spec.ts e2e/evolution-r6.spec.ts e2e/api-keys.spec.ts`
- [x] `cd frontend && npx playwright test e2e/fig-view-e2e.spec.ts e2e/fig-view-real.spec.ts` — 11/11 real-backend tests pass

## 7. Rollout Strategy

- [x] graph contract tests pass
- [x] frontend FIG tests pass
- [x] storage/evolution/auth regressions pass
- [x] no unresolved high-severity security issue
- [x] rollback path understood

## 8. Explicit Coverage Matrix For Previously Missing Topics

| Topic | Status |
|---|---|
| Timeline controls | ✅ Bounded recent-history timeline with live-sync polling |
| Similarity controls | ✅ Exploration filtering in FigControls |
| Safe title/label | ✅ safeNodeTitle with strict fallback strategy |
| Forgotten/deactivated/cold/compressed/historical states | ✅ All 8 states in display taxonomy with distinct colors |
| Graph state persistence | ✅ Local per-user/session with version guard |
| Graph topology quality | ✅ FigControls quality panel: D/H/λ health colors, self-org signals, lifecycle breakdown |
| Compression and merge signals | ✅ compressed (blue) vs deduplicated (violet) distinct; inspector lifecycle banners; legend descriptions |
| Golden equation | ✅ Backend scorecard takes precedence; client-computed labelled fallback |
| Node/edge/relation distances | ✅ relation_distance badge in explain result |
| Inheritance distance | ✅ Lineage depth coloring; inheritance edge coloring |
| Graph causality/history | ✅ Causality overlay mode (recency × frequency heat map); timeline stepping with event detail cards |
| Self-organization signals | ✅ Active ratio, macro %, compression rate, opposition density in FigControls quality panel |
| Links to open detail page | ✅ Storage provenance deep link in inspector |
| Redundancy/novelty/confidence/energy/salience | ✅ Novelty (residual), Redundancy (touch_count), Recency (last_access) as color-coded cards. Energy/confidence/salience not per-node in backend. |
| Memory status taxonomy | ✅ All 8 display states bound to backend truth |
| Similarity relationships | ✅ Similarity mode in FigControls |
| Live memory state indicators | ✅ Display-state model + polling |
| Prune candidate state | ✅ Pruned state: red-400 + "Pruned node" inspector banner; lifecycle breakdown in quality panel |

## 9. Approval Checkpoint

- [x] Explanation document approved
- [x] Implementation plan approved
- [x] Scope of v1 versus verification-required extensions approved
- [x] GO

---

## Items Left To Work (Summary)

All plan items are now implemented. The following minor optional items remain:

1. **FigEmptyState / FigErrorState / FigTimeline as separate files** — functionality exists inline in FigViewPage; extraction is optional refactor only
2. **True historical graph state reconstruction (time-machine)** — timeline stepping navigates event log; full graph-at-seq requires a backend time-travel API endpoint not yet available
