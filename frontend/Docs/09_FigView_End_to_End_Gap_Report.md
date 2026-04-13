# 09_FigView_End_to_End_Gap_Report

Date: 2026-04-13
Source baseline: frontend/Docs/02_FigView_Implementation_Plan.md
Scope: End-to-end implementation gap report for FIG View (what is done vs what is still left).

## Executive Verdict

FIG is not fully complete end-to-end yet.

- Backend graph contract and safety are implemented and verified.
- Core frontend FIG UI is implemented and usable.
- Several plan-critical closure items are still open (timeline behavior, neighborhood expansion flow, persistence integration, FIG e2e hardening, and policy alignment).

## What Is Already Covered

### Backend coverage (implemented and verified)

- Dedicated graph router exists and is mounted.
- Endpoints implemented:
  - GET /api/v1/graph/surface
  - GET /api/v1/graph/neighborhood
  - POST /api/v1/graph/paths/explain
- Tenant isolation and API surface acceptance tests exist and pass.
- FIG mapping unit tests exist and pass.

### Data/Profile coverage (implemented and verified)

- Profile-persist storage matrix acceptance tests exist and pass.
- Profile-persist evolve matrix acceptance tests exist and pass.
- Profile page and user context bind graph identity from authenticated context and /api/v1/auth/me.

### Frontend base FIG coverage (implemented)

- Graph route is connected to FigViewPage.
- Graph surface fetch is live.
- Canvas, controls, inspector, relation panel, legend, search, and metrics UI exist.
- Explain path API is integrated in inspector/relation flow.

## End-to-End Gaps Still Left

## 1) Timeline and live sync behavior (OPEN)

Plan intent: bounded timeline with stable event sync behavior and idempotent sequence handling.

Still left:

- Timeline is displayed as a drawer/list but not applied to graph state evolution.
- No polling/stream-based live sync flow in FIG page.
- No idempotent sequence-application loop in FIG page.
- Timeline control wiring in controls is effectively placeholder in page composition.

## 2) Neighborhood-driven exploration flow (PARTIAL/OPEN)

Plan intent: neighborhood expansion as a first-class graph navigation behavior.

Still left:

- Neighborhood API client exists, but main FIG page does not run neighborhood expansion flow as a user action path.
- Current main load path relies on surface snapshot fetch.

## 3) Graph view-state persistence integration (OPEN)

Plan intent: graph-state persistence per user/session with graph identity safety.

Still left:

- Persistence utility functions exist.
- Full save/restore lifecycle is not integrated in FigViewPage interaction loop.
- Current usage only clears stale state, not full persisted view restore/apply behavior.

## 4) Frontend hardening test coverage (OPEN)

Plan intent: dedicated FIG e2e coverage plus non-regression safety.

Still left:

- Dedicated frontend FIG e2e test file is missing.
- Existing frontend e2e currently focuses on storage/evolution/api-keys/UI baseline, not full FIG path.

## 5) Metrics policy alignment with plan (OPEN)

Plan intent in implementation plan: golden equation backend-verification-only (not frontend-computed metric).

Still left:

- Current FIG metrics bar computes D/H/lambda client-side from graph data.
- This behavior conflicts with strict plan wording and should be aligned by decision:
  - Either move to backend-sourced scorecard only, or
  - Update plan policy to allow client-side computed display metrics.

## 6) Advanced overlays and semantic emphasis depth (PARTIAL)

Plan intent: richer FAIM-specific overlays and evolution-aware semantics.

Still left:

- Basic coloring and sizing semantics exist.
- Deeper overlay semantics (retrieval path emphasis, evolution-change overlay coupling, richer temporal/causal graph overlays) are not fully closed end-to-end.

## Release Readiness Summary

Ready now:

- Backend FIG contract safety and tests.
- Core frontend FIG exploration skeleton.
- Data/profile matrix backend non-regression.

Not ready for full “plan complete” declaration:

- Timeline/live-sync closure.
- Neighborhood expansion as full UI flow.
- Persistence full integration.
- Dedicated FIG frontend e2e.
- Metrics policy alignment.
- Final advanced overlay closure.

## Final Status

- Backend FIG: Strong and validated.
- Data/Profile: Covered and validated.
- Frontend FIG end-to-end: Partial; key closure items remain open.
