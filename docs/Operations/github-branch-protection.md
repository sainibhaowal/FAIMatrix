# GitHub Branch Protection

GitHub branch protection is configured in the repository settings, not in the
codebase. This document is the exact policy FAIM should use.

## Target Branches

- `main`
- `master` if it exists in the repo history or mirrors `main`

## Required Rules

- Block direct pushes.
- Require pull requests for all changes.
- Require at least 1 approval for normal code changes.
- Require 2 approvals for:
  - `deploy/**`
  - `faim_native/api/middleware/**`
  - `faim_native/store/pg/migrations/**`
  - auth, security, or release automation files
- Require branches to be up to date before merge.
- Dismiss stale approvals when the PR changes.
- Restrict force pushes.

## Required Status Checks

Mark these as required before merge:

- `backend-tests`
- `frontend-typecheck`
- `frontend-build`
- `frontend-lint`
- `e2e-smoke`
- `migration-check`
- `security-scan`
- `secret-scan`

## Ownership Rules

Use `CODEOWNERS` to require review from the operator/security owner for:

- auth
- middleware
- migrations
- deploy

## Release Rule

- Merge only from a green PR.
- Tag releases only from a merged commit that already passed the required checks.

