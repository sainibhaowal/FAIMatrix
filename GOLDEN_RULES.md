# GOLDEN RULES

Use this file as the universal working rulebook before starting any phase, feature, fix, page, backend change, frontend change, API change, storage change, evolution change, or runtime integration work.

## 1) Start With Plan First

Before implementation, always build a proper plan first.

The plan must clearly answer:

1. What exactly needs to be done.
2. Why it needs to be done.
3. Where it must be done.
4. Which exact files, folders, modules, routes, schemas, APIs, UI paths, services, jobs, tests, and docs will be affected.
5. How it should be implemented in the safest and most accurate way.
6. What dependencies, side effects, integration points, and risks exist.
7. What must not be broken while doing the work.

No coding should start until there is a clear implementation direction.

## 2) Always Work Phase By Phase

Do not mix unrelated work.

For every phase or step:

1. Focus only on that scope.
2. Define exact boundaries.
3. Avoid uncontrolled refactors.
4. Finish the current phase correctly before moving to the next.
5. Wait for approval when the workflow requires approval before implementation.

## 3) Protect Existing System Behavior

Every change must preserve the stability of the existing application.

Always make sure:

1. Existing setup is not broken.
2. Existing connections and integrations are not broken.
3. Existing backend logic is not broken.
4. Existing frontend logic is not broken.
5. Existing auth, tenant isolation, encryption, cryptography, storage, API keys, jobs, worker, evolution, memory, retrieval, and event flows are not weakened.
6. Existing production behavior remains backward compatible unless an explicit approved change says otherwise.

## 4) Know Exact Paths Before Coding

Before implementation, identify the exact file and folder locations.

Always know:

1. Which file must be modified.
2. Which file must not be touched.
3. Which new files are needed.
4. Which routers, repos, models, schemas, services, components, hooks, utilities, and docs are involved.
5. Which tests must be added or updated.

No blind editing.

## 5) Security and Data Safety Are Mandatory

Security is not optional.

Always verify:

1. Auth and authorization remain correct.
2. Tenant isolation remains strict.
3. No secret or sensitive data is leaked.
4. Encryption and cryptography related behavior is not weakened.
5. Rate limiting, validation, and abuse protections remain correct.
6. Unsafe shortcuts are not introduced.
7. Logs, events, and errors do not expose sensitive values.

## 6) Production Grade Means Real Behavior

Do not treat production work like a mock or demo.

Always ensure:

1. Behavior is real, not placeholder-only.
2. UI is backed by real data contracts.
3. Backend semantics are materially implemented, not only logged.
4. Sync and async paths are clearly defined.
5. Failure handling is real.
6. Empty, loading, error, timeout, retry, and degraded modes are handled.

## 7) No Missing Gaps

Before saying a plan is ready or implementation is complete, check for gaps.

Always verify:

1. Functional gaps
2. Integration gaps
3. Security gaps
4. Performance gaps
5. Testing gaps
6. Documentation gaps
7. Operational rollout and rollback gaps

If any gap exists, identify it clearly before claiming readiness.

## 8) Test and Verify Every Phase

Every phase must include testing and verification.

Always define:

1. Unit tests
2. Acceptance or end-to-end tests
3. Regression tests
4. Manual validation steps if needed
5. Performance checks if relevant
6. Security validation if relevant

Never claim completion without verification evidence.

## 9) Documentation Is Part of the Work

Documentation is mandatory, not optional.

Every significant phase should include:

1. Updated implementation docs
2. Updated plan docs if scope changed
3. Updated API or UI specs if contracts changed
4. Updated operational or rollout notes if runtime behavior changed
5. Clear explanation of requested behavior vs effective behavior when relevant

## 10) Safe Change Process

Use this sequence for all serious work:

1. Read and inspect the current codebase state.
2. Build a clear implementation plan.
3. Identify exact files and risks.
4. Verify compatibility with the rest of the system.
5. Get approval when required.
6. Implement in small safe slices.
7. Run tests and validations.
8. Update docs.
9. Re-check for regressions.
10. Only then claim completion.

## 11) Frontend Specific Rules

When working on frontend:

1. Preserve existing design system or product language unless a redesign is intended.
2. UI controls must reflect real backend behavior.
3. Do not create misleading buttons, badges, or states that imply functionality that does not exist.
4. Handle mobile and desktop properly.
5. Handle empty, loading, error, and rate-limit states clearly.
6. Use real data bindings as early as safely possible.
7. Avoid visual changes that damage other screens or existing flows.

## 12) Backend Specific Rules

When working on backend:

1. Define contract truth before wiring frontend to it.
2. Keep additive-first API changes where possible.
3. Preserve tenant and auth boundaries.
4. Keep runtime semantics explicit.
5. Keep idempotency and dedup rules correct.
6. Ensure worker/job behavior is real and observable.
7. Make requested vs effective behavior visible where ambiguity can happen.

## 13) Integration Rules

When a feature touches multiple systems:

1. Trace end-to-end flow first.
2. Define source of truth.
3. Define sync vs async behavior.
4. Define event/version semantics if live updates exist.
5. Define fallback behavior if one dependency fails.
6. Validate upstream and downstream compatibility.

## 14) Completion Criteria

A phase is complete only when all are true:

1. Scope is implemented accurately.
2. Required tests pass.
3. No known critical gap is left open.
4. Docs are updated.
5. Regressions are checked.
6. Behavior is production-safe.
7. You have high confidence the system remains stable.

## 15) Commit and Tag Discipline

After successful completion and verification:

1. Make clear, scoped commits.
2. Do not mix unrelated changes in the same commit when avoidable.
3. Tag only when the phase is truly complete and verified.
4. Do not tag incomplete or unverified work.

## 16) Standard Reusable Instruction Block

Use this as the default instruction pattern before any major task:

1. Build a proper implementation plan first.
2. Maintain code accuracy, structure, security, encryption safety, workflow correctness, and integration stability.
3. Identify exactly what to do, where to do it, how to do it, and what must not break.
4. Verify all exact paths, files, folders, modules, and dependencies before editing.
5. Implement only after the plan is clear and approved when required.
6. Test, verify, document, and regression-check before claiming completion.
7. Commit and tag only after verified success.

## 17) Final Rule

Do not rush.

Clear direction first, safe execution second, verified completion last.
