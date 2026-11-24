# Governance

FAIM-Native is currently maintainer-led. Maintainers are responsible for protecting the native data contracts, security boundaries, documentation quality, and release integrity.

## Decision principles

Technical decisions should favor:

1. raw-data integrity and provenance;
2. tenant isolation and least privilege;
3. deterministic behavior where the contract requires it;
4. backward-compatible API and storage changes;
5. explicit migrations, rollback paths, and operational evidence; and
6. reproducible tests over unsupported performance claims.

## Change process

- Use an issue or pull request for design discussion.
- Keep changes scoped and explain affected contracts.
- Require review for authentication, cryptography, migrations, storage, deployment, and public API changes.
- Update documentation and tests with behavior changes.
- Do not merge changes that introduce secrets, unreviewed data access, or unexplained tenant-boundary changes.

Review ownership across the repository and critical paths (`/deploy/`, `/faim_native/api/middleware/`, and `/faim_native/store/pg/migrations/`) is defined in [`.github/CODEOWNERS`](.github/CODEOWNERS), and pull requests should follow the checklist in [`.github/pull_request_template.md`](.github/pull_request_template.md).

## Releases and security

Release notes identify API changes, database migrations, security fixes, compatibility boundaries, benchmark methodology, and rollback instructions. See [`CHANGELOG.md`](CHANGELOG.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), and [`SECURITY.md`](SECURITY.md).
