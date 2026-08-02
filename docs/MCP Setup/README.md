# MCP Setup Plan for FAIM

This folder contains the phase-by-phase implementation plan for adding an
MCP Marketplace control plane to FAIM.

Scope:
- Add a second Providers area for MCP Marketplace management.
- Keep the existing LLM Providers flow intact.
- Add backend support for connector registration, OAuth linking, policy gating,
  and Cortex-managed execution.
- Preserve tenant isolation, auth, encryption, and existing FAIM workflows.
- Start with a single safe transport path: HTTP-based MCP-compatible servers
  behind the FAIM broker, with support for later transport adapters.
- Ship with deny-by-default permissions and approval gates for any write or
  external side-effect action.

Phase files:
- `00-current-state-and-non-goals.md`
- `01-domain-model-and-storage-plan.md`
- `02-backend-mcp-broker-and-oauth-plan.md`
- `03-frontend-providers-mcp-toggle-plan.md`
- `04-cortex-orchestration-and-policy-plan.md`
- `05-testing-docs-and-release-plan.md`
- `06-mcp-protocol-and-registry-plan.md`
- `07-execution-runtime-and-worker-plan.md`
- `08-marketplace-ux-and-permissions-plan.md`
- `09-observability-recovery-and-audit-plan.md`
- `10-rollout-hardening-and-ops-plan.md`

Implementation principles:
- FAIM owns the source of truth for installed connectors and secrets.
- Browser UI never talks to MCP servers directly for privileged actions.
- Cortex may propose actions, but the broker and policy layer decide.
- Background workers execute only approved jobs.
- All connector state is tenant-scoped and audit-backed.
