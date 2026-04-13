# 10_FigView_Open_Coverage_Checklist

Date: 2026-04-13
Based on: frontend/Docs/02_FigView_Implementation_Plan.md
Purpose: Checklist of what is still left to claim full end-to-end FIG completion.

## A. Must-Close Items (Blockers for full completion)

- [ ] Implement real timeline application logic (not only timeline display list).
- [ ] Implement stable event refresh path (polling or stream fallback) in FIG page.
- [ ] Implement idempotent event-sequence apply behavior for graph updates.
- [ ] Wire neighborhood API into primary graph exploration interaction.
- [ ] Implement full graph view-state persistence (save + restore + invalidation).
- [ ] Add dedicated frontend FIG e2e spec and include it in regression runs.
- [ ] Resolve metrics policy mismatch (backend-only vs current client compute).

## B. High-Priority Functional Depth

- [ ] Expand FAIM overlay semantics beyond base color coding.
- [ ] Add clearer temporal/causal graph visualization in FIG.
- [ ] Add richer retrieval-path/explain visual emphasis on canvas (not only panel text).

## C. Validation and Hardening

- [ ] Run frontend typecheck/build and FIG e2e once added.
- [ ] Re-run storage/evolution/api-keys frontend regressions after FIG hardening changes.
- [ ] Re-run backend FIG acceptance and profile matrix acceptance after final closure.

## D. Acceptance Gate for “Fully Covered End-to-End”

Mark this complete only when all are true:

- [ ] Backend FIG endpoints and tenant isolation still pass.
- [ ] Data/profile matrix tests still pass.
- [ ] FIG timeline + live sync + idempotent apply is verified.
- [ ] FIG neighborhood expansion UX path is verified.
- [ ] FIG state persistence is verified across reload and graph identity boundaries.
- [ ] FIG frontend e2e exists and passes.
- [ ] Metrics policy is aligned to approved architecture decision.

## Current Overall State

- Backend contract: Complete.
- Data/profile backend regression: Complete.
- Frontend FIG core: Implemented.
- Full end-to-end closure: Not complete yet.
