# Phase 08 - Marketplace UX and Permissions Plan

## What to do
Build the user-facing MCP Marketplace experience inside Providers and related
dashboard surfaces.

## Why to do it
Users need to browse, install, connect, disconnect, and control connector apps
without losing sight of permissions and risk.

## Where to do it
Likely files:
- `frontend/src/app/(app)/dashboard/providers/page.tsx`
- `frontend/src/contexts/ProviderContext.tsx`
- `frontend/src/lib/providers.ts`
- `frontend/src/lib/providerDiscovery.ts`
- `frontend/src/components/layout/Sidebar/SidebarNav.tsx`
- `frontend/src/components/layout/CommandPalette.tsx`
- `frontend/src/components/shared/Providers.tsx`
- `frontend/src/app/(app)/layout.tsx`

## UX surfaces to design
- Providers toggle: `LLM Providers` and `MCP Marketplace`
- marketplace browse grid
- connector detail drawer/modal
- install flow
- OAuth connect flow
- permissions review
- approval pending state
- connection status
- execution history
- revoke / disconnect controls
- per-app tool list and capability badges
- connector health summary
- logs and audit timeline
- approval inbox / action review panel
- connector settings / scope management

## Exact screen set
- `Providers` landing page with the two top-level toggles.
- `MCP Marketplace` browse view.
- `Connector Details` drawer with tools, scopes, auth type, and risk level.
- `Install Connector` modal.
- `Connect Account` / OAuth handoff screen.
- `Permissions Review` screen before first use and for risky scope expansion.
- `Connected Apps` screen with status, refresh, revoke, and last-used metadata.
- `Execution Logs` screen for runs, events, and failures.
- `Approval Queue` screen for manual approval gates.
- `Connector Settings` screen for policy and scope adjustments.

## v1 browse categories
- Memory
- Communication
- Calendar and scheduling
- Notes and docs
- Source control
- Task tracking
- Browser automation
- Databases and storage
- Internal APIs
- Analytics and reporting

## v1 connector cards must show
- short description
- auth type
- required scopes
- risk level
- read/write support
- approval requirement
- last verified version
- trust badge
- install / connect CTA

## First release UX defaults
- surface read-first connectors first
- hide high-risk connectors under a warning section
- show “recommended for memory” labels on memory-rich apps
- show “workflow” labels on task/communication apps
- show “approval required” labels before any side-effect action

## Exact permission model
- `marketplace.read`
- `marketplace.install`
- `marketplace.connect`
- `marketplace.revoke`
- `connector.execute.read`
- `connector.execute.write`
- `connector.policy.manage`
- `connector.audit.read`
- `connector.admin`

## Tool risk classes
- `read_only`
- `read_write`
- `destructive`
- `admin`
- `credential_access`

## UX behavior rules
- Show a clear CTA only when the action is actually allowed.
- Explain the reason if approval is required.
- Show whether Cortex is suggesting a tool or directly executing a permitted one.
- Keep the LLM provider tab visually separate from MCP marketplace state.

## Permissions UX rules
- Show the exact scopes or tool permissions requested.
- Highlight write-capable or risky connectors.
- Explain when Cortex can suggest but not execute.
- Make tenant and workspace scoping visible.
- Show token state and expiration in plain language.
- Show revocation and reconnect actions separately.
- Show approval history for risky actions.

## Suggested first release screen flow
1. Open Providers.
2. Switch to MCP Marketplace.
3. Browse curated category.
4. Open connector details.
5. Review scopes and risk.
6. Start OAuth connect or install.
7. Review approval request if needed.
8. Confirm connected app status.
9. Inspect logs or revoke later if necessary.

## Compatibility rules
- Existing LLM provider controls must keep their current behavior.
- New MCP data should not pollute LLM provider localStorage state.
- Chat UX should remain stable for LLM mode.
