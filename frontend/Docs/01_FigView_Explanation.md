# 01_FigView_Explanation.md

Date: 2026-03-22
Status: Plan-first definition document. No implementation is approved by this file alone.
Scope: Defines what FAIM Fig View must be, what it must show, what it must not do, and how it fits the current FAIM system.

## 1. Purpose

Fig View is FAIM's graph exploration page at `/dashboard/graph`.

Its purpose is to make FAIM memory structure inspectable and navigable from the graph perspective, using real backend truth and without weakening tenant safety, auth, provenance integrity, or existing product behavior.

Fig View exists because:

1. Storage shows what entered the system.
2. Evolution shows how the system changed over time.
3. Query and Memory APIs expose retrieval and memory detail.
4. Fig View must show how these realities appear as connected graph structure.

It is not a separate workflow engine.
It is the visual and inspectable graph surface for what FAIM already stores, derives, evolves, and retrieves.

## 2. Boundaries

### 2.1 What Fig View is responsible for

Fig View must let the user:

1. see graph structure
2. navigate nodes and relations
3. inspect memory objects
4. inspect parent-child lineage
5. inspect similarity and opposition context
6. inspect provenance from graph node back to source memory/file context
7. inspect graph-health signals such as `D`, `H`, and `lambda`
8. inspect graph effects of pruning, deduplication, and macro emergence
9. inspect graph-side effects of evolution and self-invention without duplicating the Evolution page

### 2.2 What Fig View is not responsible for

Fig View must not become:

1. the main Storage workflow page
2. the main Evolution control page
3. the main file management page
4. the main admin or debugging console
5. a place that exposes raw secrets, auth artifacts, or unsafe internal payloads

### 2.3 Relationship to existing pages

Storage page:

1. source of upload, extraction, packetization, ingestion, provenance summary
2. Fig View consumes those truths and visualizes graph impact

Evolution page:

1. source of operational evolution controls, runs, status, and runtime diagnostics
2. Fig View shows graph-side results such as changed nodes, merge/prune effects, and macro emergence

API Key page:

1. not a graph page concern
2. still affects access and permission boundaries for FIG endpoints

Profile page:

1. not directly a graph page concern
2. profile and persist preferences may influence how some graph-derived runtime context is labeled if already exposed by backend truth

## 3. Current FAIM Repo Reality

Verified current route and surrounding frontend:

1. `frontend/src/app/(app)/dashboard/graph/page.tsx`
2. `frontend/src/components/layout/Sidebar/SidebarNav.tsx`
3. `frontend/src/components/layout/Breadcrumbs.tsx`
4. `frontend/src/components/layout/FaimShell.tsx`
5. `frontend/src/contexts/UserContext.tsx`

Verified current backend surfaces already available:

1. `faim_native/api/routers/node.py`
2. `faim_native/api/routers/memory.py`
3. `faim_native/api/routers/storage.py`
4. `faim_native/api/routers/events.py`
5. `faim_native/api/routers/metrics.py`
6. `faim_native/api/routers/evolve.py`
7. `faim_native/api/routers/query.py`

Verified graph data stores and repos:

1. `faim_native/store/pg/models_faim.py`
2. `faim_native/store/pg/repos/node_repo.py`
3. `faim_native/store/pg/repos/edge_repo.py`
4. `faim_native/store/pg/repos/event_repo.py`
5. `faim_native/store/pg/repos/graph_version_repo.py`
6. `faim_native/store/pg/repos/storage_file_repo.py`
7. `faim_native/runtime/context.py`
8. `faim_native/api/deps.py`

Important repo fact:

1. `/dashboard/graph` is currently placeholder-only.
2. there is no dedicated backend graph router yet.
3. `react-force-graph-3d`, `three`, and related frontend dependencies already exist in `frontend/package.json`.

## 4. Why Fig View Needs More Than a 3D Canvas

A 3D graph alone is not enough. FAIM requires graph exploration with semantic accountability.

Without supporting controls and inspection, a graph page becomes decorative.
Fig View must instead be an operational intelligence surface where a user can answer:

1. what is this node
2. where did it come from
3. what does it inherit from
4. what conflicts with it
5. why is it linked
6. what changed recently
7. whether it is atom-level, macro-level, deduplicated, pruned, compressed, retrieval-active, or historically important

## 5. What Fig View Must Contain

### 5.1 Core page regions

Fig View should contain these major regions:

1. graph canvas
2. top control bar
3. legend and filter panel
4. node inspector panel
5. metrics strip or metrics panel
6. graph status area
7. optional timeline/replay strip if supported in v1 or v1.5

### 5.2 Graph canvas

The canvas is the main exploration surface.

It must support:

1. 3D graph view
2. node hover
3. node click
4. node selection persistence
5. focused expansion around a node
6. visual encoding for node types and edge types
7. camera recentering
8. graph state updates without visual chaos

### 5.3 Top control bar

The top controls should include:

1. layout mode switch
2. fit graph
3. center on selection
4. reset camera
5. zoom in
6. zoom out
7. graph lock / unlock
8. hover card on / off
9. live updates on / off if needed
10. search input
11. optional similarity threshold or view density controls

### 5.4 Legend and filter panel

This panel should explain and control:

1. node colors
2. node type groups
3. edge types
4. overlay types
5. active/inactive memory states
6. visible/invisible categories
7. semantic meaning of style rules

Possible filter categories:

1. atoms
2. macros
3. inheritance edges
4. opposition edges
5. retrieved nodes
6. recent nodes
7. pruned or historical nodes if visible
8. dedup-linked nodes
9. chunk-derived nodes
10. document-derived nodes

### 5.5 Node inspector

This is the authoritative detail panel for the selected node.

It must show real backend-backed detail, not fabricated frontend summaries.

It should contain:

1. identity
2. memory metadata
3. lineage
4. provenance
5. relation details
6. conflict/opposition details
7. graph-health-related node context
8. actions for exploration

### 5.6 Overlays

Overlays may include:

1. retrieval path highlight
2. evolution change overlay
3. conflict/opposition emphasis
4. dedup/reuse markers
5. prune or deactivated markers
6. temporal or recent-change highlight

## 6. Graph Behaviors and Interaction Model

### 6.1 Layout modes

Recommended modes:

1. `Explore`
2. `Analyze`
3. `Lineage`

Explore:

1. best for broad discovery
2. spatial, visually expressive, 3D-first

Analyze:

1. best for readability and clustering
2. emphasizes semantic grouping and inter-cluster bridges

Lineage:

1. best for parent-child and inheritance inspection
2. emphasizes directionality and level structure

These modes should change presentation, not underlying truth.

### 6.2 Lock / unlock behavior

This must be defined clearly because it affects usability.

Recommended behavior:

1. unlocked mode:
   - user can pan, drag, move, orbit, and inspect freely
2. locked mode:
   - graph stabilizes around current focal model
   - camera rotation remains controlled
   - accidental node-drag or scene chaos is reduced

The lock should not freeze the product into a dead state.
It should shift interaction from free manipulation to stable observation.

### 6.3 Zoom and navigation

Required:

1. scroll zoom
2. zoom buttons
3. fit graph
4. center on selection
5. reset camera

### 6.4 Hover behavior

Hovering a node should show a floating memory card.

The floating card should show:

1. short node id
2. label or derived title if safely available
3. memory type
4. source type
5. level
6. touch/retrieval activity
7. relation summary
8. warning or status badges

The hover card must remain safe:

1. no secret values
2. no auth tokens
3. no raw payload body by default
4. no cross-tenant leakage

### 6.5 Click behavior

Clicking a node should:

1. pin the node
2. update the inspector
3. optionally center or focus the graph
4. enable next and previous relevant memory navigation
5. allow neighborhood expansion

### 6.6 Next / previous relevant memory

This is not simple "next in array" navigation.
It should follow relevance logic.

Possible relevance sequence sources:

1. strongest linked visible nodes
2. retrieval-ranked neighbors
3. inheritance-linked neighbors
4. opposition-linked neighbors when conflict view is active

This must be deterministic enough that the user feels guided, not random.

### 6.7 Search

Search should allow:

1. finding nodes by known id
2. finding nodes by safe label/title if exposed
3. optional retrieval-based highlighting if connected later to query APIs

## 7. Memory Objects in Graph Exploration

Fig View must represent memory objects in a way that reflects FAIM structure.

### 7.1 Node categories

Based on current verified repo reality and product needs, Fig View likely needs to represent:

1. atom nodes
2. macro nodes
3. parent nodes
4. child nodes
5. chunk-derived nodes
6. packet-associated nodes
7. document-derived nodes
8. retrieval-active nodes
9. conflict/opposition-linked nodes
10. dedup-linked nodes
11. pruned or historical nodes if such visibility is later exposed safely

Current backend directly verifies:

1. `kind` includes at least `atom` and `macro`
2. inheritance edges exist
3. opposition edges exist
4. provenance can be linked through raw ids and storage provenance paths

Anything beyond direct verified data should be treated as derived display classification, not hard backend truth, unless a backend contract is added.

### 7.2 Parent and child nodes

The user should be able to inspect:

1. who the parents are
2. what inheritance fractions exist
3. what children exist
4. whether the selected node is a leaf, bridge, or aggregate

### 7.3 Chunk nodes and atomized units

FAIM already stores chunk-like memory structure indirectly through:

1. `raw_id`
2. `block_id`
3. ingest and provenance relationships

Fig View should expose chunk/atom concepts through:

1. source and block metadata
2. node grouping
3. provenance panels
4. optional filter views

### 7.4 Packetized memory structures

Users should be able to understand:

1. packet hash or dedup packet identity if available
2. whether a node emerged from a deduplicated ingest path
3. whether multiple nodes map back to the same packetized source

### 7.5 Documents and supported formats

Fig View should help the user understand graph memory derived from supported formats such as PDF and other current Storage-supported inputs.

It should not become a document viewer.
Instead it should show graph-facing summaries:

1. source file or raw reference
2. mime type
3. file origin
4. chunk/block relation
5. dedup and provenance context

## 8. What Must Be Visible on Hover or Click

### 8.1 Minimum visible fields for a selected node

These are strongly recommended:

1. node id
2. graph id
3. node kind
4. level
5. vector hash
6. residual
7. touch count
8. raw id
9. block id
10. created at
11. updated at

These are already aligned with current verified backend fields.

### 8.2 Provenance-related details

If available through current endpoints:

1. source file / raw reference
2. mime type
3. file size
4. packet hash
5. dedup status
6. related provenance events

### 8.3 Relation-related details

Show:

1. parent ids
2. parent types
3. inheritance fractions
4. child count
5. visible direct children
6. opposition links
7. edge weights
8. relation reason when backend can explain it

### 8.4 State and ranking details

Show where available:

1. novelty
2. redundancy
3. energy
4. confidence or weight
5. retrieval frequency or touch count
6. compression or merge indication
7. prune candidate or historical indicator if safely exposed

Current repo verification:

1. novelty, redundancy, energy are available at graph metrics level through `metrics/scorecard`
2. node-level residual and touch count are already directly available
3. any additional node-scoped score display may require backend aggregation or explicit graph-router shaping

## 9. FAIM-Specific Concepts That Fig View Must Represent

### 9.1 Fractal inheritance

This should be visible through:

1. lineage mode
2. parent-child inspector views
3. inheritance edge styling
4. inheritance fractions in details

### 9.2 Antisymmetric memory relations

This should be visible through:

1. opposition edge styling
2. opposition badges in node cards
3. conflict-oriented filters
4. inspector explanations

### 9.3 Opposition-based deduplication

This should appear as inspectable graph context, not as undocumented hidden logic.

The user should see:

1. dedup presence
2. packet reuse
3. opposition/conflict context where the system exposes it

### 9.4 Pruning

The graph should show pruning from a graph perspective:

1. recent prune effect
2. pruned/deactivated historical indication if available
3. not as the primary operational pruning control surface

### 9.5 Macro-node emergence

Macro nodes should be visible as higher-order concept structures.

The user should be able to inspect:

1. that a node is macro-level
2. what it inherits from
3. what it compresses or groups conceptually

### 9.6 Retrieval paths

If query or retrieval context is connected:

1. highlight relevant paths
2. distinguish retrieval-active nodes
3. support exploration of why a retrieval path exists

### 9.7 Extraction paths

Where safe and available, the user should understand:

1. source document or raw object
2. extracted chunk/block path
3. graph node outcome

### 9.8 Forgetting and cold-state indications

If FAIM exposes or later adds state around cold, compressed, deactivated, or historical memories, Fig View should support visual treatment for them.

Current status:

1. explicit cold-state contracts are verification-required
2. do not invent them in UI before backend truth exists

## 10. Metrics and Equations Relevant to Fig View

Fig View should let the user inspect graph-health metrics from an exploration perspective.

### 10.1 D - Fractal Dimension

Meaning:

1. semantic density of the graph

How user should interpret it:

1. low D means sparse or weakly connected semantic structure
2. high D means richer conceptual interconnection

How it should appear:

1. metrics card or strip
2. short tooltip or inspector explanation

### 10.2 H - Entropy

Meaning:

1. graph disorder or semantic noise

How user should interpret it:

1. high H may signal noisy, disordered graph state
2. better organization, merge quality, and pruning should reduce H

How it should appear:

1. metrics card
2. health state coloration or warning marker if desired

### 10.3 lambda - Evolution Pressure

Meaning:

1. pressure toward invention or macro emergence

Formula context:

1. `lambda = 0.5 N̂ + 0.3 (1 - R̂) + 0.2 Ĥ`
2. `N̂` is novelty
3. `R̂` is redundancy
4. `Ĥ` is normalized entropy

How it should appear:

1. visible graph-health metric
2. used as explanatory context
3. not as a direct replacement for Evolution page controls

### 10.4 Golden equations and deeper graph math

Current repo verification:

1. scorecard exposes `D`, `H`, `lambda`, redundancy, novelty, energy
2. the "golden equation" should be treated as a backend-verification concept, not a frontend-computed product control

Product decision:

1. Fig View does not compute or judge the golden equation itself
2. Fig View may show a backend-provided implementation status or backend-provided derived values if and only if the backend exposes them explicitly
3. if the backend does not expose this safely, Fig View only references it in explanatory help text or backend-validation status, not as a fabricated graph metric

Fig View should surface:

1. graph similarity distance
2. relation distance
3. inheritance distance
4. topology quality summaries

These are defined below as product concepts so implementation is not left open.

## 11. Exact Product Decisions For Previously Open Topics

This section closes all remaining product-definition gaps so the implementation plan has no unresolved UX ambiguity.

### 11.1 Timeline and temporal slider

Decision:

1. Fig View v1 includes a lightweight timeline control
2. this is not a full replay studio
3. the timeline shows recent graph activity windows and lets the user step through recent event-derived graph changes

What the user can do:

1. jump to latest
2. move backward through recent graph event groups
3. replay recent change pulses visually
4. inspect what changed in relation to current selection

What it is not in v1:

1. not a full historical graph reconstruction engine
2. not a replacement for the Evolution page timeline/reporting

Default v1 behavior:

1. last `N` recent relevant events only, bounded by backend and UI performance rules
2. recent categories include:
   - evolve complete
   - prune-related
   - invention-related
   - diagnostics snapshot markers
   - retrieval-touch overlays when useful

### 11.2 Similarity controls

Decision:

1. Fig View includes a user-facing similarity control panel
2. this panel is for exploration filtering, not for changing backend memory truth

Similarity controls should include:

1. similarity emphasis slider
2. relation visibility threshold
3. toggle between:
   - local neighborhood relevance
   - inheritance emphasis
   - opposition emphasis
   - retrieval emphasis

Behavior:

1. slider changes visual filtering or ranking of already-loaded graph relations
2. slider does not rewrite backend graph structure
3. if backend later supports similarity-threshold query parameters, the UI may request filtered neighborhoods, but still as read-only exploration

Default semantics:

1. low threshold means more relations visible
2. high threshold means stronger relations only

### 11.3 Node title and label strategy

Decision:

1. every node must have a safe display title in Fig View
2. title generation must follow a strict priority order

Priority order:

1. backend-provided safe title if later exposed explicitly
2. safe derived label from source metadata or anchor metadata
3. block-based or source-type label
4. fallback short node id

Rules:

1. no raw full document text as title
2. no unsanitized payload fragments
3. no tenant-unsafe content
4. hover cards use short label
5. inspector can show the fuller safe label variant if available

### 11.4 Memory state model

Decision:

Fig View uses a defined display-state taxonomy even if backend support is phased in gradually.

Display states:

1. active
2. historical
3. compressed
4. deduplicated
5. pruned
6. cold
7. deactivated

Meaning:

1. active:
   - current working memory node or normal visible graph node
2. historical:
   - graph node important for recent history or lineage but not currently primary
3. compressed:
   - node represented as aggregated or macro-level memory
4. deduplicated:
   - node or source lineage reused from prior packetized content
5. pruned:
   - node removed or flagged by pruning logic and shown only as historical effect if backend exposes it
6. cold:
   - low-access, low-retrieval, low-activity memory state
7. deactivated:
   - hidden from normal active traversal but still inspectable through history or state filters if backend exposes it

Default v1 display rule:

1. active, compressed, and deduplicated are first-class visible states
2. pruned, cold, historical, and deactivated are visible when backend truth exists or can be safely derived
3. absent backend truth means those states are hidden rather than guessed

### 11.5 Graph state persistence

Decision:

Fig View persists view state per user/session locally.

Persisted view state:

1. selected layout mode
2. legend/filter selections
3. lock/unlock preference
4. hover-card preference
5. last focused node id when still valid
6. camera preset preference if stable enough

Not persisted across sessions unless proven safe and useful:

1. transient timeline position
2. ephemeral search queries
3. stale event cursor

Persistence rules:

1. local-only by default
2. never bypass tenant context
3. never restore a node selection into the wrong graph

### 11.6 Next and previous relevant memory ordering

Decision:

Relevant navigation follows a deterministic ranking stack.

Order of evaluation:

1. current selected node's direct visible neighborhood
2. strongest relation score among currently active mode
3. tie-break by relation type priority
4. tie-break by graph distance
5. final tie-break by stable node id ordering

Mode-specific relation priority:

1. Explore:
   - strongest overall linked visible nodes first
2. Analyze:
   - same-cluster and bridge-strength ordering first
3. Lineage:
   - parents and children first, ordered by inheritance fraction

Relation type priority defaults:

1. inheritance
2. retrieval-relevant
3. semantic similarity
4. opposition

### 11.7 Distances and relation metrics

Decision:

Fig View includes explicit graph-distance concepts in the inspector and relation panels.

Distance concepts:

1. graph hop distance
2. similarity distance
3. inheritance distance
4. relation strength distance

Definitions for product behavior:

1. graph hop distance:
   - number of traversed edges from current node
2. similarity distance:
   - inverse or transformed relation-strength measure used only if backend exposes a safe score
3. inheritance distance:
   - depth and fraction-based conceptual separation across lineage
4. relation strength distance:
   - normalized closeness score for ranking visible relation importance

Display rule:

1. show the metric only if value is available
2. otherwise show the category without a fabricated number

### 11.8 Graph topology quality

Decision:

Fig View includes a graph-topology quality summary panel.

It should summarize:

1. density
2. redundancy
3. entropy
4. structural balance
5. bridge concentration
6. macro-to-atom composition

UI purpose:

1. help the user understand whether the graph is sparse, noisy, compressed, over-clustered, or healthy

### 11.9 Self-organization signals

Decision:

Fig View includes a self-organization signal group from the graph perspective.

Signals should communicate:

1. cluster emergence
2. macro-node formation
3. decreasing entropy trend
4. relation densification
5. repeated retrieval concentration

This is explanatory, not a replacement for evolution controls.

### 11.10 Links to open detail pages

Decision:

Fig View includes contextual deep links where useful.

Possible links:

1. open related Storage provenance detail
2. open Evolution page for broader operational context
3. open source file or source record page if such route exists later

Rules:

1. deep links are optional helper actions
2. they must preserve tenant safety
3. they must never expose unavailable internal paths

### 11.11 Compression and merge signals

Decision:

Fig View explicitly distinguishes:

1. compressed conceptual nodes
2. merged graph outcomes
3. macro emergence

Visual treatment:

1. compressed or macro nodes receive distinct legend identity
2. merge outcomes appear as recent-change overlays
3. inspector shows compression/merge context where available

### 11.12 Redundancy, novelty, confidence, energy, salience

Decision:

Fig View supports these as inspectable graph-quality signals.

Display rules:

1. graph-level values belong in metrics panels
2. node-level values belong in inspector cards when backend supplies them or when they can be safely derived from loaded graph data
3. no fabricated precision

Signal meanings:

1. redundancy:
   - overlap or repeated semantic mass
2. novelty:
   - residual or new conceptual contribution
3. confidence:
   - relation or extraction confidence where explicitly available
4. energy:
   - graph vitality or useful dynamic intensity from backend metric context
5. salience:
   - visible importance rank for navigation, derived from safe graph signals such as touch count, relation strength, and state

### 11.13 Similarity relationships

Decision:

Similarity relationships appear as a first-class exploration layer.

They should be visible through:

1. relation filters
2. hover summaries
3. inspector relation panels
4. next/previous relevant memory ordering

If the backend does not expose explicit similarity edges in v1:

1. similarity remains a derived relation layer from safe graph scoring or neighborhood explanation results
2. the UI does not fabricate invisible edges as backend truth

### 11.14 Forgotten, cold, deactivated, historical, and live indicators

Decision:

These states are part of the Fig View conceptual model and should be represented visually when backend truth supports them.

Visual defaults:

1. live/active:
   - bright, fully interactive
2. historical:
   - muted but visible
3. compressed:
   - compact and macro-distinct
4. cold:
   - dimmed state
5. deactivated:
   - hidden by default, revealable by state filter
6. pruned:
   - not shown as active node, but shown in history/timeline/overlay where available
7. deduplicated:
   - reuse badge or provenance indicator

### 11.15 Graph causality and history

Decision:

Fig View includes graph history from an exploration perspective.

What is included:

1. recent event overlays
2. selected-node recent change context
3. timeline stepping across recent graph changes
4. causal hints from event kinds and relation changes

What is excluded from v1:

1. full offline graph-state reconstruction engine

### 11.16 Prune candidate state

Decision:

Fig View includes a prune-candidate indicator when backend truth supports it.

If backend does not expose an explicit prune-candidate field in v1:

1. show only confirmed prune effects from events
2. do not label nodes as prune candidates by guess

## 12. Data Requirements

Fig View needs:

1. graph snapshot
2. node list
3. edge list
4. graph version
5. last event sequence
6. graph metrics
7. node detail
8. node explain detail
9. node provenance detail
10. file provenance detail where relevant
11. recent events

Current gap:

1. existing backend has many of these pieces, but not one dedicated aggregate graph API surface for canvas-ready loading

That means Fig View likely needs a graph router rather than stitching many large page-load requests client-side.

## 13. Safety Rules

Fig View must respect these non-negotiables:

1. existing code structure must remain stable
2. existing integrations and connections must not be broken
3. auth and tenant isolation must remain strict
4. encryption, cryptography, and secure storage behavior must not be weakened
5. existing backend and frontend behavior must not regress
6. existing workflows for Storage, Evolution, Memory, Query, Jobs, Events, and Profile must not be broken

Specifically, Fig View must not:

1. bypass backend auth with local fallback logic
2. expose raw secret or credential data
3. expose raw document payloads by default
4. repurpose existing endpoints in a breaking way
5. mutate graph state during read-only graph exploration

## 14. What the Final Fig View Should Feel Like

It should feel:

1. powerful
2. exact
3. highly organized
4. safe
5. inspectable
6. stable
7. trustworthy

It should not feel:

1. decorative only
2. chaotic
3. toy-like
4. like a generic graph demo

The user should leave Fig View with clear answers about graph structure, provenance, lineage, opposition, retrieval context, and graph health.

## 15. Verification-Required Items

These should not be assumed to have backend support until explicitly verified or contract-added, but the product behavior itself is already defined above:

1. explicit cold-state / forgotten-state graph contracts
2. backend-exposed golden-equation implementation status or derived values
3. fully defined node titles/labels beyond safe derived identifiers
4. full temporal replay if not backed by a dedicated graph replay contract
5. explicit compressed-memory or historical-memory state markers if not yet exposed by backend truth

These are implementation verification items, not product-definition gaps.
