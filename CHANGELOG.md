# Changelog

All notable changes to FAIM-Native should be recorded here. This project is still evolving, so historical stage reports under `docs/` are implementation records rather than stable release guarantees.

## Unreleased

### Documentation and project policy

- Added Apache License 2.0 licensing for source code.
- Added CC BY 4.0 policy for original documentation and non-code assets.
- Added trademark, third-party notice, contribution, security, conduct, and governance guidance.
- Added a canonical README hero asset under `assets/`.
- Added explicit experimental-use boundaries and research-positioning language.
- Added public-facing experimental status, research positioning, and roadmap documents.

### CI/CD

- Added parallel pull-request and manual CI quality checks.
- Added manual semantic-release configuration with `vX.Y.Z` tags.
- Added manual GHCR image publishing and guarded VPS deployment workflow.
- Added registry Compose override and non-volume Docker cleanup deployment script.

### Release discipline

Future entries should include:

- user-visible changes;
- API and storage contract changes;
- migrations and rollback notes;
- security impact;
- test and benchmark evidence; and
- known limitations.
