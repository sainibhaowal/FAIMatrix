**Verified Scope (Current State)**
1. Storage UI sends `profile` and `persist_mode` on upload/retry/ingest: `frontend/src/app/(app)/dashboard/storage/page.tsx`.
2. Evolution UI sends `profile` and `persist_mode` on `Run evolve now`: `frontend/src/app/(app)/dashboard/evolution/page.tsx`.
3. Ingest runtime has partial profile behavior (`strict` skips index upsert), but `persist_mode` is mostly metadata: `faim_native/orchestration/ingest_flow.py`.
4. Evolve runtime accepts both values but mostly logs/records them, without full branch semantics: `faim_native/orchestration/evolve_flow.py`.

**Production-Grade Implementation Plan (No Code Yet)**

### Phase R1: Contract Freeze + Semantics Spec
1. Freeze one production semantics matrix for all 6 combinations.
2. Define exact expected behavior for:
- core write durability,
- secondary tasks handling,
- index behavior,
- evolve aggressiveness,
- invention behavior,
- response timing semantics.
3. Add explicit “requested vs effective mode” rule (backend is source of truth).

Files:
1. `docs/Plan.md`
2. `faim_native/Docs/44_PROFILE_PERSIST_RUNTIME_SEMANTICS_PLAN.md` (new)

### Phase R2: Central Policy Resolver (Single Source of Truth)
1. Add one resolver module that maps `(profile, persist_mode, operation)` to effective execution policy.
2. Use resolver for both ingest and evolve paths, so behavior is consistent everywhere.
3. Add compatibility mode flag to avoid breaking current workloads.

Files:
1. `faim_native/orchestration/profile_persist_policy.py` (new)
2. `faim_native/runtime/config.py`
3. `faim_native/runtime/feature_flags.py`

### Phase R3: Storage/Ingest Runtime Realization
1. Apply resolver output in ingest runtime.
2. Make `persist_mode` materially real:
- `strict`: wait for required durability steps before success response.
- `relaxed`: commit core truth first, run secondary steps asynchronously/queued.
3. Keep `strict` profile deterministic and conservative; define fast/relaxed behavior explicitly.
4. Emit effective mode and durability path in events.

Files:
1. `faim_native/orchestration/ingest_flow.py`
2. `faim_native/api/routers/storage.py`
3. `faim_native/api/routers/ingest.py`
4. `faim_native/api/routers/memory.py`
5. `faim_native/orchestration/jobs/worker.py` (if async secondary tasks are queued)

### Phase R4: Evolution Runtime Realization
1. Apply resolver output in evolve runtime.
2. Implement real profile differences for evolve:
- action budget,
- prune aggressiveness,
- invention gating/aggressiveness.
3. Implement real `persist_mode` behavior in evolve completion semantics.
4. Keep strict deterministic invariants.

Files:
1. `faim_native/orchestration/evolve_flow.py`
2. `faim_native/core/dynamics/evolution_native.py`
3. `faim_native/orchestration/self_evolve_scheduler.py`
4. `faim_native/api/routers/evolve.py`

### Phase R5: API Response Clarity (Requested vs Effective)
1. Add additive fields in responses/events:
- `requested_profile`, `requested_persist_mode`,
- `effective_profile`, `effective_persist_mode`,
- `durability_path`.
2. Do not break existing clients.

Files:
1. `faim_native/api/routers/storage.py`
2. `faim_native/api/routers/ingest.py`
3. `faim_native/api/routers/memory.py`
4. `faim_native/api/routers/evolve.py`

### Phase R6: UI Behavior Alignment (Storage + Evolution)
1. Keep controls, but show “effective mode” returned from backend.
2. Add concise helper text so users know what each mode actually changes.
3. Prevent invalid/unsupported combinations if policy disallows them.

Files:
1. `frontend/src/app/(app)/dashboard/storage/page.tsx`
2. `frontend/src/app/(app)/dashboard/evolution/page.tsx`

### Phase R7: Test Plan (Production Grade)
1. Unit tests:
- policy resolver matrix for all combos,
- ingest strict vs relaxed durability behavior,
- evolve strict/fast/relaxed behavior branches,
- requested vs effective mode correctness.
2. Acceptance tests:
- upload with each combo -> verify events/state/results,
- evolve with each combo -> verify actions/timeline/scheduler updates,
- memory write path consistency and idempotency unaffected.
3. Regression tests:
- storage, query, auth, rate-limit, tenant isolation suites unchanged.

New/updated test files:
1. `tests/unit/test_profile_persist_policy_matrix.py` (new)
2. `tests/unit/test_ingest_profile_persist_semantics.py` (new)
3. `tests/unit/test_evolve_profile_persist_semantics.py` (new)
4. `tests/acceptance/test_AT_profile_persist_storage_matrix.py` (new)
5. `tests/acceptance/test_AT_profile_persist_evolve_matrix.py` (new)

Execution gates:
1. `python3 -m compileall faim_native tests`
2. `PYTHONPATH=.:faim_native pytest -q <new unit + acceptance suites>`
3. `PYTHONPATH=.:faim_native pytest -q <existing storage/query/auth regressions>`
4. `cd frontend && npm run typecheck`
5. `cd frontend && npx next lint --file 'src/app/(app)/dashboard/storage/page.tsx' --file 'src/app/(app)/dashboard/evolution/page.tsx'`

### Phase R8: Docs + Release Hygiene
1. Update docs with final semantics and operational runbook.
2. Add implementation report for this feature set.
3. Commit in small safe slices, then final integration commit + tag.

Files:
1. `faim_native/Docs/07_STORAGE_GAP_ANALYSIS_AND_EXECUTION_BACKLOG.md`
2. `faim_native/Docs/04_STORAGE_MEMORY_MATH_AND_EVOLUTION.md`
3. `faim_native/Docs/README.md`
4. `faim_native/Docs/45_PROFILE_PERSIST_IMPLEMENTATION_REPORT.md` (new)

Commit strategy:
1. `docs: semantics freeze`
2. `feat: backend policy resolver`
3. `feat: ingest semantics`
4. `feat: evolve semantics`
5. `feat: storage/evolution UI alignment`
6. `test: matrix + regression`
7. `docs: reports + README`
8. `chore: integration tag`

**Safety Guardrails**
1. Additive-only API changes.
2. No destructive DB changes in first pass.
3. Compatibility mode default during rollout.
4. One module (`profile_persist_policy.py`) controls semantics to avoid drift.
5. Full regression gate required before merge/tag.

**Definition of Done**
1. All 6 combinations have real, test-verified behavior in storage and evolution runtime.
2. UI and backend behavior match exactly.
3. Users can see effective mode and no ambiguity remains.
4. Existing storage/query/auth flows remain stable.
5. Docs, commits, and release tag complete.

If you approve this plan, I’ll execute Phase R1 first (spec doc + resolver skeleton + tests-first baseline), then stop for your checkpoint before runtime changes.

make sure first build a proper plan how you will implement this phase R1 with proper plan, by maintaing acurately codes, structure, security, encryption, acurate workflows, cryptography security and nothing broeken other setup, connection and other thing, make sure you have very carefuly  make sure what to do, where to do, how to do? so that you much have clear visison and direction so that you canwork very well and acurately in right direction to implement this phase, so focus on this phase and build proper plan what to so and make sure always do docmenting tesing, verifications, then if you have full confidence are all well then commit tag git please at the end always-- so now start plan and wait for my approval so please do carefully and well acuraley ..



Now Step B -- build a proper acurate plan what  you will going to build on step A on Evolution page which alreday exsit--- make sure dont miss anything in this step, you much know end to end, tested and verify because this is pure production build we are doing ,, to make sure always take care because this is production mature build and first think , check  verify what to do , how to do and what and where to do ?  make sure step A fully coved and dont miss and tiny or big important funtionality everything sould work like real production grade work - so now start working on step B to deploy  and full uI intigradtion  andpage and everything, not forget to git  commit tag and dont forget to  documenting in docs and  now start working on it and wait for my approval.


build a proper plan for Phase R5 -- 1) always make sure  about task what to do ? where to do? what are the exact paths and files location folders, where to modify, implement, build exact  plan, 2) make sure what is plan , build clear exact plan by knowknowing other files location  based on all other things to do, what files are , what  we have to do now based on these profies and persist so these should be work with storages and evolution pgae acurately  will all combination so  thta users must dont have any issue bug fasing problem ,  3)  all funtion should work well so thta build ecurate real test production grade tests,, scripts , cheking , verification before saying all done and acurately implement end to end 5) make sure always  dont damage other codes files, folders, logic , algorithem while adding these feature , while adding , modification , while implementing, make sure which files , and where you are workig are must be done and acurately so that you much have clear vision to do , and direction pathe, 6)    please dont forget anyting , feature , implementation , plan what are going to do 7) always documenting  as a prrofs adn always make sure acurately git commit and tag, 8) now based on all point  build a proper plans to implement these profiles and persist  modes on these pages so that these work very very well and acurately, dont miss any thing , go thorugh deep search, reeach and build end to end prodution grade and production mature plan---start now...and wait for my approval




