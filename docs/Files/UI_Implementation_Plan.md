# FAIM Lab Dashboard — Production Redesign Plan

## Executive Summary

The current FAIM Lab dashboard is **functional** but operates more as a **developer preview** than a **production-grade product**. This plan outlines a comprehensive redesign to transform it into a fully **user-friendly, polished, and production-mature** application with the signature FAIM aesthetic.

---

## Current State Analysis

### What Works Well ✓

| Component               | Strength                                             |
| ----------------------- | ---------------------------------------------------- |
| **FaimShell**           | Clean layout with sidebar + topbar + content pattern |
| **Visual Theme**        | Dark mode with cyan accent color is premium          |
| **Cursor-follow glow**  | Unique FAIM signature effect                         |
| **Component isolation** | Each page is modular                                 |
| **Graph 3D View**       | Impressive technical showcase                        |

### Critical Gaps ⚠️

| Area                      | Issue                             | Impact                    |
| ------------------------- | --------------------------------- | ------------------------- |
| **Empty States**          | Pages show bare "—" or "No data"  | Users feel lost           |
| **Loading States**        | Inconsistent spinners/skeletons   | Feels unpolished          |
| **Error Handling**        | Uses `alert()` and console warns  | Not production-grade      |
| **Onboarding**            | No guided flow for new users      | High bounce rate          |
| **Mobile UX**             | Limited responsive design         | 40%+ users are mobile     |
| **Data Visualization**    | Basic text metrics, no charts     | Underutilizes data        |
| **Accessibility**         | Missing ARIA labels, focus states | Not WCAG compliant        |
| **Notification System**   | No toast/notification UI          | Actions feel silent       |
| **Keyboard Navigation**   | Limited support                   | Power users frustrated    |
| **Help/Docs Integration** | No in-app help                    | Increases support tickets |

---

## Proposed Changes

### Phase 1: Design System Foundation

> **IMPORTANT**: This is the foundation that all other improvements depend on.

#### [NEW] design-tokens.css

Create a centralized design token system:

```css
:root {
  /* FAIM Color Palette */
  --faim-primary: #22d3ee; /* Cyan-400 */
  --faim-secondary: #a78bfa; /* Violet-400 */
  --faim-accent: #f472b6; /* Pink-400 */

  /* Semantic Colors */
  --faim-success: #34d399;
  --faim-warning: #fbbf24;
  --faim-error: #f87171;
  --faim-info: #60a5fa;

  /* Surface Hierarchy */
  --surface-0: #050b14; /* Base */
  --surface-1: #0f1629; /* Card */
  --surface-2: #1e293b; /* Elevated */
  --surface-3: #334155; /* Modal */

  /* Spacing Scale */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;

  /* Animation */
  --ease-faim: cubic-bezier(0.2, 0.8, 0.2, 1);
  --duration-fast: 150ms;
  --duration-normal: 300ms;
}
```

---

#### [NEW] ui/index.ts

Consolidated UI component library:

| Component    | Purpose                                     |
| ------------ | ------------------------------------------- |
| `Button`     | Primary, secondary, ghost, danger variants  |
| `Card`       | With GlowCard effect built-in               |
| `Input`      | Text, search, number with validation states |
| `Select`     | Dropdown with NeonDropdown styling          |
| `Modal`      | Accessible overlay with focus trap          |
| `Toast`      | Notification system (success/error/info)    |
| `Skeleton`   | Loading placeholder                         |
| `EmptyState` | Consistent "no data" UI                     |
| `Spinner`    | Loading indicator                           |
| `Badge`      | Status indicators                           |
| `Tooltip`    | Hover information                           |
| `Progress`   | Bar and circular variants                   |
| `Tabs`       | Navigation within pages                     |

---

### Phase 2: Shell & Navigation Improvements

#### [MODIFY] FaimShell.tsx

**Changes:**

1. **Add mobile drawer navigation**

   - Hamburger menu for < 768px
   - Slide-out drawer with same nav items
   - Touch-friendly gestures

2. **Add global notification center**

   - Bell icon in TopBar
   - Real-time notifications from SSE
   - Unread count badge

3. **Add command palette trigger**

   - `Cmd+K` / `Ctrl+K` shortcut
   - Quick navigation, search, actions

4. **Improve sidebar collapse**
   - Icons-only mode when collapsed
   - Hover to expand (optional)
   - Remember user preference

---

#### [MODIFY] SidebarNav.tsx

**Changes:**

1. **Add nav item grouping**

```
── CORE
   Dashboard
   Chat + Memory
   FIG View

── OPERATIONS
   Monitor
   Storage
   Benchmarks

── ACCOUNT
   Billing
   Settings
   Admin (if admin)
```

2. **Add collapsible sections**

3. **Add keyboard navigation**

   - Arrow keys for navigation
   - Enter to select
   - Focus indicators

4. **Add quick action buttons**
   - "New Chat" floating action
   - "Upload" shortcut

---

#### [MODIFY] TopBar.tsx

**Changes:**

1. **Simplify UI** — Currently 43KB, too complex

2. **Add breadcrumbs**

   - Show current location: `Dashboard / Chat / Session #abc123`

3. **Add global search**

   - Search memories, documents, chat sessions
   - Keyboard shortcut indicator

4. **Health indicator redesign**
   - Animated pulse when healthy
   - Warning state with details tooltip

---

### Phase 3: Dashboard Page Redesign

#### [MODIFY] dashboard/page.tsx

**Current:** Basic status cards and quick actions  
**Problem:** Static, no personalization, no engagement

**Proposed Redesign:**

```
┌─────────────────────────────────────────────────────────────┐
│ ☀️ Good afternoon, User!                          ○ Healthy │
│ Your FAIM engine is ready. Here's what's happening:        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐   │
│ │  💬 42    │ │  📄 18    │ │  🔗 1,247 │ │  ⚡ 12ms  │   │
│ │ Messages  │ │ Documents │ │   Nodes   │ │  Latency  │   │
│ └───────────┘ └───────────┘ └───────────┘ └───────────┘   │
│                                                             │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░  Token Usage: 42% of 1M   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 📊 ACTIVITY GRAPH (7 days)                                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │     ⬛⬛⬛⬛                                              │ │
│ │   ⬛⬛⬛⬛⬛⬛                          ⬛⬛              │ │
│ │ ⬛⬛⬛⬛⬛⬛⬛⬛      ⬛⬛⬛⬛      ⬛⬛⬛⬛⬛            │ │
│ │ Mon  Tue  Wed  Thu  Fri  Sat  Sun                       │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 🚀 QUICK ACTIONS                                           │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│ │   💬        │ │   📤        │ │   🔍        │            │
│ │ New Chat    │ │ Upload Doc  │ │ View Graph  │            │
│ │             │ │             │ │             │            │
│ └─────────────┘ └─────────────┘ └─────────────┘            │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 📜 RECENT ACTIVITY                                         │
│ ├─ 🕐 2 min ago   Chat: "What is FAIM?"                   │
│ ├─ 🕐 1 hour ago  Uploaded: research_notes.pdf            │
│ ├─ 🕐 3 hours ago Memory evolved: 47 nodes consolidated   │
│ └─ 🕐 Yesterday   New graph created: "Project Alpha"      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**New Features:**

1. **Personalized greeting** with time of day
2. **Live activity chart** (last 7 days)
3. **Recent activity feed** with real-time updates
4. **Token usage progress bar** with upgrade CTA at 80%
5. **Animated metric cards** with trend indicators (↑ ↓)
6. **Quick action keyboard shortcuts**

---

### Phase 4: Chat Page Improvements

#### [MODIFY] dashboard/chat/page.tsx

**Current Issues:**

- 1,435 lines in single file (too complex)
- Session management is cumbersome
- No message search
- No markdown rendering
- No code highlighting

**Proposed Changes:**

1. **Split into components:**

   - `ChatSidebar.tsx` — Session list
   - `ChatMessages.tsx` — Message thread
   - `ChatInput.tsx` — Input area
   - `ChatContext.tsx` — Memory sidebar

2. **Add markdown rendering**

   - Support for code blocks with syntax highlighting
   - Tables, lists, headers
   - LaTeX math expressions

3. **Add message actions**

   - Copy message
   - Regenerate response
   - View context nodes

4. **Add search**

   - Search across all sessions
   - Highlight matches

5. **Add typing indicator**

   - Show "FAIM is thinking..." with animation

6. **Add session templates**
   - "Research Assistant"
   - "Code Helper"
   - "Knowledge Q&A"

---

### Phase 5: Storage Page Improvements

#### [MODIFY] dashboard/storage/page.tsx

**Proposed Changes:**

1. **Drag-and-drop upload zone**

   - Visual feedback during drag
   - Multi-file support
   - Progress indicator per file

2. **File preview**

   - PDF thumbnails
   - Text file preview
   - Image preview

3. **Batch operations**

   - Select multiple files
   - Bulk delete
   - Bulk download

4. **File organization**

   - Folders/tags
   - Sort by date/name/size
   - Filter by type

5. **Processing status**
   - Real-time SSE updates
   - Cancel processing option
   - Retry failed files

---

### Phase 6: Graph View Improvements

#### [MODIFY] dashboard/graph/page.tsx

**Proposed Changes:**

1. **Add graph overview panel**

   - Total nodes/edges count
   - Graph density metrics
   - Most connected nodes

2. **Improve node selection**

   - Click to select, shift+click for multi-select
   - Selection panel showing all selected nodes

3. **Add zoom controls**

   - Zoom in/out buttons
   - Fit to screen
   - Reset view

4. **Add legend**

   - Node type color coding
   - Edge type explanations

5. **Add minimap**
   - Overview of entire graph
   - Click to navigate

---

### Phase 7: Monitor Page Improvements

#### [MODIFY] dashboard/monitor/page.tsx

**Proposed Changes:**

1. **Replace placeholder blocks** with real functionality:

   - **Incidents:** Connect to error logging
   - **Jobs:** Show Celery task queue status
   - **Audit:** Display recent admin actions

2. **Add health history chart**

   - Last 24 hours of uptime
   - Response time trends

3. **Add resource usage**
   - Redis memory
   - Postgres connections
   - Qdrant storage

---

### Phase 8: Common UX Patterns

#### [NEW] hooks/useToast.ts

Global toast notification system:

```typescript
const { toast } = useToast();

toast.success("Document uploaded successfully");
toast.error("Failed to connect to API");
toast.info("Processing your request...");
```

---

#### [NEW] components/EmptyState.tsx

Reusable empty state with:

- Icon
- Title
- Description
- Action button

```tsx
<EmptyState
  icon={<FileText />}
  title="No documents yet"
  description="Upload your first document to get started"
  action={{ label: "Upload", onClick: handleUpload }}
/>
```

---

#### [NEW] components/ErrorBoundary.tsx

- Catch React errors gracefully
- Show user-friendly error UI
- Include "Report Issue" button
- Log to backend for monitoring

---

### Phase 9: Accessibility (A11y)

**Required Changes Across All Components:**

| Fix                  | Details                                            |
| -------------------- | -------------------------------------------------- |
| **Focus indicators** | Visible keyboard focus rings using `focus-visible` |
| **ARIA labels**      | All interactive elements labeled                   |
| **Color contrast**   | Minimum 4.5:1 ratio for text                       |
| **Reduced motion**   | Respect `prefers-reduced-motion`                   |
| **Screen reader**    | Announce dynamic content changes                   |
| **Skip links**       | "Skip to main content" link                        |

---

### Phase 10: Performance Optimizations

| Optimization           | Where                           |
| ---------------------- | ------------------------------- |
| **Code splitting**     | Lazy load dashboard pages       |
| **Image optimization** | Use Next.js Image component     |
| **Virtual scrolling**  | Chat messages, file lists       |
| **Memoization**        | Expensive computations          |
| **SSE management**     | Single connection, shared state |

---

## Implementation Priority

| Priority  | Phase                     | Estimated Effort |
| --------- | ------------------------- | ---------------- |
| 🔴 **P0** | Design System Foundation  | 2-3 days         |
| 🔴 **P0** | Toast Notification System | 1 day            |
| 🟠 **P1** | Dashboard Page Redesign   | 2 days           |
| 🟠 **P1** | Empty States & Loading    | 1 day            |
| 🟡 **P2** | Chat Improvements         | 3 days           |
| 🟡 **P2** | Shell & Navigation        | 2 days           |
| 🟢 **P3** | Storage Improvements      | 2 days           |
| 🟢 **P3** | Graph Improvements        | 2 days           |
| 🔵 **P4** | Monitor Improvements      | 1 day            |
| 🔵 **P4** | Accessibility Pass        | 2 days           |

**Total Estimated Effort: ~18-20 days**

---

## Verification Plan

### Automated Tests

- Visual regression tests using Playwright
- Component unit tests with Vitest
- Accessibility audits with axe-core

### Manual Verification

- Cross-browser testing (Chrome, Firefox, Safari)
- Mobile device testing (iOS Safari, Android Chrome)
- Screen reader testing

### User Testing

- Onboarding flow walkthrough
- Task completion benchmarks
- User feedback collection

---

## Next Steps

Upon approval:

1. Create `task.md` with detailed checklist
2. Begin Phase 1: Design System Foundation
3. Implement UI component library
4. Progressively update each dashboard page

---

_Document generated: January 5, 2026_  
_FAIM Lab — Fractal Antisymmetric Inheritance Memory_

FAIM Dashboard Redesign — Task Checklist

Phase 1: Design System Foundation (P0)

Design Tokens
Create design-tokens.css with FAIM color palette
Add semantic colors (success, warning, error, info)
Add surface hierarchy tokens
Add spacing scale
Add animation tokens
Import tokens in global styles

UI Component Library

Create components/ui/ directory structure
Button.tsx — Primary, secondary, ghost, danger variants
Card.tsx — With GlowCard effect built-in
Input.tsx — Text, search, number with validation states
Select.tsx — NeonDropdown styling
Modal.tsx — Accessible overlay with focus trap
Skeleton.tsx — Loading placeholder
Spinner.tsx — Loading indicator
Badge.tsx — Status indicators
Tooltip.tsx — Hover information
Progress.tsx — Bar and circular variants
Tabs.tsx — Navigation within pages
ui/index.ts — Export barrel file

Phase 1b: Toast Notification System (P0)
Create hooks/useToast.ts hook
Create components/ui/Toast.tsx component
Create components/ui/ToastContainer.tsx for portal
Add ToastProvider to app layout
Implement success/error/info/warning variants
Add auto-dismiss with configurable duration
Add manual dismiss button
Add stacking for multiple toasts

Phase 2: Dashboard Page Redesign (P1)

Add personalized greeting with time of day
Add live activity chart (last 7 days)
Add recent activity feed with real-time updates
Add token usage progress bar
Add upgrade CTA at 80% usage
Add animated metric cards with trend indicators
Add quick action keyboard shortcuts
Wire real data from API

Phase 3: Empty States & Loading (P1)

Create components/EmptyState.tsx
Create components/ErrorBoundary.tsx
Add consistent Skeleton loading to all pages
Replace all alert() calls with toast notifications
Add error boundaries to each dashboard page

Phase 4: Chat Improvements (P2)

Split chat page into components:
ChatSidebar.tsx
ChatMessages.tsx
ChatInput.tsx
ChatContext.tsx
Add markdown rendering with syntax highlighting
Add message actions (copy, regenerate)
Add search across sessions
Add typing indicator animation
Add session templates

Phase 5: Shell & Navigation (P2)

Add mobile drawer navigation
Add hamburger menu for < 768px
Add global notification center (bell icon)
Add command palette (Cmd+K)
Add nav item grouping (CORE/OPERATIONS/ACCOUNT)
Add collapsible sidebar sections
Add keyboard navigation
Simplify TopBar (currently 43KB)
Add breadcrumbs

Phase 6: Storage Improvements (P3)

Add drag-and-drop upload zone
Add multi-file support
Add progress indicator per file
Add file preview (PDF thumbnails, text preview)
Add batch operations (multi-select, bulk delete)
Add file organization (sort, filter)
Add real-time SSE processing status

Phase 7: Graph Improvements (P3)

Add graph overview panel
Improve node selection (shift+click multi-select)
Add zoom controls
Add legend for node types
Add minimap

Phase 8: Monitor Improvements (P4)

Replace Incidents placeholder with real error log
Replace Jobs placeholder with Celery queue status
Replace Audit placeholder with admin actions
Add health history chart (24h)
Add resource usage (Redis/Postgres/Qdrant)

Phase 9: Accessibility Pass (P4)

Add focus indicators (focus-visible)
Add ARIA labels to all interactive elements
Verify color contrast (4.5:1 minimum)
Respect prefers-reduced-motion
Add screen reader announcements
Add skip link
Phase 10: Performance Optimizations
Add code splitting for dashboard pages
Use Next.js Image component
Add virtual scrolling for chat/files
Add memoization for expensive computations
Single SSE connection with shared state

Verification

Visual regression tests with Playwright
Component unit tests with Vitest
Accessibility audit with axe-core
Cross-browser testing
Mobile device testing
Create walkthrough.md with screenshots
