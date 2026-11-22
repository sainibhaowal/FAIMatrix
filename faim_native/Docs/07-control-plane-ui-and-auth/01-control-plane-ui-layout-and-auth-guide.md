# Control Plane UI Layout Container & Auth Session Resilience Guide

## 1. Scope
Documents the unified centered `FaimShell` dashboard container standard (`max-w-[1440px]` with responsive side margins) and the client-side NextAuth session token caching mechanism that eliminates auth polling contention:
- **Shell Container**: `frontend/src/components/layout/FaimShell.tsx`, `frontend/src/components/layout/GlassHeader.tsx`
- **Aligned Pages**:
  - `frontend/src/app/(admin)/dashboard/mcp/page.tsx`
  - `frontend/src/app/(admin)/dashboard/api-keys/page.tsx`
  - `frontend/src/app/(admin)/dashboard/providers/page.tsx`
  - `frontend/src/app/(admin)/dashboard/billing/page.tsx`
  - `frontend/src/app/(admin)/dashboard/benchmarks/page.tsx`
  - `frontend/src/app/(admin)/dashboard/journal/page.tsx`
  - Sibling dashboard views inheriting `FaimShell`: `page.tsx`, `storage/page.tsx`, `evolution/page.tsx`, `embedding-providers/page.tsx`, `profile/page.tsx`
- **Full-Bleed Exception**: `frontend/src/app/(admin)/dashboard/graph/page.tsx` (`3D FigView` canvas retains `overflow-hidden p-0` / `h-full`)
- **Auth Token Caching**: `frontend/src/app/(admin)/dashboard/evolution/page.tsx`, `frontend/src/app/(admin)/dashboard/page.tsx`, `frontend/src/app/(admin)/dashboard/storage/page.tsx`

---

## 2. Balanced Global Page Container Standard (`FaimShell`)
In `FaimShell.tsx` (`L246-263`), non-graph dashboard routes are wrapped in a centered balanced workspace container rather than cramped `max-w-6xl` (`1152px`) or edge-to-edge un-capped stretching:
- **`<main>` padding**: `overflow-y-auto px-4 py-6 sm:px-6 md:px-10 lg:px-14 xl:px-16` (`40px`–`64px` desktop horizontal breathing room).
- **Inner wrapper**: `mx-auto w-full max-w-[1440px]` (caps content width at a centered `1440px` across all screens).
- **`/dashboard/graph` exception**: keeps `overflow-hidden p-0` on `<main>` and `h-full` on the inner wrapper for full-viewport 3D canvas rendering.

### Canonical Page Wrapper Pattern
Every non-graph dashboard page under `frontend/src/app/(admin)/dashboard/` should use the standard `px-1` wrapper with `<div className="faim-grid" />` without introducing conflicting outer `max-w-*` caps:
```tsx
<div className="relative space-y-4 pb-8 text-slate-100 px-1">
  <div className="faim-grid" />
  <GlassHeader ... />
  {/* Balanced sections and grids inheriting FaimShell max-w-[1440px] */}
</div>
```

### Fixed Layout Discrepancies
1. **`FaimShell` Global Cap (`FaimShell.tsx`)**: Replaced `md:px-6` + uncapped `w-full` with `sm:px-6 md:px-10 lg:px-14 xl:px-16` + `mx-auto w-full max-w-[1440px]`, giving every dashboard page consistent centered proportions (neither too narrow at `1152px` nor edge-to-edge on wide viewports).
2. **`/dashboard/mcp` (`mcp/page.tsx`) & `/dashboard/api-keys` (`api-keys/page.tsx`)**: Removed inner `mx-auto max-w-6xl space-y-6 px-6 pt-6` wrappers so body cards align flush with `<GlassHeader />` inside `FaimShell`.
3. **`/dashboard/providers` (`providers/page.tsx`)**: Aligned root wrapper to `relative space-y-4 pb-8 text-slate-100 px-1` with `<div className="faim-grid" />`, and expanded the 3 Navigator cards (`Embedding Active`, `Reranker Active`, `OCR Active`) to `grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4`.
4. **`/dashboard/billing` (`billing/page.tsx`)**: Removed per-page `max-w-7xl mx-auto` and aligned wrapper to `relative space-y-4 pb-8 text-slate-100 px-1`.
5. **`/dashboard/benchmarks` (`benchmarks/page.tsx`) & `/dashboard/journal` (`journal/page.tsx`)**: Added matching `relative ... pb-8 text-slate-100 px-1` horizontal padding so headers and grids align to the exact pixel column as sibling pages.

*(Dialog/modal widths such as `max-w-sm` / `max-w-md` and compact drawers remain compact by design.)*

---

## 3. NextAuth Session Token Caching (`resolveCachedAccessToken`)
### Failure mode addressed
Dashboard views with multiple concurrent polling/fetch calls previously called NextAuth `getSession()` on every HTTP request, flooding `GET /api/auth/session` and triggering `CLIENT_FETCH_ERROR` / `ERR_CONNECTION_REFUSED` spikes under burst load.

### Implemented Pattern
In `frontend/src/app/(admin)/dashboard/evolution/page.tsx` (`resolveCachedAccessToken`) and sibling dashboard data fetchers:
- Caches `accessToken` in module scope for `SESSION_TOKEN_TTL_MS = 60_000` (`60s`).
- Deduplicates concurrent calls via a shared `inflightSession` promise so simultaneous API requests await a single `/api/auth/session` fetch.
- Gracefully falls back to the last valid cached token if a transient network glitch occurs while refreshing.
