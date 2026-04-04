# 02_FigView_Implementation_Plan.md

Date: 2026-03-22
Status: Plan-first execution document. Stop after planning. Wait for approval before implementation.
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

Expected new frontend files:

1. `frontend/src/components/graph/FigViewPage.tsx`
2. `frontend/src/components/graph/FigCanvas.tsx`
3. `frontend/src/components/graph/FigControls.tsx`
4. `frontend/src/components/graph/FigLegend.tsx`
5. `frontend/src/components/graph/FigInspector.tsx`
6. `frontend/src/components/graph/FigFloatingCard.tsx`
7. `frontend/src/components/graph/FigMetricsBar.tsx`
8. `frontend/src/components/graph/FigEmptyState.tsx`
9. `frontend/src/components/graph/FigErrorState.tsx`
10. `frontend/src/components/graph/FigTimeline.tsx` verification-required depending on v1 scope
11. `frontend/src/lib/figViewApi.ts`
12. `frontend/src/lib/figViewGraphTransform.ts`
13. `frontend/src/lib/figViewLayout.ts`
14. `frontend/src/lib/figViewSafety.ts`
15. `frontend/src/types/figView.ts`

### 2.2 Backend touchpoints

Verified current files:

1. `faim_native/api/app.py`
2. `faim_native/api/deps.py`
3. `faim_native/api/routers/node.py`
4. `faim_native/api/routers/memory.py`
5. `faim_native/api/routers/storage.py`
6. `faim_native/api/routers/events.py`
7. `faim_native/api/routers/metrics.py`
8. `faim_native/api/routers/evolve.py`
9. `faim_native/api/routers/query.py`
10. `faim_native/runtime/context.py`
11. `faim_native/store/pg/models_faim.py`
12. `faim_native/store/pg/repos/node_repo.py`
13. `faim_native/store/pg/repos/edge_repo.py`
14. `faim_native/store/pg/repos/event_repo.py`
15. `faim_native/store/pg/repos/graph_version_repo.py`
16. `faim_native/store/pg/repos/storage_file_repo.py`

Expected new backend files:

1. `faim_native/api/routers/graph.py`
2. `tests/acceptance/test_AT_fig_graph_api_surface.py`
3. `tests/acceptance/test_AT_fig_graph_tenant_isolation.py`
4. `tests/unit/test_fig_graph_mapping.py`

Potential additive repo updates:

1. `faim_native/api/routers/__init__.py`
2. `faim_native/api/app.py`
3. `faim_native/store/pg/repos/node_repo.py`
4. `faim_native/store/pg/repos/edge_repo.py`

Schema changes:

1. not recommended initially
2. only allowed if an additive schema gap is proven
3. any migration need is verification-required before implementation

### 2.3 Current route and API compatibility review points

Frontend routes to protect:

1. `/dashboard/storage`
2. `/dashboard/evolution`
3. `/dashboard/api-keys`
4. `/dashboard/profile`
5. `/dashboard`
6. `/dashboard/graph`

Backend APIs to protect:

1. storage APIs
2. memory APIs
3. query API
4. evolve APIs
5. events APIs
6. auth and API key behavior

### 2.4 Auth and tenant safety review points

Must verify during implementation:

1. `UserContext` graph binding remains session-safe
2. no hardcoded graph ids
3. no graph loading without authenticated tenant context
4. graph router uses existing `FAIMContext`
5. no cross-tenant graph access by query parameter manipulation

### 2.5 Observability and logging review points

Must review before release:

1. graph endpoint timing
2. error logging with request id
3. safe graph and tenant logging
4. no sensitive payload logging
5. event refresh failure visibility

## 3. Implementation Phases

## Phase 0: Scope Freeze and Baseline

Goal:

1. confirm current repo baseline
2. confirm no unrelated refactor enters FIG work
3. confirm exact scope for v1

Checklist:

- [ ] inspect current graph page placeholder
- [ ] inspect current frontend shell and graph route wiring
- [ ] inspect current graph-related backend endpoints
- [ ] confirm no dedicated graph router exists
- [ ] confirm current test baseline
- [ ] confirm no schema migration is needed for first pass unless proven

Validation:

- [ ] current graph route still placeholder-only
- [ ] storage and evolution pages still behave normally

Acceptance gate:

- [ ] scope approved
- [ ] no unresolved ambiguity about ownership of graph data

## Phase 1: Graph API Contract

Authoritative spec (request/response, limits, semantics): `frontend/Docs/03_Phase1_FIG_Graph_API_Contract.md`.

Goal:

1. define a dedicated aggregate graph API for FIG without breaking existing APIs

Planned new endpoints:

1. `GET /api/v1/graph/surface`
2. `GET /api/v1/graph/neighborhood`
3. `POST /api/v1/graph/paths/explain`

Checklist:

- [ ] define request limits
- [ ] define response shape
- [ ] define snapshot/version semantics
- [ ] define deterministic ordering rules
- [ ] define error contract
- [ ] define additive-only compatibility rule
- [ ] define timeline window semantics
- [ ] define similarity-control semantics
- [ ] define node title fallback field strategy
- [ ] define graph display-state mapping contract
- [ ] define relation-distance field policy
- [ ] define graph-topology summary payload policy
- [ ] define safe deep-link policy

Validation:

- [ ] contract covers graph load
- [ ] contract covers node expansion
- [ ] contract covers relation explanation
- [ ] contract does not require breaking Storage, Memory, or Evolution contracts

Acceptance gate:

- [ ] contract approved before backend coding

## Phase 2: Backend Graph Router

Goal:

1. implement the minimum backend surface needed for live FIG

Files:

1. create `faim_native/api/routers/graph.py`
2. update `faim_native/api/routers/__init__.py`
3. update `faim_native/api/app.py`

Implementation principles:

1. reuse existing repos and current truth sources
2. do not duplicate provenance logic unnecessarily
3. do not weaken auth or scope behavior
4. do not change existing endpoint meanings

Checklist:

- [ ] implement graph surface
- [ ] implement graph neighborhood
- [ ] implement path explanation
- [ ] apply hard server-side bounds
- [ ] ensure deterministic ordering
- [ ] ensure graph_id is tenant-safe
- [ ] include recent-history timeline payload support for bounded recent event windows
- [ ] include enough relation metadata to support similarity and distance display where available
- [ ] include node display-state fields where backend truth exists or can be safely derived
- [ ] include graph-topology summary fields if contract-approved for surface response

Validation:

- [ ] graph surface returns nodes, edges, snapshot, and metrics safely
- [ ] neighborhood expands from selected node only within tenant graph
- [ ] explain returns safe relation summary or no-path response
- [ ] no backend field is guessed when unavailable
- [ ] absent advanced metrics degrade safely rather than fabricate values

Acceptance gate:

- [ ] backend routes compile and pass new contract tests

## Phase 3: Backend Tests and Non-Regression

Goal:

1. prove the new graph router is safe and non-breaking

New tests:

1. `tests/acceptance/test_AT_fig_graph_api_surface.py`
2. `tests/acceptance/test_AT_fig_graph_tenant_isolation.py`
3. `tests/unit/test_fig_graph_mapping.py`

Existing tests to re-run:

1. `tests/acceptance/test_AT_P1_storage_api_surface.py`
2. `tests/acceptance/test_AT_PD_storage_auth_tenant_isolation.py`
3. `tests/acceptance/test_AT_profile_persist_storage_matrix.py`
4. `tests/acceptance/test_AT_profile_persist_evolve_matrix.py`

Checklist:

- [ ] surface contract test
- [ ] neighborhood contract test
- [ ] explain contract test
- [ ] cross-tenant denial test
- [ ] bounds validation test
- [ ] re-run critical non-regression backend tests

Acceptance gate:

- [ ] no backend regression introduced

## Phase 4: Frontend Live Skeleton

Goal:

1. replace placeholder graph route with real data loading and safe state handling

Files:

1. update `frontend/src/app/(app)/dashboard/graph/page.tsx`
2. create `frontend/src/components/graph/FigViewPage.tsx`
3. create `frontend/src/lib/figViewApi.ts`
4. create `frontend/src/types/figView.ts`
5. create `frontend/src/lib/figViewSafety.ts`

Checklist:

- [ ] remove placeholder-only UI
- [ ] bind route to authenticated graph id
- [ ] load graph surface from backend
- [ ] support loading state
- [ ] support empty state
- [ ] support error state
- [ ] support degraded state
- [ ] implement safe node-title fallback strategy
- [ ] implement graph-state local persistence rules

Validation:

- [ ] route works inside existing shell
- [ ] no hardcoded universe ids
- [ ] graph cannot silently load from wrong tenant context
- [ ] stale persisted state never restores into the wrong graph

Acceptance gate:

- [ ] real graph data is rendered in a minimal but usable skeleton

## Phase 5: Canvas, Layout, and Core Controls

Goal:

1. deliver elite graph navigation without unstable behavior

Files:

1. create `frontend/src/components/graph/FigCanvas.tsx`
2. create `frontend/src/components/graph/FigControls.tsx`
3. create `frontend/src/lib/figViewLayout.ts`

Checklist:

- [ ] implement Explore mode
- [ ] implement Analyze mode
- [ ] implement Lineage mode
- [ ] implement fit graph
- [ ] implement center on selection
- [ ] implement reset camera
- [ ] implement zoom controls
- [ ] implement lock/unlock behavior
- [ ] implement scroll zoom
- [ ] implement timeline toggle/button entry point
- [ ] implement similarity controls entry point

Validation:

- [ ] same graph version renders stably
- [ ] switching layout does not lose selection
- [ ] lock/unlock behavior is predictable
- [ ] timeline interaction does not destabilize the graph scene
- [ ] similarity control changes view filtering only, not backend truth

Acceptance gate:

- [ ] graph exploration feels stable and intentional

## Phase 6: Inspector, Hover Cards, and Relation Exploration

Goal:

1. make graph objects inspectable and explainable

Files:

1. create `frontend/src/components/graph/FigInspector.tsx`
2. create `frontend/src/components/graph/FigFloatingCard.tsx`
3. create `frontend/src/components/graph/FigRelationPanel.tsx`
4. create `frontend/src/lib/figViewGraphTransform.ts`

Checklist:

- [ ] hover card
- [ ] node click selection
- [ ] pinned selection
- [ ] parent/child section
- [ ] provenance section
- [ ] conflict/opposition section
- [ ] explain relation section
- [ ] next relevant memory navigation
- [ ] previous relevant memory navigation
- [ ] graph-distance display
- [ ] display-state badges
- [ ] safe deep links where relevant
- [ ] redundancy/novelty/energy/confidence/salience cards where available

Validation:

- [ ] node detail matches backend truth
- [ ] hover card remains safe and light
- [ ] provenance never leaks beyond tenant graph
- [ ] next/previous relevant memory ordering is deterministic
- [ ] state badges do not guess unavailable backend states

Acceptance gate:

- [ ] a user can answer "what is this node and why is it here"

## Phase 7: Legend, Filters, Search, and Metrics

Goal:

1. make dense graph exploration usable at scale

Files:

1. create `frontend/src/components/graph/FigLegend.tsx`
2. create `frontend/src/components/graph/FigMetricsBar.tsx`
3. optional `frontend/src/components/graph/FigSearch.tsx`

Checklist:

- [ ] legend for nodes and edges
- [ ] node-type filters
- [ ] edge-type filters
- [ ] retrieval/activity filters if available
- [ ] search input
- [ ] metrics display for `D`, `H`, `lambda`
- [ ] graph version and event sequence visibility
- [ ] timeline control
- [ ] similarity threshold controls
- [ ] topology quality summary
- [ ] self-organization signal summary
- [ ] display-state legend

Validation:

- [ ] metrics are sourced from backend scorecard only
- [ ] missing values show `N/A`
- [ ] filter toggles do not mutate backend truth
- [ ] golden equation is not computed client-side

Acceptance gate:

- [ ] graph can be interpreted without developer tooling

## Phase 8: Overlays and FAIM-Specific Graph Signals

Goal:

1. show FAIM graph semantics, not just topology

Checklist:

- [ ] inheritance emphasis
- [ ] opposition emphasis
- [ ] dedup indicators
- [ ] prune/historical indicators if backend-backed
- [ ] macro emergence indicators
- [ ] retrieval path indicators if supported
- [ ] recent evolution change overlay
- [ ] historical/cold/deactivated visual treatment when state truth exists
- [ ] compression and merge distinction
- [ ] prune-effect and prune-candidate handling policy
- [ ] graph causality hints from recent event flow

Validation:

- [ ] overlays use real event and graph data
- [ ] FIG does not duplicate the Evolution page workflow
- [ ] historical-state visuals degrade safely when not supported

Acceptance gate:

- [ ] graph-side FAIM concepts are visually understandable

## Phase 9: Event Sync, Timeline, and State Persistence

Goal:

1. keep FIG current without instability

Checklist:

- [ ] integrate `events/latest`
- [ ] integrate event stream or polling fallback
- [ ] apply events idempotently by sequence
- [ ] preserve selection where possible
- [ ] preserve graph view state if appropriate
- [ ] implement bounded timeline stepping
- [ ] align persisted view state with graph identity

Validation:

- [ ] no duplicate event application
- [ ] reconnect or fallback does not corrupt view
- [ ] timeline only operates on supported bounded recent history

Acceptance gate:

- [ ] live graph updates remain stable

## Phase 10: Frontend Tests and Release Hardening

Goal:

1. prove FIG does not break the rest of FAIM

New frontend tests:

1. `frontend/e2e/fig-view.spec.ts`

Existing frontend tests to protect:

1. `frontend/e2e/storage-r6.spec.ts`
2. `frontend/e2e/evolution-r6.spec.ts`
3. `frontend/e2e/api-keys.spec.ts`
4. `frontend/tests/e2e/ui0.spec.ts`

Checklist:

- [ ] graph page loads
- [ ] empty state works
- [ ] hover card works
- [ ] inspector works
- [ ] layout switching works
- [ ] fit/center/reset works
- [ ] auth-expired or unauth state works safely
- [ ] rate-limit state works safely
- [ ] re-run existing frontend regressions

Acceptance gate:

- [ ] no critical frontend regression

## 4. Risk Register

### Risk 1: Contract fragmentation

Problem:

1. current graph data is spread across multiple routers

Mitigation:

1. add a dedicated graph router
2. keep existing detail endpoints as secondary detail sources

### Risk 2: Tenant leakage

Problem:

1. graph_id-driven pages can accidentally leak if validation is weak

Mitigation:

1. use existing `FAIMContext`
2. add explicit tenant isolation tests
3. avoid client-side bypass logic

### Risk 3: Overloading the graph page

Problem:

1. FIG can become a dumping ground for Storage and Evolution details

Mitigation:

1. keep page boundaries clear
2. show graph-facing summaries only
3. link out to other pages when full workflows belong elsewhere

### Risk 4: Performance collapse on dense graphs

Problem:

1. 3D graphs degrade quickly if everything is rendered at once

Mitigation:

1. cap initial payload
2. add neighborhood expansion
3. add LOD
4. reduce hover/labels when necessary

### Risk 5: Unsafe UI assumptions

Problem:

1. many desired graph semantics are not yet explicit backend contracts

Mitigation:

1. mark unverified concepts as verification-required
2. do not invent backend meaning in the frontend

### Risk 6: State-model drift

Problem:

1. states like cold, historical, deactivated, compressed, or prune-candidate can become misleading if UI guesses too much

Mitigation:

1. define the display taxonomy now
2. only bind a visible state when backend truth or safe derivation exists
3. otherwise hide the state rather than fake it

### Risk 7: Timeline overreach

Problem:

1. full replay could bloat v1 and destabilize the page

Mitigation:

1. use bounded recent-history timeline only
2. keep full replay out of v1 unless the backend contract proves it cleanly

## 5. What Must Not Break

Absolute non-regression targets:

1. existing code structure
2. existing integrations and connections
3. auth
4. tenant isolation
5. security and rate limiting
6. encryption-at-rest behavior
7. storage APIs and workflows
8. memory APIs and workflows
9. query behavior
10. evolution runtime behavior
11. events and jobs
12. dashboard shell and routing

Specific checks:

- [ ] storage upload/list/provenance unchanged
- [ ] memory get/search/provenance unchanged
- [ ] query unchanged
- [ ] evolve status and events unchanged
- [ ] auth and API key behavior unchanged
- [ ] no sensitive logging introduced
- [ ] persisted graph view state never crosses graph boundaries
- [ ] timeline mode never degrades current event APIs or evolution page behavior

## 6. Validation Commands

Backend:

- [ ] `python3 -m compileall faim_native tests`
- [ ] `PYTHONPATH=.:faim_native pytest -q tests/acceptance/test_AT_P1_storage_api_surface.py tests/acceptance/test_AT_PD_storage_auth_tenant_isolation.py`
- [ ] `PYTHONPATH=.:faim_native pytest -q tests/acceptance/test_AT_profile_persist_storage_matrix.py tests/acceptance/test_AT_profile_persist_evolve_matrix.py`
- [ ] `PYTHONPATH=.:faim_native pytest -q tests/acceptance/test_AT_fig_graph_api_surface.py tests/acceptance/test_AT_fig_graph_tenant_isolation.py`

Frontend:

- [ ] `cd frontend && npm run typecheck`
- [ ] `cd frontend && npm run build`
- [ ] `cd frontend && npx playwright test e2e/storage-r6.spec.ts e2e/evolution-r6.spec.ts e2e/api-keys.spec.ts`
- [ ] `cd frontend && npx playwright test e2e/fig-view.spec.ts`

## 7. Rollout Strategy

Recommended rollout:

1. internal validation
2. pilot users or pilot tenant graph
3. broader release after evidence

Release conditions:

- [ ] graph contract tests pass
- [ ] frontend FIG tests pass
- [ ] storage/evolution/auth regressions pass
- [ ] no unresolved high-severity security issue
- [ ] rollback path understood

Rollback options:

1. disable graph route runtime feature if implemented behind a flag
2. revert new graph router without touching core existing routers
3. redeploy prior frontend bundle if needed

## 8. Explicit Coverage Matrix For Previously Missing Topics

| Topic | Planned resolution |
|---|---|
| Timeline controls | Included in v1 as bounded recent-history timeline, not full replay studio |
| Similarity controls | Included in v1 as exploration filtering controls |
| Safe title/label | Strict fallback strategy in frontend plus backend-safe field preference |
| Forgotten/deactivated/cold/compressed/historical states | Formal display taxonomy defined now; implementation binds only supported states |
| Graph state persistence | Local per-user/session persistence included |
| Graph topology quality | Included as topology summary panel |
| Compression and merge signals | Included as separate visual/inspector concepts |
| Golden equation | Backend verification/status only, not frontend-computed |
| Node/edge/relation distances | Included as inspector/relation concepts where values are available |
| Inheritance distance | Included conceptually in relation metrics |
| Graph causality/history | Included via bounded recent-history timeline and event overlays |
| Self-organization signals | Included as graph-side explanatory summary |
| Links to open detail page | Included as safe contextual deep links |
| Redundancy/novelty/confidence/energy/salience | Included as graph or node signal cards where available |
| Memory status taxonomy | Included as explicit display-state model |
| Similarity relationships | Included as first-class exploration layer |
| Live memory state indicators | Included in display-state model and recent activity treatment |
| Prune candidate state | Included only when backed by explicit truth; prune effects always shown when event-backed |

## 9. Approval Checkpoint

This is a plan-first task.
Implementation should not start until these are approved:

- [ ] Explanation document approved
- [ ] Implementation plan approved
- [ ] Scope of v1 versus verification-required extensions approved

Decision:

- [ ] GO
- [ ] NO-GO
