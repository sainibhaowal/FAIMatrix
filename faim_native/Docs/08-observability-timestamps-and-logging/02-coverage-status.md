# FAIM test coverage status

Updated 2026-11-20.

This repository now has reproducible local coverage commands for both runtimes.
Coverage is measured against source code; untested files are not excluded to
make the percentage look higher.

## Verified baseline

| Surface | Command | Result |
| --- | --- | --- |
| Backend tests | `FAIM_LOCAL_SQLITE=1 python -m pytest -q --disable-warnings` | `1073 passed, 1 skipped` (coverage run emitted `590` resource warnings) |
| Backend coverage | `FAIM_LOCAL_SQLITE=1 python -m pytest --cov=faim_native --cov-report=term-missing -q --disable-warnings` | `1073 passed, 1 skipped, 79% statements, 590 warnings` |
| Frontend unit tests | `pnpm run test:unit` | `20 passed` |
| Frontend unit coverage | `pnpm run test:unit:coverage` | `8.72% statements` |
| Frontend E2E | `PLAYWRIGHT_E2E_JWT=<local test JWT> pnpm run test:e2e` | `58 passed` against the live backend |

The single backend skip is the PostgreSQL backup-drill test, which is
intentionally skipped under SQLite. The PostgreSQL drill is a separate
environment validation and must run against the production-compatible database
when it is available.

## Remaining work

The remaining percentage is real uncovered behavior, not a tooling failure.
This run added contract coverage for deterministic clustering/path reasoning,
implication chaining, versioned query/stat caches, Redis fallbacks, backup
success/failure/retention behavior, invariants, the user repository, raw
encryption/payload delegation, deterministic ANN fallback operations, the
lazy encoding export contract, the events SSE lifecycle, auth/TOTP and account
purge paths, MCP JSON-RPC and scope handling, and embedding/OCR provider
lifecycles. It also disposes the SQLite test engine after each fixture to avoid
leaking test connections. The frontend tranche covers
FIG API authentication/request contracts, graph transforms and scorecards,
timeline reconciliation, profile/persistence policy behavior, and the
realtime SSE event/error contract.

The largest backend gaps remain storage backfill and graph-store modules,
extractor/OCR failure paths, worker branches, and storage/auth middleware
routes. The
frontend gap is larger because the source scope includes dashboards, routes,
controls, manuals, and shared UI; the current unit suite covers the
deterministic API, provider, FIG safety/layout, error, and banner contracts but
not those application surfaces. The 590 warnings are not test failures, but
they must be triaged before a zero-warning release gate is claimed.

Do not add `pragma: no cover`, reduce the source include scope, or convert the
SQLite skip into a pass. Completion requires tests that execute the real branch
and a final run showing 100% for the declared scope.
