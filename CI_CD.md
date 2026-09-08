# CI, releases, and VPS deployment

FAIM-Native uses GitHub Actions for review gates, manual releases, and manual production deployment. The workflows are intentionally conservative because this repository is still an experimental research system.

## Workflow behavior

### `CI` — `.github/workflows/ci.yml`

- Runs automatically for pull requests targeting `main`.
- Can be started manually with `workflow_dispatch`.
- Does not run for every ordinary push to `main`.
- Runs independent jobs in parallel: backend tests, Python/shell checks, frontend quality checks, Compose validation, and the repository security audit.
- Configure the branch rule for `main` to require the CI jobs before merging.

The frontend formatting check is not currently a required gate because the repository has pre-existing formatting drift. It should be promoted to a required check after that backlog is deliberately cleaned up.

## Semantic releases

### `Semantic release` — `.github/workflows/release.yml`

This workflow is manual-only. Run a dry run first, review the calculated version and notes, then run it again with `dry_run=false`.

The release configuration is in [`.releaserc.json`](.releaserc.json). Conventional `feat:` commits produce a minor release and `fix:` commits produce a patch release; `BREAKING CHANGE:` produces a major release. A successful release creates a `vX.Y.Z` Git tag, GitHub release notes, and updates `CHANGELOG.md`. If the commit range contains no releasable Conventional Commit, semantic-release exits successfully but publishes nothing; review the workflow log for “no release is published”. Release and VPS deployment are separate manual workflows; publishing a release does not implicitly SSH to the VPS.

The earlier documentation commit was intentionally pushed without a tag. Future tags are created only when this manual release workflow is run successfully.

## Manual VPS deployment

### `Deploy research VPS` — `.github/workflows/deploy-vps.yml`

This workflow is also manual-only and requires `confirm=true`. GitHub environment
protection rules may add an approval gate when the repository plan supports it;
this repository currently has a `main`-only production branch policy and no
reviewer rule. An unconfirmed run fails explicitly and does not silently appear
successful.

1. GitHub Actions builds the backend image and frontend image with BuildKit.
2. Images are pushed to GHCR with an immutable commit-based or manually supplied tag.
3. The deployment descriptors are copied to the configured VPS.
4. The VPS authenticates to GHCR and pulls that exact tag.
5. PostgreSQL, Redis, and Qdrant are kept running; migrations run before application replacement.
6. API, worker, and frontend are updated with Compose `--wait` and without `docker compose down`.
7. `https://faimatrix.com` is checked at `/health`, `/ready`, `/version`, and `/`; every endpoint must return an actual 2xx response (redirects such as a Cloudflare Access login are rejected).
8. No global Docker prune is performed. Unrelated containers, images, build
   caches, and persistent data remain untouched; cleanup is an explicit
   operator-controlled maintenance task.

The FAIM VPS override publishes no host ports. Its private Caddy joins the
existing `aurelinx_default` Docker network so the independent gateway can
reverse-proxy to it, while the deployment workflow never edits or reloads
`/opt/gateway/Caddyfile`. Add and validate the public `faimatrix.com` gateway
route as a separate operator change with a backup when you are ready to expose
the service.

The deploy does not run `docker volume prune`, `docker system prune --volumes`, or any command that intentionally removes the persistent PostgreSQL, Redis, Qdrant, raw-data, backup, or Caddy volumes. It also does not use `docker compose down`.

Compose service replacement on one host is designed to minimize interruption by keeping the Caddy proxy and data services up, but an absolute zero-downtime guarantee requires a blue/green or multi-host topology. The workflow must therefore be treated as a controlled rolling-style update, not as proof of high availability.

## Required GitHub configuration

Create a `production` environment and, preferably, require a reviewer before the deploy job can start. Add these environment secrets:

The workflow checks these values inside the approved deploy job (not the image-build job), so environment-scoped secrets are supported and missing credentials fail closed before any SSH or service change.

- `VPS_HOST` — VPS hostname or address;
- `VPS_USER` — restricted deployment user, preferably not root;
- `VPS_PORT` — SSH port, optional if `22`;
- `VPS_PATH` — application directory, optional if `/opt/faim/FAIM`;
- `VPS_SSH_KEY` — private deploy key in OpenSSH format;
- `VPS_KNOWN_HOSTS` — pinned `ssh-keyscan` output for the VPS host.

The workflow uses its short-lived GitHub job token for GHCR login. It does not
require or retain a long-lived GHCR personal-access token on the VPS.

The VPS must already contain `deploy/env.vpsprod` with real production secrets and persistent `Runtime/vps` directories. That file is never synchronized from GitHub.

For database-only production auth, keep `TENANT_KEYS_JSON={}`. To establish a
first tenant key without retaining plaintext in that file, an operator may add
a temporary `FAIM_TENANT_KEY_BOOTSTRAP_JSON` line containing the documented
tenant-to-key JSON map. During deployment, the VPS helper runs the backend
image bootstrap after migrations, stores only Argon2id hashes, and removes only
that temporary line after success. Treat the temporary value as an
operator-supplied secret: do not place it in GitHub workflow logs, source
control, or a long-running API/worker environment.
See [`docs/PRODUCTION_HARDENING.md`](docs/PRODUCTION_HARDENING.md) for the
manual dry-run and rotation procedure.

Before an actual update, validate the installed VPS configuration without changing services:

```bash
FAIM_IMAGE_PREFIX=ghcr.io/sainibhaowal/faimatrix \\
FAIM_IMAGE_TAG=preflight \\
./scripts/vps_deploy_ci.sh --preflight-only
```

For a private GHCR package, the deployment job authenticates the VPS with its
short-lived job token before pulling the exact immutable image tag.

## VPS preparation checklist

- Install Docker Engine and a current Docker Compose v2 plugin.
- Create the deployment directory and persistent `Runtime/vps` directories.
- Install the production environment file with mode `600`.
- Verify the deployment user can run the required Docker commands.
- Confirm DNS and TLS for `faimatrix.com`.
- Confirm `/health`, `/ready`, `/version`, and `/` work before the first automated deployment.
- Test backup and restore before loading irreplaceable data.
