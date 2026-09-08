# [0.6.0](https://github.com/sainibhaowal/FAIMatrix/compare/v0.5.2...v0.6.0) (2026-09-08)


### Bug Fixes

* keep production API responsive and label alpha preview ([bbe360f](https://github.com/sainibhaowal/FAIMatrix/commit/bbe360f06ff8d0193cdf4a352a0672d01c52bdc0))
* **marketing:** align landing claims with evidence ([06ca55e](https://github.com/sainibhaowal/FAIMatrix/commit/06ca55e0efc6697d6b709eb6e0f8a9b0d530d535))


### Features

* **marketing:** add evidence-led systems comparison ([4e332ad](https://github.com/sainibhaowal/FAIMatrix/commit/4e332ad7dceac7e1f8bd741e0aecb645b96e6655))

## [0.5.2](https://github.com/sainibhaowal/FAIMatrix/compare/v0.5.1...v0.5.2) (2026-09-08)


### Bug Fixes

* isolate VPS caddy upstream names ([320b993](https://github.com/sainibhaowal/FAIMatrix/commit/320b9936ae475f820fcee466ef78db9fc5839dc2))
* point VPS frontend proxy at unique API service ([279f5dd](https://github.com/sainibhaowal/FAIMatrix/commit/279f5ddf9b5e42f9ea143f0bad9d264c8ef98cbd))

## [0.5.1](https://github.com/sainibhaowal/FAIMatrix/compare/v0.5.0...v0.5.1) (2026-09-08)


### Bug Fixes

* create sqlite parent directories for clean test runs ([4703023](https://github.com/sainibhaowal/FAIMatrix/commit/4703023fc7c944ec689dda065dc4f843d08877ab))
* harden production deployment and memory runtime ([499b9d5](https://github.com/sainibhaowal/FAIMatrix/commit/499b9d52fdc5b60eb674ec3cff9ec313a63c8651))
* track frontend libraries and isolate CI test databases ([62cc956](https://github.com/sainibhaowal/FAIMatrix/commit/62cc95607ae30112e64e77ebbf6333867c79d8b3))
* use frozen pnpm installs in frontend CI and image ([b62167b](https://github.com/sainibhaowal/FAIMatrix/commit/b62167be0fdcae57ff74cd93daccce1c5078ef3b))

# Changelog

All notable changes to FAIM-Native should be recorded here. This project is still evolving, so historical stage reports under `docs/` are implementation records rather than stable release guarantees.

## Unreleased

### Reliability and UI

- Run readiness and pipeline diagnostics in FastAPI's synchronous worker pool,
  and use the production gunicorn worker configuration so a slow graph or
  storage operation cannot stall the API liveness path.
- Correct the dashboard pipeline-stat request to use the authenticated
  `/api/v1/pipeline/stats` contract.
- Label the public landing page as the FAIMATRIX project experiment alpha
  research preview; capability and performance claims remain subject to
  validation.

### Documentation and project policy

- Added Apache License 2.0 licensing for source code.
- Added CC BY 4.0 policy for original documentation and non-code assets.
- Added trademark, third-party notice, contribution, security, conduct, and governance guidance.
- Added a canonical README hero asset under `assets/`.
- Added explicit experimental-use boundaries and research-positioning language.
- Added public-facing experimental status, research positioning, and roadmap documents.
- Expanded README with implementation-grounded end-to-end, ingest, query, evolution, and deployment diagrams.
- Added a detailed runtime component inventory and boundary document under `docs/`.

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
