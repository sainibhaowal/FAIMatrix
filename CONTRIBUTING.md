# Contributing to FAIM-Native

Thank you for improving FAIM-Native. The project is experimental and spans a memory graph engine, API, worker runtime, dashboard, security boundary, and operational tooling. Small, well-scoped changes are easier to review and safer to deploy.

## Before you contribute

- Read the root [`README.md`](README.md) and the relevant architecture or security guide.
- Do not include secrets, credentials, private raw data, generated runtime databases, or production environment files.
- Make sure you have the right to submit every line, asset, dataset, and dependency change in your contribution.
- Flag migrations, API contract changes, tenant-isolation effects, provenance changes, and cryptographic changes clearly in the pull request.

## Development checks

For Python changes:

```bash
python -m pytest -q
ruff check faim_native tests
mypy faim_native
```

For frontend changes:

```bash
cd frontend
npm ci
npm run typecheck
npm run test:unit
npm run format:check
```

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
