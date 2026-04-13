# 11_FigView_Validation_Evidence_Snapshot

Date: 2026-04-13
Purpose: Evidence snapshot supporting current coverage vs open gaps.

## Test Evidence (Executed)

FIG backend tests:

- tests/acceptance/test_AT_fig_graph_api_surface.py
- tests/acceptance/test_AT_fig_graph_tenant_isolation.py
- Result: 14 passed

FIG unit mapping:

- tests/unit/test_fig_graph_mapping.py
- Result: 12 passed

Data/profile matrix acceptance:

- tests/acceptance/test_AT_profile_persist_storage_matrix.py
- tests/acceptance/test_AT_profile_persist_evolve_matrix.py
- Result: 13 passed

## Code Evidence Snapshot

Backend endpoints and wiring exist:

- faim_native/api/routers/graph.py
- faim_native/api/app.py
- faim_native/api/routers/__init__.py

Frontend FIG implementation exists:

- frontend/src/app/(app)/dashboard/graph/page.tsx
- frontend/src/components/graph/FigViewPage.tsx
- frontend/src/components/graph/FigCanvas.tsx
- frontend/src/components/graph/FigControls.tsx
- frontend/src/components/graph/FigInspector.tsx
- frontend/src/components/graph/FigRelationPanel.tsx
- frontend/src/components/graph/FigLegend.tsx
- frontend/src/components/graph/FigMetricsBar.tsx
- frontend/src/components/graph/FigSearch.tsx
- frontend/src/lib/figViewApi.ts
- frontend/src/lib/figViewSafety.ts
- frontend/src/lib/figViewGraphTransform.ts
- frontend/src/lib/figViewLayout.ts
- frontend/src/types/figView.ts

## Gap Evidence Snapshot

Open/partial areas observed:

- Timeline control path is present but functional toggle/apply flow is incomplete in page composition.
- Neighborhood API function is defined but not fully used in main FigView exploration flow.
- View-state persistence helper functions exist, but full save/restore integration is not complete.
- Dedicated frontend FIG e2e spec is absent in frontend/e2e.
- Current metrics UI computes D/H/lambda client-side, while plan wording expects backend-verification-only policy.

## Practical Conclusion

As of this snapshot:

- Backend + data/profile validation is strong.
- Frontend FIG is feature-rich but not yet fully closed against every end-to-end item in the implementation plan.
