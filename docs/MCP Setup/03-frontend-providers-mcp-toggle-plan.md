# Phase 03 - Frontend Providers MCP Toggle Plan

## What to do
Extend the existing Providers page and provider context into a two-mode
control surface:
- `LLM Providers`
- `MCP Marketplace`

## Why to do it
Users need a clear split between model endpoints and connector apps. Mixing
them in one list would confuse install flows, permissions, and runtime
semantics.

## Where to do it
Frontend files likely involved:
- `frontend/src/app/(app)/dashboard/providers/page.tsx`
- `frontend/src/contexts/ProviderContext.tsx`
- `frontend/src/lib/providers.ts`
- `frontend/src/lib/providerDiscovery.ts`
- `frontend/src/app/api/provider/discover/route.ts`
- `frontend/src/app/api/provider/chat/route.ts`
- `frontend/src/components/layout/Sidebar/SidebarNav.tsx`
- `frontend/src/components/layout/CommandPalette.tsx`

## UI changes to plan
- Add a top-level toggle for `LLM Providers` vs `MCP Marketplace`.
- Keep the existing LLM add/discover/remove flow unchanged.
- Add an MCP marketplace grid/list view.
- Show connector install, connect, disconnect, and status states.
- Show tenant-approved scope grants and risk labels.
- Show direct login/connect buttons only when allowed by policy.
- Add marketplace categories so users can browse:
  - memory sources
  - communication sources
  - code sources
  - workflow/task sources
  - browser/web sources
  - database/data sources
  - enterprise/admin sources
- Add a “curated / verified” badge for safe default connectors.

## UX rules
- No raw secrets in UI previews.
- Clear state labels: available, installed, connected, pending approval, error.
- Display effective permissions and current policy mode.
- Separate “model provider” actions from “app connector” actions.
- Prefer read-only connectors in the first-screen defaults.
- Keep write/admin connectors visually separated behind risk warnings.

## Compatibility rules
- Do not regress current provider persistence.
- Do not break the active provider selection behavior.
- Do not change chat behavior for the current LLM providers path.

## Suggested first release screens
- Marketplace home
- Connector catalog browse
- Connector detail / install
- OAuth connect / consent
- Connected apps
- Permissions and approval queue
- Execution history and logs
- Revoke / disconnect
