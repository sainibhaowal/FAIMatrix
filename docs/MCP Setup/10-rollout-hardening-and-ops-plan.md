# Phase 10 - Rollout, Hardening, and Ops Plan

## What to do
Prepare a safe deployment and rollout strategy for the MCP Marketplace.

## Why to do it
This feature touches auth, secrets, orchestration, and memory control. It
needs staged rollout and operational guardrails.

## Where to do it
Likely files:
- `docs/Operations/`
- `faim_native/Docs/`
- `frontend/tests/`
- `tests/unit/`
- `tests/acceptance/`
- `tests/security/`
- deployment scripts and env templates

## Rollout strategy
- hidden or feature-flagged launch
- internal admin validation first
- limited tenant rollout
- connector-by-connector expansion
- production observability review before general availability
- start with read-first connectors only
- enable write-capable connectors only after review
- require explicit approval for high-risk tools

## Recommended first connector categories
- memory sources
- notes / docs
- calendar / scheduling
- email / messaging
- source control
- task tracking
- browser automation
- databases
- internal knowledge systems
- analytics / reporting

## Recommended first release connectors
- Google Drive / Docs
- Gmail
- Google Calendar
- Slack
- Notion
- GitHub
- Jira or Linear
- browser automation
- PostgreSQL / database access
- internal HTTP API connector templates

## Connector-specific rollout rules
- Memory sources can be enabled earliest because they improve long-term recall.
- Communication connectors need read-first defaults and explicit send approval.
- Source control and task connectors need issue/PR approval gates.
- Browser automation should remain heavily restricted and audited.
- Database and internal API connectors must be allowlisted per tenant.

## Hardening requirements
- encrypted secret storage
- strict tenant isolation
- safe defaults for scopes
- deny-by-default broker policy
- no raw token exposure in browser logs or backend logs
- connector allowlist by catalog entry
- per-tool risk tagging
- token refresh quarantine on repeated failures
- visible approval history for dangerous actions

## Operational requirements
- backup and restore considerations for connector state
- revocation playbook
- incident response for broken connectors
- retry and queue draining guidance
- clear rollback path if marketplace causes instability
- periodic registry sync / refresh if using public MCP registry data
- local FAIM catalog as the source of truth for enabled production apps

## Rollout checkpoints
- Step 1: catalog + browse only
- Step 2: OAuth connect for read-first connectors
- Step 3: read-only tool execution
- Step 4: approval-gated write actions
- Step 5: limited admin expansion to additional connectors
- Step 6: broader tenant rollout after audit review
