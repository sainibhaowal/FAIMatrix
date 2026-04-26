Yes. For a real production UI, frontend should support the backend workflows that users and operators actually need.

Based on the current code, here is the practical page-by-page answer.

**First**
There is no dedicated `dashboard/settings/page.tsx` right now.
So “settings page” is effectively split across:

- [profile page](</home/sephi-asi/FAIM/frontend/src/app/(app)/dashboard/profile/page.tsx>)
- [storage page](</home/sephi-asi/FAIM/frontend/src/app/(app)/dashboard/storage/page.tsx>)
- [evolution page](</home/sephi-asi/FAIM/frontend/src/app/(app)/dashboard/evolution/page.tsx>)
- [providers page](</home/sephi-asi/FAIM/frontend/src/app/(app)/dashboard/providers/page.tsx>) if model/provider config matters

## What to update

**1. Memory Query page**
Current state:

- [memory-query page](</home/sephi-asi/FAIM/frontend/src/app/(app)/dashboard/memory-query/page.tsx>) is still just the chat shell
- [ChatInterface.tsx](/home/sephi-asi/FAIM/frontend/src/components/memoryquery/ChatInterface.tsx) renders generic assistant text only

Needs:

- show Phase 9 `answer` block
- show citations
- show confidence
- show contradiction notes
- show provenance/source links
- show temporal badges: `CURRENT` / `HISTORICAL`
- show result badges for:
  - multilingual/concept-linked
  - multimodal evidence
  - domain-linked fact/entity
- add an expandable “why this answer” panel using existing explain data

This is the highest-value UI gap.

**2. Storage page**
Current state:

- [storage page](</home/sephi-asi/FAIM/frontend/src/app/(app)/dashboard/storage/page.tsx>) is already strong and closest to operational UI
- it already has provenance concepts and upload/job flows

Needs:

- buttons for backend rebuild/import workflows:
  - canonical semantics rebuild
  - multilingual semantics rebuild
  - multimodal backfill/rebuild
  - domain profile rebuild
  - domain knowledge import
- job progress / status for those operations
- last run timestamp / result summary
- per-graph scope selector if needed
- optional extractor mode display:
  - current extractor
  - DocNative enabled/disabled

This page should become the main control plane for Phases 2, 6, 7, 8.

**3. Evolution page**
Current state:

- [evolution page](</home/sephi-asi/FAIM/frontend/src/app/(app)/dashboard/evolution/page.tsx>) is focused on self-evolution diagnostics/jobs

Needs:

- show retrieval-health metrics, not only graph evolution metrics
- add visibility for:
  - graph diffusion active state
  - index/ANN freshness
  - canonical/domain/multilingual rebuild freshness
- add “recompute retrieval artifacts” actions if appropriate
- show whether query-side enhancements are active on the selected graph

Do not overload this page with all rebuild buttons.
Keep it focused on graph/evolution/runtime health.

**4. API Keys page**
Current state:

- [api-keys page](</home/sephi-asi/FAIM/frontend/src/app/(app)/dashboard/api-keys/page.tsx>) manages key lifecycle well

Needs:

- review scopes against real backend features
- if backend supports these actions through API, add scopes for:
  - storage rebuild/import actions
  - domain knowledge import
  - evolution controls
  - advanced query/explain access if scoped
- expose which keys can trigger admin/operator workflows

Do not add feature UI here beyond permissions.
This page is for access control, not workflow execution.

**5. FIG / Graph page**
Current state:

- [graph page](</home/sephi-asi/FAIM/frontend/src/app/(app)/dashboard/graph/page.tsx>) just mounts `FigViewPage`
- graph inspectors already show some provenance-related info

Needs:

- display new node/edge kinds cleanly:
  - concept nodes
  - entity / relation / fact / value / time nodes
  - multilingual translation / concept-surface edges
  - domain edges
  - semantic edge types
- allow filtering by these new kinds
- allow badges/colors for:
  - contradiction/opposition
  - historical/current facts
  - imported KB facts
- optional path view for graph-semantic reasoning

This is important because backend graph semantics expanded a lot.

**6. Profile page**
Current state:

- [profile page](</home/sephi-asi/FAIM/frontend/src/app/(app)/dashboard/profile/page.tsx>) is mostly identity/account

Needs:

- probably not much for Phases 1-9 directly
- if you want a true settings hub, this page can link to:
  - retrieval settings
  - graph settings
  - ingestion settings
  - rebuild/admin actions

Do not cram backend workflow controls into profile itself.
Keep it identity-focused.

## Do you need a new page?

Yes, probably **one** new page is justified.

**Recommended new page: `Retrieval / Engine Control`**
Purpose:

- runtime/operator-facing controls for retrieval stack behavior
- visibility into enabled features by graph
- rebuild status summary
- index freshness
- semantic layer status
- domain knowledge status
- multilingual status
- multimodal status

Why:

- right now these controls would otherwise be scattered awkwardly
- storage page can own file-based workflows
- evolution page can own self-evolution
- graph page can own visualization
- this new page can own retrieval system operations

Good route:

- `/dashboard/retrieval`
  or
- `/dashboard/engine`

## What you do **not** need to expose

You do not need UI for every internal mechanism:

- raw BM25 stats
- every scoring constant
- every table/model
- every ANN internal
- every sidecar storage detail

Expose:

- actions users/operators need
- status they need to trust the system
- outputs they need to understand results

## Best practical structure

- **Memory Query**
  - answer block, citations, confidence, contradiction notes, temporal badges
- **Storage**
  - canonical/multilingual/multimodal/domain rebuild and import actions
- **Evolution**
  - graph/evolution health plus retrieval artifact freshness summary
- **API Keys**
  - scopes for admin/rebuild/import/query-explain workflows
- **FIG View**
  - support new node/edge kinds and graph filters
- **Profile**
  - identity only, maybe links out
- **New page**
  - retrieval/engine control center

## Bottom line

Yes, frontend should be updated to support backend workflows.

Most important missing areas:

1. Memory Query UI
2. Storage operator controls
3. FIG support for new graph semantics
4. API scopes alignment
5. One new retrieval/engine operations page

If you want, next I can turn this into an exact implementation plan with:

- which files to change
- which new page to add
- which buttons/actions to place on each existing page
