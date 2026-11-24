# Contributing to FAIM-Native

Thank you for contributing to FAIM-Native. The repository spans a native memory graph engine, FastAPI control plane, durable worker runtime, Next.js workspace, security boundary, and benchmark/operational tooling. Small, well-scoped changes are easier to review and safer to deploy.

## Before you contribute

- Read the root [`README.md`](README.md), [`GOVERNANCE.md`](GOVERNANCE.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md), and the relevant architecture or security guide.
- Do not include secrets, credentials, private raw data, generated runtime databases, or production environment files.
- Make sure you have the right to submit every line, asset, dataset, and dependency change in your contribution.
- Flag migrations, API contract changes, tenant-isolation effects, provenance changes, and cryptographic changes clearly in the pull request.

## Development checks

For Python changes:

```bash
python -m pip install -r requirements-quality.txt
FAIM_LOCAL_SQLITE=1 python -m pytest -q
FAIM_LOCAL_SQLITE=1 python -m pytest --cov=faim_native --cov-report=term-missing -q
ruff check faim_native tests
mypy faim_native
black --check .
bandit -r faim_native faim-benchmarks/faim_benchmarks scripts -ll
```

`FAIM_LOCAL_SQLITE=1` forces isolated, file-backed SQLite databases for local
tests even when a developer shell has a PostgreSQL `DATABASE_URL` configured.
It clears only the test database selectors and never changes production
credentials. The PostgreSQL backup/restore drill remains a separate production
validation because SQLite cannot execute `pg_dump` or restore PostgreSQL
extensions.

The Bandit command is the production-code gate: `-ll` requires zero medium- or
high-severity findings. Test assertions and generated/runtime data are not
production attack surfaces and are validated by the test suite and repository
ignore rules separately.

For frontend changes:

```bash
cd frontend
corepack pnpm install --frozen-lockfile
corepack pnpm run typecheck
corepack pnpm run test:unit
corepack pnpm run test:unit:coverage
corepack pnpm run format:check
```

`test:unit:coverage` uses the pinned V8 provider and reports all TypeScript
and TSX application code under `frontend/src`. Browser journeys remain a
separate Playwright gate; neither unit coverage nor E2E success is a substitute
for the other.

Run the applicable end-to-end, acceptance, Docker, and security checks before merging. If a check cannot run locally, explain why and include the closest available evidence.

## Pull requests

Describe:

1. what changed and why;
2. which user-visible, API, storage, or operational contracts are affected;
3. how the change was tested;
4. whether documentation, migration, rollback, or security updates are required; and
5. any known limitations or follow-up work.

Do not commit directly to `main`. Use a branch and pull request.

## Contribution licensing

Unless you explicitly state otherwise at the time of submission, source-code contributions are submitted under the Apache License 2.0 and documentation or original non-code asset contributions under CC BY 4.0. You retain ownership of your contribution, subject to the rights granted by those licenses.

By submitting work, you confirm that you have the authority to grant these permissions and that the contribution does not knowingly include material whose license is incompatible with the applicable project license.

This project currently does not require a separate Contributor License Agreement. That policy may change for a future legal entity or commercial distribution and would be announced before it applies.
