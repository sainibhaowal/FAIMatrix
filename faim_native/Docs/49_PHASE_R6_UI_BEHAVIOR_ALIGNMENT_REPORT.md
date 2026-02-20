# 49 - Phase R6 UI Behavior Alignment Report

Date: 2026-02-20  
Owner: FAIM Native Runtime  
Status: Completed

## Objective

Align Storage and Evolution UI behavior with R5 runtime/API semantics by making requested vs effective mode clarity visible in the UI, adding user-facing mode helper text, and enforcing invalid/unsupported mode guards in action paths.

## Scope Delivered

1. Storage page now shows requested mode helper context and displays effective mode/durability returned by backend for queue items and ingest actions.
2. Evolution page now shows requested mode helper context and displays effective mode/durability for manual evolve outcomes.
3. Evolution timeline summaries now include mode/durability details for `EVOLUTION_COMPLETE` and `EVOLUTION_SKIPPED` payloads when provided.
4. UI action guards now block unsupported combinations through shared policy resolver checks.
5. Additive-only UI changes; no backend contract break.

## Files Updated

1. `frontend/src/app/(app)/dashboard/storage/page.tsx`
2. `frontend/src/app/(app)/dashboard/evolution/page.tsx`
3. `frontend/tests/e2e/storage-phase-f.spec.ts`
4. `frontend/e2e/storage-r6.spec.ts` (new)
5. `frontend/e2e/evolution-r6.spec.ts` (new)
6. `faim_native/Docs/README.md`

## Implementation Notes

### 1) Storage UI alignment

1. Added mode policy helper integration using `resolveUiModePolicy(...)`, `getProfileHelper(...)`, `getPersistHelper(...)`.
2. Added requested/effective/durability fields to frontend response types for upload batch/status and ingest action payloads.
3. Queue items now store and render backend-returned mode clarity:
   - `requested_profile`
   - `requested_persist_mode`
   - `effective_profile`
   - `effective_persist_mode`
   - `durability_path`
4. Added UI guard handling for unsupported mode combinations in:
   - file enqueue path
   - retry path
   - ingest/retry file actions
5. Disabled mode-sensitive buttons when current combination is unsupported.

### 2) Evolution UI alignment

1. Extended evolve response type coverage to include R5 additive clarity fields and completion metadata.
2. Added mode helper text in controls and unsupported-combination guard before `Run evolve now`.
3. Latest run outcome now surfaces requested/effective/durability text from backend.
4. Timeline summaries now include mode/durability context from event payloads for evolve complete/skip events.

### 3) Test alignment

1. Existing storage Phase-F e2e mocks were enriched with requested/effective/durability fields.
2. Added active Playwright specs (under configured `frontend/e2e` testDir):
   - `storage-r6.spec.ts`
   - `evolution-r6.spec.ts`

## Verification Evidence

1. Frontend typecheck:
```bash
cd frontend
npm run typecheck
```
Result: pass.

2. Targeted active Playwright suite:
```bash
cd frontend
npm run test:e2e -- storage-r6.spec.ts evolution-r6.spec.ts
```
Result: `2 passed`.

3. Frontend lint status:
```bash
cd frontend
npm run lint
```
Result: fails with pre-existing unrelated lint issues outside Phase R6 scope (dashboard marketing/legacy pages), no new R6-specific lint blocker identified.

## Safety Notes

1. UI-only behavior alignment; no schema changes.
2. No auth/tenant isolation logic changes.
3. No crypto/encryption path changes.
4. No breaking API contract changes; frontend consumes additive fields defensively.

