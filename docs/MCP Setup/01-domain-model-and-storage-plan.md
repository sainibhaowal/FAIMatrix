# Phase 01 - Domain Model and Storage Plan

## What to do
Define the MCP Marketplace data model, storage tables, and backend contracts
needed to represent:
- connector catalog entries,
- tenant-installed connectors,
- OAuth linkage state,
- approval / policy state,
- execution history,
- error and audit history.

## Why to do it
The marketplace cannot be safe or durable if it only exists in the frontend.
FAIM needs a backend source of truth for installed apps, token state, and
connector actions.

## Where to do it
Likely files and folders:
- `faim_native/store/pg/models_faim.py`
- `faim_native/store/pg/schema.sql`
- `faim_native/store/pg/migrations/`
- `faim_native/store/pg/repos/`
- `faim_native/store/crypto/envelope.py`
- `faim_native/api/contracts/`
- `faim_native/api/routers/`

## Proposed data model
- `mcp_catalog_entries`
- `mcp_installations`
- `mcp_oauth_accounts`
- `mcp_connector_secrets`
- `mcp_connector_policies`
- `mcp_connector_runs`
- `mcp_connector_run_events`
- `mcp_connector_audit_log`

## Initial state machine
- `cataloged`
- `available`
- `install_pending`
- `installed`
- `oauth_pending`
- `connected`
- `suspended`
- `revoked`
- `error`
- `disabled`

## Required fields
- tenant_id
- graph_id when connector is graph-scoped
- connector_id
- provider_name
- connector_type
- transport_type
- catalog_version
- install_version
- install_status
- oauth_status
- scopes
- requested_scopes
- granted_scopes
- secret_ciphertext / encrypted token blob
- secret_version
- secret_kid / key reference
- created_at / updated_at / revoked_at
- last_used_at
- last_error
- last_error_code
- last_error_at
- policy_mode
- approval_required flags
- approval_state
- approval_actor
- approval_at
- execution metadata
- run_count
- success_count
- failure_count

## Exact storage responsibilities
- `mcp_catalog_entries`: built-in marketplace catalog and version metadata.
- `mcp_installations`: tenant installs and lifecycle state.
- `mcp_oauth_accounts`: OAuth token metadata, refresh state, expiry, subject.
- `mcp_connector_secrets`: encrypted access/refresh tokens and derived secrets.
- `mcp_connector_policies`: per-connector permissions and approval rules.
- `mcp_connector_runs`: execution requests, status, timestamps, and outcomes.
- `mcp_connector_run_events`: step-by-step traces for execution and retries.
- `mcp_connector_audit_log`: immutable lifecycle and policy decisions.

## Encrypted secret flow
- Use envelope encryption from `faim_native/store/crypto/envelope.py`.
- Store only ciphertext plus non-secret metadata in Postgres.
- Keep provider tokens out of frontend state after the initial OAuth exchange.
- Support key rotation by re-wrapping secrets, not exposing plaintext.

## Safety rules
- Store secrets only encrypted.
- Use key rotation-friendly crypto helpers.
- Keep all rows tenant-scoped.
- Do not re-use plain auth key storage for OAuth tokens.
- Do not store refresh tokens in browser localStorage or sessionStorage.
- Do not store raw OAuth callback payloads beyond necessary audit metadata.

## Validation targets
- Connector installs are isolated per tenant.
- Token refresh and revocation are auditable.
- Catalog and installation records can be queried without exposing secrets.

## v1 curated connector set
FAIM should begin with this smaller, high-value connector set:
- Google Drive / Docs
- Gmail
- Google Calendar
- Slack
- Notion
- GitHub
- Jira or Linear
- browser automation
- PostgreSQL / database access
- internal HTTP API connectors

## Per-connector policy baseline
- Google Drive / Docs: read-first, write only after approval.
- Gmail: read and draft by default, send only after approval.
- Google Calendar: read and propose only by default, create/update after
  approval.
- Slack: read and draft by default, send after approval.
- Notion: read-first, write after approval.
- GitHub: read-first, issue/PR actions after approval.
- Jira / Linear: read-first, create/update after approval.
- browser automation: read-first, click/input side effects after approval.
- PostgreSQL / database: read-only by default, write only for admin-approved
  tasks.
- internal HTTP APIs: allowlist-only, permission-specific, approval-gated when
  side effects exist.
