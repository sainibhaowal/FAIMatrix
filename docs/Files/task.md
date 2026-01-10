# FAIM Dashboard Redesign — Task Checklist

## Phase 1: Design System Foundation (P0)

### Design Tokens

- [x] Create design tokens in `globals.css` with FAIM color palette
- [x] Add semantic colors (success, warning, error, info)
- [x] Add surface hierarchy tokens
- [x] Add spacing scale
- [x] Add animation tokens (shimmer, slideIn, fadeIn, pulse-glow)
- [x] Import tokens in global styles

### UI Component Library

- [x] Create `components/ui/` directory structure
- [x] `Button.tsx` — Primary, secondary, ghost, danger, success variants
- [x] `Card.tsx` — With GlowCard effect built-in
- [x] `Input.tsx` — Text, search, textarea with validation states
- [x] `Select.tsx` — NeonDropdown styling + MultiSelect
- [x] `Modal.tsx` — Accessible overlay with focus trap
- [x] `Skeleton.tsx` — Loading placeholder (in Spinner.tsx)
- [x] `Spinner.tsx` — Loading indicator
- [x] `Badge.tsx` — Status indicators
- [x] `Tooltip.tsx` — Hover information
- [x] `Progress.tsx` — Bar and circular variants
- [x] `Tabs.tsx` — Navigation within pages (in Tooltip.tsx)
- [x] `ui/index.ts` — Export barrel file

---

## Phase 1b: Toast Notification System (P0)

- [x] Create `hooks/useToast.ts` hook (combined in Toast.tsx)
- [x] Create `components/ui/Toast.tsx` component
- [x] Create `components/ui/ToastContainer.tsx` for portal (in Toast.tsx)
- [x] Add ToastProvider to app layout
- [x] Implement success/error/info/warning variants
- [x] Add auto-dismiss with configurable duration
- [x] Add manual dismiss button
- [x] Add stacking for multiple toasts

---

## Phase 2: Dashboard Page Redesign (P1)

- [x] Add personalized greeting with time of day
- [x] Add live activity chart (last 7 days)
- [x] Add recent activity feed with real-time updates
- [x] Add token usage progress bar
- [x] Add upgrade CTA at 80% usage
- [x] Add animated metric cards with trend indicators
- [x] Add quick action keyboard shortcuts (C/U/G/R)
- [x] Wire real data from API (with mock fallback)

---

## Phase 3: Empty States & Loading (P1)

- [x] Create `components/EmptyState.tsx`
- [ ] Create `components/ErrorBoundary.tsx`
- [ ] Add consistent Skeleton loading to all pages
- [ ] Replace all `alert()` calls with toast notifications
- [ ] Add error boundaries to each dashboard page

---

## Phase 4: Chat Improvements (P2)

- [ ] Split chat page into components:
  - [ ] `ChatSidebar.tsx`
  - [ ] `ChatMessages.tsx`
  - [ ] `ChatInput.tsx`
  - [ ] `ChatContext.tsx`
- [ ] Add markdown rendering with syntax highlighting
- [ ] Add message actions (copy, regenerate)
- [ ] Add search across sessions
- [ ] Add typing indicator animation
- [ ] Add session templates

---

## Phase 5: Shell & Navigation (P2)

- [ ] Add mobile drawer navigation
- [ ] Add hamburger menu for < 768px
- [ ] Add global notification center (bell icon)
- [ ] Add command palette (Cmd+K)
- [ ] Add nav item grouping (CORE/OPERATIONS/ACCOUNT)
- [ ] Add collapsible sidebar sections
- [ ] Add keyboard navigation
- [ ] Simplify TopBar (currently 43KB)
- [ ] Add breadcrumbs

---

## Phase 6: Storage Improvements (P3)

- [ ] Add drag-and-drop upload zone
- [ ] Add multi-file support
- [ ] Add progress indicator per file
- [ ] Add file preview (PDF thumbnails, text preview)
- [ ] Add batch operations (multi-select, bulk delete)
- [ ] Add file organization (sort, filter)
- [ ] Add real-time SSE processing status

---

## Phase 7: Graph Improvements (P3)

- [ ] Add graph overview panel
- [ ] Improve node selection (shift+click multi-select)
- [ ] Add zoom controls
- [ ] Add legend for node types
- [ ] Add minimap

---

## Phase 8: Monitor Improvements (P4)

- [ ] Replace Incidents placeholder with real error log
- [ ] Replace Jobs placeholder with Celery queue status
- [ ] Replace Audit placeholder with admin actions
- [ ] Add health history chart (24h)
- [ ] Add resource usage (Redis/Postgres/Qdrant)

---

## Phase 9: Accessibility Pass (P4)

- [ ] Add focus indicators (`focus-visible`)
- [ ] Add ARIA labels to all interactive elements
- [ ] Verify color contrast (4.5:1 minimum)
- [ ] Respect `prefers-reduced-motion`
- [ ] Add screen reader announcements
- [ ] Add skip link

---

## Phase 10: Performance Optimizations

- [ ] Add code splitting for dashboard pages
- [ ] Use Next.js Image component
- [ ] Add virtual scrolling for chat/files
- [ ] Add memoization for expensive computations
- [ ] Single SSE connection with shared state

---

## Verification

- [ ] Visual regression tests with Playwright
- [ ] Component unit tests with Vitest
- [ ] Accessibility audit with axe-core
- [ ] Cross-browser testing
- [ ] Mobile device testing
- [ ] Create walkthrough.md with screenshots
