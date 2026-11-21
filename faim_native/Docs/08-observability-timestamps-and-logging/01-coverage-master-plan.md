# FAIM complete coverage master plan

Updated 2026-11-20.

## Objective and rules

The objective is 100% measured statement, branch, function, and line coverage
for the declared backend and frontend source scopes, with real tests exercising
the behavior. Coverage exclusions, `pragma: no cover`, deleting source from the
coverage scope, broad mocks that bypass the behavior under test, and converting
the PostgreSQL-only skip into a pass are prohibited.

The final release gate is not satisfied until both of these commands report
100% for their declared scopes and the functional gates remain green:

```bash
FAIM_LOCAL_SQLITE=1 python -m pytest --cov=faim_native --cov-branch \
  --cov-report=term-missing --cov-report=json -q
cd frontend && corepack pnpm run test:unit:coverage
```

The PostgreSQL backup drill remains a separate required environment gate. SQLite
is the deterministic local test database only; it does not prove PostgreSQL
backup compatibility.

## Current inventory

The source scope contains 215 Python files under `faim_native/` and 180
TypeScript/TSX files under `frontend/src/`. The test inventory contains 200
Python test files, 8 frontend unit files, and 10 Playwright E2E files.

Current measured baseline:

| Surface | Evidence | Current result |
| --- | --- | --- |
| Backend | Full pytest + coverage run | 1073 passed, 1 skipped, 79% statements |
| Frontend unit | Vitest + V8 coverage | 20 passed, 8.72% statements |
| Frontend E2E | Playwright against live backend | 58 passed |
| Static gates | Ruff, Black, Mypy, Bandit, ESLint, Prettier, TypeScript | Passing |

The baseline is not a 100% release claim. The one backend skip is the
PostgreSQL backup drill under SQLite. The coverage run also exposes resource
warnings that must be reduced before a zero-warning gate is claimed.

## File and folder allocation

Every source folder is assigned to a coverage tranche. Tests must be placed in
the existing corresponding test area unless a cross-cutting contract belongs
in `tests/unit/test_coverage_tranche_core.py` or a frontend contract belongs in
`frontend/tests/unit/`.

### Backend allocation

| Tranche | Production folders/files | Test location and evidence |
| --- | --- | --- |
| B1 API foundation | `faim_native/api/app.py`, `api/deps.py`, `api/contracts/`, `api/fig_graph_core.py` | `tests/unit/` plus router/acceptance tests; cover startup, dependency failures, contracts, graph surface validation |
| B2 security and auth | `api/middleware/auth.py`, `api/middleware/jwt.py`, `api/middleware/security.py`, `api/middleware/ratelimit.py`, `api/routers/auth.py`, `api/routers/oauth.py`, `runtime/api_key_bootstrap.py`, `runtime/secrets.py` | existing auth/security tests plus new isolated request tests; cover invalid credentials, tenant mismatch, rate limits, rotation, expiry, and safe failure paths |
| B3 API resources | `api/routers/api_keys.py`, `events.py`, `health.py`, `metrics.py`, `node.py`, `query.py`, `reasoning.py`, `reranker.py` | router unit/acceptance tests; every status code, validation error, auth boundary, pagination, and dependency failure |
| B4 ingestion and storage API | `api/routers/ingest.py`, `api/routers/storage.py`, `api/routers/memory.py`, `api/services/memory_service.py`, `api/validators/input_limits.py` | API tests with SQLite and transactional fakes; cover upload, chunking, idempotency, queue modes, quotas, rollback, retention, encrypted payloads, and tenant isolation |
| B5 provider and MCP API | `api/routers/embedding_providers.py`, `api/routers/ocr_providers.py`, `api/routers/mcp.py`, `encoding/embedding_providers.py`, `perception/extract/ocr_service.py` | provider contract tests with deterministic external-service adapters; cover discovery, timeout, malformed response, unavailable provider, API-key redaction, and fallback |
| B6 retrieval and indexes | `core/query/`, `core/reasoning/`, `index/`, `lexical/`, `encoding/`, `domain/` | existing retrieval tests plus focused branch tests; cover empty graph, ties, dimension errors, ANN unavailable/available, lexical+dense fusion, rerank, multilingual and explainability paths |
| B7 perception | `perception/chunking.py`, `perception/extract/`, `perception/packetize.py`, `perception/router.py`, `perception/validate.py`, `encoding/OCR/`, `encoding/adapters/`, `encoding/layout/` | fixture-based document tests for text, HTML, PDF/image adapter boundaries, OCR success/failure, malformed documents, limits, and cleanup |
| B8 orchestration | `orchestration/`, `orchestration/jobs/`, `orchestration/perf/` | worker/job tests with transaction fakes and retry clocks; cover claim, lease, rollback, retry, dead-letter, autonomy isolation, cancellation, and metrics |
| B9 runtime/config | `runtime/config.py`, `runtime/context.py`, `runtime/feature_flags.py` | environment matrix tests; cover defaults, invalid values, production safety, feature combinations, tenant context, and request scope |
| B10 storage implementation | `store/raw/`, `store/crypto/`, `store/journal/`, `store/pg/session.py`, `store/pg/migrate.py`, `store/pg/models_*.py`, `store/pg/repos/` | SQLite unit tests, PostgreSQL integration tests, and repository contract tests; cover every repository method, migration branch, encryption rotation, journal cursor, backup, and cleanup |
| B11 legacy/zero-coverage modules | `store/pg/graph_store.py`, `store/pg/backfill_cognitive.py`, `store/pg/repos/payload_store.py`, `store/pg/repos/__init__.py` | first determine whether each is live, compatibility-only, or dead; live code gets behavior tests, compatibility code gets contract tests, dead code is removed only with dependency evidence and user-owned changes preserved |
| B12 cognitive/evolution | `core/dynamics/`, `core/cognitive/`, `core/learning/`, `core/metrics/`, `core/operators/`, `core/temporal/`, `core/monitoring/` | deterministic model/property tests; cover empty inputs, invariants, conflicts, feedback, evolution safeguards, metrics overflow, and disabled-autonomy paths |

### Frontend allocation

| Tranche | Production folders/files | Test location and evidence |
| --- | --- | --- |
| F1 shared libraries | `frontend/src/lib/` (17 files), `frontend/src/types/`, `frontend/src/contexts/` | `frontend/tests/unit/`; cover every exported function, auth/header behavior, safeFetch errors, realtime SSE, FIG transforms, persistence, and provider discovery |
| F2 middleware and route handlers | `frontend/src/middleware.ts`, `frontend/src/app/api/**/route.ts` | unit tests with request/response fixtures; cover auth injection, missing/invalid session, API proxy errors, provider/reranker routes, and stream route behavior |
| F3 app shells and auth | `frontend/src/app/layout.tsx`, `(admin)/layout.tsx`, `(marketing)/layout.tsx`, `app/auth/**`, `app/oauth/**`, `app/api/auth/**` | React Testing Library tests; cover loading, unauthenticated, authenticated, error, redirect, and accessibility states |
| F4 dashboard routes | `frontend/src/app/(admin)/dashboard/**` including API keys, billing, embedding providers, evolution, graph, journal, MCP, profile, providers, storage | route-level component tests plus existing Playwright tests; cover loading/empty/success/error, mutations, tenant-safe display, and retry states |
| F5 graph and evolution components | `frontend/src/components/graph/`, `components/evolution/`, `components/reasoning/`, `components/dashboard/` | focused component tests with deterministic fixtures and user interactions; E2E remains the integration proof |
| F6 layout, shared, UI | `components/layout/`, `components/manuals/`, `components/shared/`, `components/ui/`, `components/brand/` | parameterized accessibility and interaction tests for every exported component and branch |
| F7 marketing/docs | `app/(marketing)/**`, `components/landing/**` (42 files) | smoke/render tests for every page and component variant; verify links, feature flags, responsive branches, and legal content |
| F8 integration | `frontend/e2e/*.spec.ts` and `playwright.config.ts` | keep the 58 live-backend tests green; add coverage for any route/component branch not reachable through unit tests |

## Execution order

1. Freeze the inventory and create a machine-readable coverage manifest from
   `coverage.json` and `frontend/coverage/coverage-summary.json`.
2. Resolve the backend zero-coverage and lowest-coverage modules first:
   payload store, cognitive backfill, graph store, extractor/OCR, auth/MCP,
   storage, worker, and Qdrant.
3. Close backend router and orchestration branches in dependency order so
   tests exercise real contracts instead of mocking the router itself.
4. Cover frontend libraries and route handlers before rendering large pages;
   then add component tests in dashboard, graph, evolution, layout/UI, and
   marketing groups.
5. Run each tranche with its targeted test command, then run the complete
   backend and frontend suites. No tranche is accepted if it reduces coverage,
   introduces a skipped test, or weakens an auth/tenant assertion.
6. Resolve SQLite resource warnings and run the PostgreSQL backup drill in its
   supported environment.
7. Run the final static, unit, coverage, E2E, security, and diff checks. Only
   after the exact output is 100% may the repository be described as fully
   covered.

## Safety and non-regression requirements

- Tests must never disable authentication or tenant isolation in production
  code. Test-only bypasses must be explicit, local, and impossible to activate
  through production configuration.
- Encryption, key derivation, API-key hashing, JWT validation, and redaction
  tests must assert both success and failure paths.
- External providers, Qdrant, Redis, OCR, and PostgreSQL use contract fakes for
  deterministic unit tests plus real integration gates where available.
- Existing integrations, routes, schemas, jobs, storage, journal events,
  evolution, and frontend behavior must remain backward compatible.
- Do not commit generated coverage directories, local secrets, E2E tokens, or
  benchmark data. Preserve unrelated user changes in the dirty worktree.

## Evidence required for completion

The final report must include the exact commands, exit codes, test counts,
coverage totals, remaining skips/warnings, changed files, and a clean diff
check. It must explicitly state any environment-only gate that was not run.
Until all of those conditions are met, the status remains “in progress”, not
“100% complete” or “production-ready”.
