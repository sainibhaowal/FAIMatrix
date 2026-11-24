# CI, releases, and remote deployment

FAIM-Native uses GitHub Actions for automated pull-request verification, manual semantic release tagging, and manual remote container deployment.

## Continuous integration (`.github/workflows/ci.yml`)

- Runs automatically on pull requests targeting `main` and supports manual execution via `workflow_dispatch`.
- Runs independent verification jobs in parallel: backend unit/integration checks, Python and shell static checks, frontend typecheck/lint/unit checks, Docker Compose configuration validation, and repository security auditing.
- Protect `main` in repository branch settings by requiring CI status checks before merging.

## Semantic releases (`.github/workflows/release.yml`)

This workflow is manual-only (`workflow_dispatch`). Run it with `dry_run=true` first to review the calculated version and release notes, then run with `dry_run=false` to publish.

- Release rules are defined in [`.releaserc.json`](../../../.releaserc.json) using Conventional Commits (`feat:` for minor versions, `fix:` for patch versions, and `BREAKING CHANGE:` for major versions).
- A successful non-dry-run creates a `vX.Y.Z` Git tag, publishes GitHub release notes, and updates [`CHANGELOG.md`](../../../CHANGELOG.md).
- Release creation and remote deployment are decoupled: tagging a release does not automatically deploy to any remote host.

## Manual remote deployment (`.github/workflows/deploy-vps.yml`)

Remote deployment is manual-only and requires `confirm=true` (and optional reviewer approval when a GitHub `production` environment protection rule is enabled).

1. GitHub Actions builds the backend and frontend container images with BuildKit and pushes them to the configured container registry (GHCR) under an immutable tag.
2. Deployment descriptors are synced to the target host at `VPS_PATH`.
3. The host pulls the exact immutable image tag, keeps stateful data services (PostgreSQL, Redis, Qdrant) running, applies schema migrations, and updates API, worker, and frontend services with `docker compose ... up -d --wait`.
4. The workflow validates `/health`, `/ready`, `/version`, and `/` with HTTP 2xx responses without running `docker compose down` or destructive volume prunes.
5. Compose service replacement on a single host is a controlled rolling-style update; high availability requires an external multi-host or blue/green topology.

### Required GitHub configuration

Configure a `production` GitHub environment with these scoped secrets:

- `VPS_HOST`: Target host name or address.
- `VPS_USER`: Restricted non-root deployment user.
- `VPS_PORT`: SSH port (defaults to `22` if omitted).
- `VPS_PATH`: Application deployment directory on the remote host.
- `VPS_SSH_KEY`: Private deploy key in OpenSSH format.
- `VPS_KNOWN_HOSTS`: Pinned `ssh-keyscan` host key entry for the target server.

The deployment job uses the short-lived `GITHUB_TOKEN` for registry authentication and does not store a long-lived registry PAT on the remote host.

### Operator runtime configuration and preflight

Keep host-specific environment secrets and persistent runtime data directories outside source control on the target host. For DB-backed API-key authentication, keep `TENANT_KEYS_JSON={}` and use a one-time bootstrap flow as documented in [production hardening](../11-security/02-production-hardening.md) so plaintext bootstrap keys are imported as Argon2id hashes and never retained in long-running environments.

Run deployment preflight validation before applying remote updates:

```bash
FAIM_IMAGE_PREFIX=ghcr.io/<owner>/<repo> \
FAIM_IMAGE_TAG=preflight \
./scripts/vps_deploy_ci.sh --preflight-only
```

If deploying behind an external reverse proxy, join the configured external gateway Docker network separately and manage TLS, DNS, and gateway routes outside this automated application deployment workflow.
