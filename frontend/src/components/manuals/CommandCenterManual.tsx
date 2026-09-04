"use client";

import React from "react";
import {
  ManualShell,
  SectionHeading,
  SubHeading,
  Callout,
  DTable,
  K,
  type TocItem,
} from "@/components/manuals/ManualShell";

const TOC: TocItem[] = [
  { id: "overview", label: "1. Introduction" },
  {
    id: "realtime",
    label: "2. Live Data Architecture",
    children: [
      { id: "rt-sse", label: "SSE Event Stream" },
      { id: "rt-poll", label: "Polling Fallback" },
      { id: "rt-endpoints", label: "Data Endpoints" },
    ],
  },
  {
    id: "kpi",
    label: "3. KPI Strip",
    children: [
      { id: "kpi-nodes", label: "Active Nodes" },
      { id: "kpi-storage", label: "Storage Used" },
      { id: "kpi-keys", label: "API Keys" },
      { id: "kpi-health", label: "System Health" },
    ],
  },
  {
    id: "spectrum",
    label: "4. Graph Topology Spectrum",
    children: [
      { id: "spec-metrics", label: "D / H / λ" },
      { id: "spec-history", label: "Historical Sampling" },
    ],
  },
  {
    id: "fig3d",
    label: "5. Live Cortex 3D Graph",
    children: [
      { id: "fig-data", label: "Real Topology Data" },
      { id: "fig-colors", label: "Node / Edge Colors" },
      { id: "fig-states", label: "Loading & Empty States" },
    ],
  },
  {
    id: "activity",
    label: "6. Event Velocity & Activity Log",
    children: [
      { id: "act-feed", label: "Live Activity Feed" },
      { id: "act-kinds", label: "Event Kinds" },
      { id: "act-velocity", label: "Throughput Chart" },
    ],
  },
  {
    id: "gauges",
    label: "7. Topology Metrics (D / H / λ)",
    children: [
      { id: "gauge-d", label: "D — Density" },
      { id: "gauge-h", label: "H — Entropy" },
      { id: "gauge-lambda", label: "λ — Spectral Radius" },
    ],
  },
  {
    id: "commands",
    label: "8. Quick Command Matrix",
    children: [
      { id: "cmd-shortcuts", label: "Shortcuts" },
      { id: "cmd-upload", label: "Upload to FAIM" },
    ],
  },
  { id: "security", label: "9. Security & Auth Keys" },
  {
    id: "evolution",
    label: "10. Evolution Engine",
    children: [
      { id: "evo-run", label: "Running Evolution" },
      { id: "evo-status", label: "Status Semantics" },
    ],
  },
  {
    id: "infrastructure",
    label: "11. Worker Pool & GPU Acceleration",
    children: [
      { id: "infra-workers", label: "Worker Pool Topology" },
      { id: "infra-gpu", label: "GPU Acceleration Status" },
    ],
  },
  {
    id: "telemetry",
    label: "12. Storage, Mini-Map & Pipeline Telemetry",
    children: [
      { id: "tel-storage", label: "Storage Modality Breakdown" },
      { id: "tel-minimap", label: "Bird's Eye Mini-Map" },
      { id: "tel-latency", label: "Pipeline Latency & Health" },
      { id: "tel-cache", label: "Cache Hit Rate & Retention" },
    ],
  },
  { id: "troubleshoot", label: "13. Troubleshooting" },
  {
    id: "quickstart",
    label: "14. Quick Start",
    children: [
      { id: "qs-first", label: "First Login" },
      { id: "qs-ingest", label: "Ingest Your First Document" },
      { id: "qs-evolve", label: "Run Your First Evolution" },
      { id: "qs-fig", label: "Explore the FIG View" },
    ],
  },
  {
    id: "bestpractices",
    label: "15. Best Practices & Tips",
    children: [
      { id: "bp-ingest", label: "Ingestion Strategy" },
      { id: "bp-evolve", label: "Evolution Cadence" },
      { id: "bp-monitor", label: "Monitoring Health" },
      { id: "bp-keys", label: "API Key Hygiene" },
    ],
  },
  {
    id: "interpret",
    label: "16. Metrics Interpretation Guide",
    children: [
      { id: "interp-d", label: "Reading Density (D)" },
      { id: "interp-h", label: "Reading Entropy (H)" },
      { id: "interp-lambda", label: "Reading Spectral Radius (λ)" },
      { id: "interp-combined", label: "Combined Signals" },
    ],
  },
  {
    id: "glossary",
    label: "17. Glossary",
    children: [
      { id: "glossary-core", label: "Core Terms" },
      { id: "glossary-metrics", label: "Metrics" },
      { id: "glossary-events", label: "Event Types" },
    ],
  },
  {
    id: "faq",
    label: "18. FAQ",
  },
];

export function CommandCenterManual({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  return (
    <ManualShell
      open={open}
      onClose={onClose}
      title="Command Center — User Manual"
      subtitle="Real-Time Graph Health · Activity Feed · Operational Controls"
      toc={TOC}
      accent="#22d3ee"
    >
      <SectionHeading id="overview" kicker="Chapter 01" title="Introduction">
        <p>
          The Command Center is the live operational view of your FAIM graph. It
          aggregates real backend telemetry — node and edge counts, storage
          usage, API key state, system health, evolution status — and surfaces
          them as a single control surface. Nothing on this page is generated
          client-side: every number and visualization is backed by a live API
          call to the FAIM backend.
        </p>
        <Callout tone="info" title="All data is real">
          The charts and the 3D graph render actual graph data fetched from the
          backend — not placeholder or decorative series. Empty states are
          shown honestly while the graph is empty or while the first samples
          are still arriving.
        </Callout>
      </SectionHeading>

      <SectionHeading id="realtime" kicker="Chapter 02" title="Live Data Architecture">
        <p>
          The page uses a hybrid push + pull model so updates arrive quickly
          without hammering the backend.
        </p>

        <SubHeading id="rt-sse">SSE Event Stream</SubHeading>
        <p>
          The activity feed subscribes to the backend Server-Sent Events
          endpoint <span className="font-mono text-cyan-300">/api/v1/events/stream</span>{" "}
          once the initial event history is loaded. It resumes from your last
          known sequence number (<span className="font-mono text-cyan-300">after_seq</span>),
          so no events are skipped or replayed. The backend sends a heartbeat
          every 15 seconds to keep the connection alive, and the client
          reconnects automatically with a 3-second backoff if the stream drops.
        </p>

        <SubHeading id="rt-poll">Polling Fallback</SubHeading>
        <p>
          Because a stream can silently stall, the dashboard keeps a safety-net
          poll of the event journal every 15 seconds — but only while the SSE
          connection is unhealthy. Duplicate events are de-duplicated by event
          id, so overlap between the stream and the poll never shows double
          entries. The scorecard, storage summary, and evolution status are
          refreshed on a 30-second cadence.
        </p>

        <SubHeading id="rt-endpoints">Data Endpoints</SubHeading>
        <DTable
          head={["Panel", "Endpoint", "Cadence"]}
          rows={[
            {
              cells: [
                "Active Nodes",
                <span className={K.mono} key="e1">/api/v1/metrics/scorecard</span>,
                "30s",
              ],
            },
            {
              cells: [
                "Storage Used",
                <span className={K.mono} key="e2">/api/v1/storage/summary</span>,
                "30s",
              ],
            },
            {
              cells: [
                "API Keys",
                <span className={K.mono} key="e3">/api/v1/api-keys</span>,
                "on load",
              ],
            },
            {
              cells: [
                "System Health",
                <span className={K.mono} key="e4">/api/health</span>,
                "on load",
              ],
            },
            {
              cells: [
                "3D Cortex Graph",
                <span className={K.mono} key="e5">/api/v1/graph/surface</span>,
                "30s",
              ],
            },
            {
              cells: [
                "Event Activity",
                <span className={K.mono} key="e6">/api/v1/events/stream</span>,
                "SSE real-time",
              ],
            },
            {
              cells: [
                "Evolution Status",
                <span className={K.mono} key="e7">/api/v1/evolve/status</span>,
                "30s",
              ],
            },
          ]}
        />
      </SectionHeading>

      <SectionHeading id="kpi" kicker="Chapter 03" title="KPI Strip">
        <p>
          The top row shows four live counters. Each card carries an accent bar
          whose color matches its series, and a skeleton shimmer while the
          first fetch is in flight.
        </p>

        <SubHeading id="kpi-nodes">Active Nodes</SubHeading>
        <p>
          Total nodes and edges in your graph, straight from the scorecard
          endpoint. These counts reflect the live graph version shown next to
          the topology chart.
        </p>

        <SubHeading id="kpi-storage">Storage Used</SubHeading>
        <p>
          Total bytes across all stored files (auto-formatted as KB / MB / GB)
          and the total file count from the storage summary.
        </p>

        <SubHeading id="kpi-keys">API Keys</SubHeading>
        <p>
          Total API keys configured for your tenant and how many are currently
          active (not revoked or expired).
        </p>

        <SubHeading id="kpi-health">System Health</SubHeading>
        <p>
          Liveness of the backend plus measured latency in milliseconds. The
          badge in the header shows <span className="font-mono text-emerald-300">System Online</span>{" "}
          when the health endpoint reports ok.
        </p>
      </SectionHeading>

      <SectionHeading id="spectrum" kicker="Chapter 04" title="Graph Topology Spectrum">
        <p>
          This chart plots three graph-theoretic measures over time: Density
          (D), Entropy (H), and Spectral Radius (λ). You can toggle each series
          on and off with the buttons above the chart.
        </p>

        <SubHeading id="spec-metrics">D / H / λ</SubHeading>
        <p>
          The three series come from the backend scorecard — specifically the{" "}
          <span className="font-mono text-cyan-300">dimension_D</span>,{" "}
          <span className="font-mono text-cyan-300">entropy_H</span>, and{" "}
          <span className="font-mono text-cyan-300">pressure_lambda</span>{" "}
          fields, which are computed by the fractal-physics engine and emitted
          as DIAGNOSTICS_SNAPSHOT events during ingest and evolution.
        </p>

        <SubHeading id="spec-history">Historical Sampling</SubHeading>
        <p>
          On load the chart is seeded with up to 10 real DIAGNOSTICS_SNAPSHOT
          samples pulled from the event journal, then a fresh live point is
          appended every 30 seconds. If no diagnostics samples exist yet, the
          chart shows a "waiting for real-time telemetry" state instead of a
          fabricated curve.
        </p>
        <Callout tone="warn" title="Fresh graphs">
          A brand-new graph with no ingest activity has no metrics snapshot, so
          the spectrum chart stays empty until evolution or ingest emits the
          first diagnostics event.
        </Callout>
      </SectionHeading>

      <SectionHeading id="fig3d" kicker="Chapter 05" title="Live Cortex 3D Graph">
        <p>
          The 3D panel is a live preview of the actual knowledge graph — the
          same surface data used by the full FIG view at{" "}
          <span className="font-mono text-cyan-300">/dashboard/graph</span>,
          capped to 30 nodes and 60 edges for the small canvas.
        </p>

        <SubHeading id="fig-data">Real Topology Data</SubHeading>
        <p>
          Every 30 seconds the canvas refetches{" "}
          <span className="font-mono text-cyan-300">/api/v1/graph/surface</span>{" "}
          and re-lays out your real nodes and links. Node size reflects access
          activity (touch count), so frequently used memories render larger.
          The canvas auto-rotates so you can inspect clusters.
        </p>

        <SubHeading id="fig-colors">Node / Edge Colors</SubHeading>
        <p>
          Node and edge colors encode the node kind. The palette maps common
          kinds such as concepts (cyan), facts (green), events (violet),
          entities (amber), procedures (emerald), and macro nodes (pink);
          unknown kinds render slate gray.
        </p>

        <SubHeading id="fig-states">Loading & Empty States</SubHeading>
        <p>
          The panel is explicit about what it is showing: a "LOADING GRAPH
          DATA…" label while fetching, a "NO GRAPH DATA YET" state when the
          graph is empty, and the real node/edge count in the LIVE CORTEX badge
          once data is rendered.
        </p>
        <Callout tone="info" title="Inspect deeper">
          Click the <span className="font-mono text-cyan-300">Inspect</span>{" "}
          link in the panel header to open the full interactive FIG view with
          search, timeline stepping, and node inspection.
        </Callout>
      </SectionHeading>

      <SectionHeading id="activity" kicker="Chapter 06" title="Event Velocity & Activity Log">
        <p>
          Two panels work together to show what the engine is doing right now:
          a rolling throughput chart and a live event feed.
        </p>

        <SubHeading id="act-feed">Live Activity Feed</SubHeading>
        <p>
          Every graph event is shown as a row with a colored kind tag, a
          human-readable summary, and a relative timestamp (e.g.{" "}
          <span className="font-mono">just now</span>,{" "}
          <span className="font-mono">12s ago</span>). New events stream in
          instantly over SSE and are capped to the 50 most recent. The counter
          in the velocity panel header shows the latest sequence number and the
          total event count.
        </p>

        <SubHeading id="act-kinds">Event Kinds</SubHeading>
        <p>Each kind is color-coded so you can scan activity at a glance:</p>
        {/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Kind", "Tag", "Meaning"]}
          rows={[
            { cells: ["NODE_UPSERT", "UPSERT", "A memory node was created or updated"] },
            { cells: ["INVENT_MACRO_NODE", "MACRO", "The engine invented a macro node"] },
            { cells: ["PRUNE_NODE", "PRUNE", "A node was pruned from the graph"] },
            { cells: ["MERGE / EVOLUTION_MERGE", "MERGE / EVOLVE", "Edges or nodes were merged"] },
            { cells: ["EVOLUTION_COMPLETE", "EVOLVED", "An evolution pass finished"] },
            { cells: ["EVOLUTION_SKIPPED", "SKIP", "Evolution ran but found nothing to change"] },
            { cells: ["GRAPH_VERSION_BUMP", "VERSION", "Graph version advanced"] },
            { cells: ["QUERY_*", "QUERY / RANK / DONE", "Query lifecycle: start, rerank, complete"] },
            { cells: ["STORAGE_RAW_STORED", "STORE", "A raw file was stored"] },
            { cells: ["STORAGE_ENCRYPT_FAILED", "ERR", "Encryption failed during storage"] },
          ]}
        />

        <SubHeading id="act-velocity">Throughput Chart</SubHeading>
        <p>
          The velocity chart measures genuine event throughput: a rolling count
          of events received in the last 60 seconds, sampled at each event
          arrival. It reflects the true ingest / evolution rate in events per
          minute, not a placeholder.
        </p>
      </SectionHeading>

      <SectionHeading id="gauges" kicker="Chapter 07" title="Topology Metrics (D / H / λ)">
        <p>
          Three gauges summarize graph health with human-readable labels and
          thresholds. A gauge shows <span className="font-mono">—</span> with
          the hint "no snapshot" when the backend has not yet produced a
          metrics snapshot.
        </p>

        <SubHeading id="gauge-d">D — Density</SubHeading>
        <p>
          Edge-to-node richness. <span className="text-cyan-300">dense</span>{" "}
          above 0.15, <span className="text-amber-300">sparse</span> between
          0.05 and 0.15, <span className="text-slate-400">disconnected</span>{" "}
          below 0.05.
        </p>

        <SubHeading id="gauge-h">H — Entropy</SubHeading>
        <p>
          Semantic diversity of the graph.{" "}
          <span className="text-violet-300">diverse</span> above 0.8,{" "}
          <span className="text-amber-300">moderate</span> between 0.3 and 0.8,{" "}
          <span className="text-slate-400">uniform</span> below 0.3.
        </p>

        <SubHeading id="gauge-lambda">λ — Spectral Radius</SubHeading>
        <p>
          Connectivity scale. <span className="text-emerald-300">clustered</span>{" "}
          at or above 2.0, <span className="text-amber-300">moderate</span>{" "}
          between 0.5 and 2.0, <span className="text-slate-400">sparse</span>{" "}
          below 0.5.
        </p>
      </SectionHeading>

      <SectionHeading id="commands" kicker="Chapter 08" title="Quick Command Matrix">
        <p>
          One-click navigation to the most-used FAIM areas, plus the file upload
          action. Each command shows its keyboard hint.
        </p>

        <SubHeading id="cmd-shortcuts">Shortcuts</SubHeading>
        {/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Command", "Keyboard", "Destination"]}
          rows={[
            { cells: ["Open FIG View", "⌘G", "Interactive graph explorer"] },
            { cells: ["FAIM Cortex", "⌘M", "Semantic memory query"] },
            { cells: ["View Journal", "⌘J", "Append-only event journal"] },
            { cells: ["API Keys", "⌘K", "Key management"] },
            { cells: ["Storage", "⌘S", "File and retention management"] },
          ]}
        />

        <SubHeading id="cmd-upload">Upload to FAIM</SubHeading>
        <p>
          The <span className="font-mono text-cyan-300">Upload to FAIM</span>{" "}
          button opens a file picker for the active graph. The upload streams
          with real byte progress, and the storage card plus activity feed
          refresh shortly after completion.
        </p>
      </SectionHeading>

      <SectionHeading id="security" kicker="Chapter 09" title="Security & Auth Keys">
        <p>
          This panel reports how many API keys are active for your tenant. The
          green indicator means at least one key is active. Use the{" "}
          <span className="font-mono text-cyan-300">Manage</span> link to open
          the full key matrix where you can create, rotate, and revoke keys.
          Every dashboard API request is authenticated with your session token.
        </p>
        <Callout tone="success" title="Isolation">
          All data shown is scoped to your tenant and graph. The backend
          derives your tenant from your session token, so you only ever see
          your own graph and storage.
        </Callout>
      </SectionHeading>

      <SectionHeading id="evolution" kicker="Chapter 10" title="Evolution Engine">
        <p>
          FAIM runs autonomous graph self-organization: merging redundant
          memories, inventing macro nodes, pruning stale structures, and
          bumping the graph version.
        </p>

        <SubHeading id="evo-run">Running Evolution</SubHeading>
        <p>
          Click <span className="font-mono text-emerald-300">Run Evolution</span>{" "}
          to trigger a strict-profile evolution pass on the active graph. The
          button disables while a job is already running. After submission the
          page re-checks status and re-fetches the scorecard and activity feed
          to show the results.
        </p>

        <SubHeading id="evo-status">Status Semantics</SubHeading>
        <p>
          Status colors tell you the engine state at a glance:{" "}
          <span className="text-cyan-300">running</span> (worker active),{" "}
          <span className="text-emerald-300">completed</span> (last job
          finished cleanly), <span className="text-rose-300">error / failed</span>{" "}
          (last job errored), and slate when idle. The worker count, if shown,
          reflects how many background evolution workers are online.
        </p>
      </SectionHeading>

      <SectionHeading id="infrastructure" kicker="Chapter 11" title="Worker Pool & GPU Acceleration">
        <p>
          FAIM employs a decoupled, asynchronous micro-worker architecture for
          ingestion pipelines, vector indexing, graph evolution, and hardware
          acceleration. The infrastructure strip gives immediate visibility into
          thread concurrency, task queues, and hardware compute state.
        </p>

        <SubHeading id="infra-workers">Worker Pool Topology</SubHeading>
        <p>
          The Worker Pool card tracks four distinct subsystem services in real time:
        </p>
        {/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Subsystem", "Role & Responsibility", "State Indicators"]}
          rows={[
            {
              cells: [
                "Evolution Workers",
                "Asynchronous background workers executing graph entropy reduction and memory self-organization passes.",
                <span key="evolution-workers" className="font-mono text-[10px] text-emerald-300">IDLE · RUNNING (X active) · OFFLINE</span>,
              ],
            },
            {
              cells: [
                "Ingest Pipeline",
                "Multi-stage document parsing, markdown extraction, token chunking, and semantic embedding generation.",
                <span key="ingest-pipeline" className="font-mono text-[10px] text-cyan-300">IDLE · QUEUED · N jobs/s throughput</span>,
              ],
            },
            {
              cells: [
                "Vector Index",
                "Qdrant HNSW vector search database connection health, payload filtering, and indexing status.",
                <span key="vector-index" className="font-mono text-[10px] text-violet-300">CONNECTED · DISCONNECTED</span>,
              ],
            },
            {
              cells: [
                "GPU Accelerator",
                "NVIDIA CUDA hardware offloading for embedding inference and deep neural re-ranking models.",
                <span key="gpu-accelerator" className="font-mono text-[10px] text-amber-300">CUDA ACTIVE · CPU FALLBACK · DISABLED</span>,
              ],
            },
          ]}
        />

        <SubHeading id="infra-gpu">GPU Acceleration Status</SubHeading>
        <p>
          The GPU radial utilization gauge displays whether your deployment is
          leveraging dedicated GPU compute (CUDA/TensorRT) or operating in CPU fallback
          mode. When hardware acceleration is enabled, vector embeddings and neural
          re-ranking operations achieve sub-5ms latencies.
        </p>
        <Callout tone="info" title="CPU Fallback">
          If NVIDIA GPU drivers are unavailable in your container or host, FAIM
          transparently switches to quantized CPU matrix operations without dropping queries.
        </Callout>
      </SectionHeading>

      <SectionHeading id="telemetry" kicker="Chapter 12" title="Storage, Mini-Map & Pipeline Telemetry">
        <p>
          The right operational rail provides multi-modal storage analytics, bird's-eye
          spatial graph previews, hot cache telemetry, and end-to-end ingestion pipeline
          latency heatmaps.
        </p>

        <SubHeading id="tel-storage">Storage Modality Breakdown</SubHeading>
        <p>
          Documents ingested into FAIM are classified and stored by their true
          modality. The interactive bar chart dynamically visualizes file distributions:
        </p>
        {/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Modality", "File Types", "Processing Pipeline"]}
          rows={[
            { cells: ["PDF", ".pdf", "OCR extraction + layout-aware section chunking"] },
            { cells: ["TEXT", ".txt, .md, .rst", "Direct tokenization + AST header parsing"] },
            { cells: ["TABLE", ".csv, .xlsx, .tsv", "Tabular schema extraction + row-level embedding"] },
            { cells: ["IMAGE", ".png, .jpg, .webp", "Vision transformer embedding + caption indexing"] },
            { cells: ["RAW", ".bin, .zip, other", "Encrypted blob storage with metadata indexing"] },
          ]}
        />

        <SubHeading id="tel-minimap">Bird's Eye Mini-Map</SubHeading>
        <p>
          The Mini-Map renders a lightweight 2D canvas radar showing active
          knowledge clusters and edge connections. It provides instant topological
          awareness of graph partitioning without requiring full 3D WebGL camera navigation.
        </p>

        <SubHeading id="tel-latency">Pipeline Latency & Health Heatmap</SubHeading>
        <p>
          Tracks the live queue depth, end-to-end throughput (jobs/second), and hot
          in-memory cache size. Provides visual indicators when queue depth exceeds
          normal operating thresholds.
        </p>

        <SubHeading id="tel-cache">Cache Hit Rate & Retention</SubHeading>
        <p>
          Measures the proportion of queries and graph traversals served directly
          from Redis/memory without disk or vector re-computation. A high hit rate
          (&gt;75%) ensures ultra-responsive Cortex turns.
        </p>
      </SectionHeading>

      <SectionHeading id="troubleshoot" kicker="Chapter 13" title="Troubleshooting">
        <SubHeading id="trouble-empty">Empty charts on a new graph</SubHeading>
        <p>
          A fresh graph has no diagnostics snapshot yet. Ingest a document or
          run evolution — the spectrum chart and velocity chart will populate
          with the first real samples.
        </p>

        <SubHeading id="trouble-3d">3D graph shows "no graph data"</SubHeading>
        <p>
          The panel reads from the live surface endpoint. If your graph has no
          nodes yet, that state is accurate — upload content to populate it. If
          the panel shows an error state, the surface fetch failed and it
          retries automatically on the 30-second cadence.
        </p>

        <SubHeading id="trouble-feed">Activity feed pauses</SubHeading>
        <p>
          The feed reconnects on its own. If it ever appears stale, click{" "}
          <span className="font-mono text-cyan-300">Refresh</span> in the header
          to force a full reload of every panel, including re-seeding chart
          history from the event journal.
        </p>
        <SubHeading id="trouble-health">"Checking…" health</SubHeading>
        <p>
          If the System Health card stays in the checking state, the health
          endpoint is unreachable from your browser. Confirm the backend is up
          and reachable, then press Refresh.
        </p>
      </SectionHeading>

      <SectionHeading id="quickstart" kicker="Chapter 14" title="Quick Start">
        <p>
          New to FAIM? This walkthrough gets you from empty graph to live
          intelligence in four steps.
        </p>

        <SubHeading id="qs-first">First Login</SubHeading>
        <p>
          After signing in you land on the Command Center. If the KPI strip shows
          <span className="font-mono text-slate-400">0 nodes</span> and{" "}
          <span className="font-mono text-slate-400">0 B storage</span>, your graph
          is empty — that is expected. The <span className="font-mono text-emerald-300">System Online</span>{" "}
          badge confirms the backend is reachable.
        </p>

        <SubHeading id="qs-ingest">Ingest Your First Document</SubHeading>
        <ol className="list-decimal list-inside space-y-2 text-sm text-slate-300">
          <li>
            Click <span className="font-mono text-cyan-300">Upload to FAIM</span> in
            the Quick Command Matrix (or press <span className="font-mono">⌘S</span>
            then choose the file).
          </li>
          <li>
            Select a PDF, Markdown, or text file. The upload streams with real
            byte progress; the Storage card updates on completion.
          </li>
          <li>
            Ingest runs automatically — watch the Activity Log for{" "}
            <span className="font-mono text-blue-300">STORE</span> and{" "}
            <span className="font-mono text-cyan-300">UPSERT</span> events as
            nodes are created.
          </li>
        </ol>
        <Callout tone="info" title="Supported formats">
          PDF, Markdown, plain text, CSV, JSON, and Office documents. Large
          files stream in chunks; progress is shown per-byte.
        </Callout>

        <SubHeading id="qs-evolve">Run Your First Evolution</SubHeading>
        <p>
          Once you have a handful of nodes, click{" "}
          <span className="font-mono text-emerald-300">Run Evolution</span> in the
          Evolution Engine card. The status changes to{" "}
          <span className="text-cyan-300">running</span> while background
          workers merge duplicates, build lineage edges, and compute the first
          spectral metrics snapshot.
        </p>

        <SubHeading id="qs-fig">Explore the FIG View</SubHeading>
        <p>
          Click <span className="font-mono text-cyan-300">Open FIG View</span> in
          the Quick Command Matrix (or press <span className="font-mono">⌘G</span>).
          The full 3D interactive explorer opens with camera controls, node
          inspector, neighborhood expansion, and explain overlays.
        </p>
      </SectionHeading>

      <SectionHeading id="bestpractices" kicker="Chapter 15" title="Best Practices & Tips">
        <SubHeading id="bp-ingest">Ingestion Strategy</SubHeading>
        <ul className="list-disc list-inside space-y-2 text-sm text-slate-300">
          <li>
            <strong>Batch related documents</strong> — uploading a project's docs in
            one session lets evolution find cross-document patterns immediately.
          </li>
          <li>
            <strong>Use descriptive filenames</strong> — they become the
            <span className="font-mono">galaxy_id</span> in the graph, helping you
            trace nodes back to their source.
          </li>
          <li>
            <strong>Prefer text over scanned PDFs</strong> — OCR adds latency and
            can introduce noise; clean text yields cleaner nodes.
          </li>
        </ul>

        <SubHeading id="bp-evolve">Evolution Cadence</SubHeading>
        <ul className="list-disc list-inside space-y-2 text-sm text-slate-300">
          <li>
            <strong>Run evolution after every 3–5 ingests</strong> — this keeps
            the graph tight and prevents redundancy buildup.
          </li>
          <li>
            <strong>Watch the Entropy (H) gauge</strong> — if H drops below 0.3
            (uniform), the graph is oversimplified; run evolution with a fresh
            ingest to restore diversity.
          </li>
          <li>
            <strong>Use the Journal</strong> (<span className="font-mono">⌘J</span>)
            to audit exactly what evolution changed — every merge, prune, and
            macro invention is logged with before/after context.
          </li>
        </ul>

        <SubHeading id="bp-monitor">Monitoring Health</SubHeading>
        <ul className="list-disc list-inside space-y-2 text-sm text-slate-300">
          <li>
            <strong>Density (D) below 0.05</strong> — graph is fragmented; ingest
            more related content or run evolution to connect clusters.
          </li>
          <li>
            <strong>Spectral radius (λ) above 3.0</strong> — graph is over-connected
            (dense core with many weak edges); evolution will prune automatically.
          </li>
          <li>
            <strong>Event velocity sustained above 50 ev/min</strong> — indicates
            heavy ingest or evolution activity; normal for batch loads.
          </li>
          <li>
            <strong>Storage growth</strong> — the Storage card shows raw bytes;
            enable retention policies in the Storage page to auto-archive cold
            files.
          </li>
        </ul>

        <SubHeading id="bp-keys">API Key Hygiene</SubHeading>
        <ul className="list-disc list-inside space-y-2 text-sm text-slate-300">
          <li>
            <strong>Rotate keys quarterly</strong> — use the rotation grace window
            to swap credentials without downtime.
          </li>
          <li>
            <strong>Scope minimally</strong> — grant only the scopes an
            integration needs (e.g., <span className="font-mono">ingest:write</span>
            for a pipeline, not <span className="font-mono">admin</span>).
          </li>
          <li>
            <strong>Audit last-used</strong> — the key matrix shows last-used
            timestamp; revoke keys unused for 90+ days.
          </li>
        </ul>
      </SectionHeading>

      <SectionHeading id="interpret" kicker="Chapter 16" title="Metrics Interpretation Guide">
        <p>
          The three metrics (D, H, λ) are not independent — they form a
          diagnostic triangle. Here is how to read them together.
        </p>

        <SubHeading id="interp-d">Reading Density (D)</SubHeading>
        <p>
          <strong>D measures edge richness relative to nodes.</strong> A fully
          connected graph has D = 1.0; a star has D ≈ 2/N. FAIM graphs typically
          sit between 0.05 and 0.3.
        </p>
        {/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Range", "Interpretation", "Action"]}
          rows={[
            { cells: ["D < 0.05", "Disconnected / fragmented", "Ingest more related content; run evolution"] },
            { cells: ["0.05 ≤ D < 0.15", "Sparse but structured", "Healthy for early-stage graphs"] },
            { cells: ["0.15 ≤ D < 0.30", "Well-connected", "Mature knowledge base; good retrieval"] },
            { cells: ["D ≥ 0.30", "Dense core", "Strong clustering; watch for redundancy"] },
          ]}
        />

        <SubHeading id="interp-h">Reading Entropy (H)</SubHeading>
        <p>
          <strong>H measures semantic diversity.</strong> High H = many distinct
          topics; low H = repetitive or narrow coverage. FAIM uses the
          fractal-physics entropy estimator on the active adjacency spectrum.
        </p>
        {/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Range", "Interpretation", "Action"]}
          rows={[
            { cells: ["H < 0.3", "Uniform / repetitive", "Ingest diverse topics; avoid duplicate uploads"] },
            { cells: ["0.3 ≤ H < 0.8", "Moderate diversity", "Balanced; good for general queries"] },
            { cells: ["H ≥ 0.8", "Highly diverse", "Excellent coverage; retrieval spans many domains"] },
          ]}
        />

        <SubHeading id="interp-lambda">Reading Spectral Radius (λ)</SubHeading>
        <p>
          <strong>λ measures the largest eigenvalue of the normalized adjacency
          — roughly, how far a random walk travels before mixing.</strong> It
          correlates with the "effective diameter" of the graph.
        </p>
        {/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Range", "Interpretation", "Action"]}
          rows={[
            { cells: ["λ < 0.5", "Sparse / shallow", "Graph lacks connective tissue; ingest bridging docs"] },
            { cells: ["0.5 ≤ λ < 2.0", "Moderate connectivity", "Healthy small-world structure"] },
            { cells: ["2.0 ≤ λ < 3.0", "Clustered", "Strong communities; good for topical queries"] },
            { cells: ["λ ≥ 3.0", "Over-connected", "Dense hubs forming; evolution will prune"] },
          ]}
        />

        <SubHeading id="interp-combined">Combined Signals</SubHeading>
        <p>
          The three metrics together diagnose graph health more reliably than any
          single number:
        </p>
        {/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Pattern", "D / H / λ", "Meaning", "Remedy"]}
          rows={[
            { cells: ["Starved", "Low / Low / Low", "Too little content", "Ingest documents"] },
            { cells: ["Fragmented", "Low / High / Low", "Many isolated topics", "Run evolution to connect"] },
            { cells: ["Echo chamber", "High / Low / High", "Redundant core", "Ingest diverse content; run evolution"] },
            { cells: ["Healthy", "Med / High / Med", "Balanced knowledge base", "Maintain cadence"] },
            { cells: ["Overgrown", "High / Med / High", "Dense with redundancy", "Run evolution; enable retention"] },
          ]}
        />
        <Callout tone="success" title="Rule of thumb">
          A healthy FAIM graph typically settles around
          <span className="font-mono">D ≈ 0.12–0.25</span>,
          <span className="font-mono">H ≈ 0.6–0.9</span>,
          <span className="font-mono">λ ≈ 1.0–2.2</span> after a few evolution
          cycles. Deviations are not errors — they tell you what the graph needs
          next.
        </Callout>
      </SectionHeading>

      <SectionHeading id="glossary" kicker="Chapter 17" title="Glossary">
        <SubHeading id="glossary-core">Core Terms</SubHeading>
        {/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Term", "Definition"]}
          rows={[
            { cells: ["Graph", "Your tenant-scoped knowledge network: nodes (memories) + edges (relations)"] },
            { cells: ["Node", "A memory unit — fact, concept, event, entity, procedure, or macro"] },
            { cells: ["Edge", "A typed relation between nodes (e.g., SUPPORTS, CONTRADICTS, SEQUENCE)"] },
            { cells: ["Macro node", "An invented higher-level node that abstracts a recurring pattern"] },
            { cells: ["Galaxy", "A source-document grouping; all nodes from one upload share a galaxy_id"] },
            { cells: ["Temperature", "Node access tier: hot (recent), warm (occasional), cold (archived)"] },
            { cells: ["Touch count", "How many times a node has been accessed or cited in queries"] },
            { cells: ["Graph version", "Monotonically increasing counter; bumped on every structural change"] },
            { cells: ["DIAGNOSTICS_SNAPSHOT", "Event emitted after evolution/ingest with D, H, λ, and counts"] },
            { cells: ["Seq", "Monotonic event sequence number; the source of truth for ordering"] },
            { cells: ["Tenant", "Isolation boundary — all data and keys belong to exactly one tenant"] },
            { cells: ["Scope", "Permission grant on an API key (e.g., ingest:write, query:read, admin)"] },
          ]}
        />

        <SubHeading id="glossary-metrics">Metrics</SubHeading>
        {/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Symbol", "Name", "What It Measures"]}
          rows={[
            { cells: ["D", "Density", "Edge count / (node count choose 2) — structural richness"] },
            { cells: ["H", "Entropy", "Spectral entropy of normalized adjacency — semantic diversity"] },
            { cells: ["λ (lambda)", "Spectral Radius", "Largest eigenvalue — connectivity scale / effective diameter"] },
            { cells: ["R", "Redundancy", "Fraction of edges that are inferable from transitive closure"] },
            { cells: ["N", "Novelty", "Fraction of new information added since last snapshot"] },
            { cells: ["E", "Energy", "Total residual in the system — proxy for unresolved tension"] },
          ]}
        />

        <SubHeading id="glossary-events">Event Types</SubHeading>
        <p>
          The activity feed shows these event kinds (color-coded in the UI):
        </p>
        {/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Kind", "Tag", "Trigger"]}
          rows={[
            { cells: ["NODE_UPSERT", "UPSERT", "Node created or updated (ingest or evolution)"] },
            { cells: ["INVENT_MACRO_NODE", "MACRO", "Evolution invented a macro node"] },
            { cells: ["PRUNE_NODE", "PRUNE", "Evolution removed a stale node"] },
            { cells: ["MERGE", "MERGE", "Two nodes or edges merged as duplicates"] },
            { cells: ["EVOLUTION_MERGE", "EVOLVE", "Macro-node merge during evolution"] },
            { cells: ["EVOLUTION_COMPLETE", "EVOLVED", "Evolution pass finished"] },
            { cells: ["EVOLUTION_SKIPPED", "SKIP", "Evolution ran but graph unchanged"] },
            { cells: ["GRAPH_VERSION_BUMP", "VERSION", "Graph version incremented"] },
            { cells: ["QUERY_START", "QUERY", "Cortex query initiated"] },
            { cells: ["QUERY_RERANKED", "RANK", "Results reranked by late interaction"] },
            { cells: ["QUERY_TOUCH", "TOUCH", "Result node touch count incremented"] },
            { cells: ["QUERY_COMPLETE", "DONE", "Query returned results"] },
            { cells: ["STORAGE_RAW_STORED", "STORE", "Raw file persisted to storage"] },
            { cells: ["STORAGE_ENCRYPT_FAILED", "ERR", "Encryption failure during storage"] },
          ]}
        />
      </SectionHeading>

      <SectionHeading id="faq" kicker="Chapter 18" title="FAQ">
        <SubHeading id="faq-1">Why does the spectrum chart show "waiting for real-time telemetry"?</SubHeading>
        <p>
          Your graph has no DIAGNOSTICS_SNAPSHOT event yet. This happens on a
          brand-new graph before any ingest or evolution. Ingest a document and
          run evolution — the chart will seed with real samples.
        </p>

        <SubHeading id="faq-2">What does "LIVE CORTEX — 0 N · 0 E" mean?</SubHeading>
        <p>
          The 3D panel has connected to the surface endpoint but your graph has
          zero nodes. Upload a document; the badge will update to real counts on
          the next 30-second refresh.
        </p>

        <SubHeading id="faq-3">How real-time is the activity feed?</SubHeading>
        <p>
          The feed uses a persistent SSE stream from <span className="font-mono">/api/v1/events/stream</span>.
          New events appear within milliseconds of being committed to the event
          journal. A 15-second polling fallback runs only if the stream drops.
        </p>

        <SubHeading id="faq-4">Can I export the dashboard data?</SubHeading>
        <p>
          Not directly from the Command Center. Use the API endpoints directly:
          <span className="font-mono">/api/v1/metrics/scorecard</span>,
          <span className="font-mono">/api/v1/storage/summary</span>,
          <span className="font-mono">/api/v1/events</span>. The Benchmarks page
          (<span className="font-mono">/dashboard/benchmarks</span>) also has
          exportable reports.
        </p>

        <SubHeading id="faq-5">Why are the D/H/λ gauges showing "—" (dash)?</SubHeading>
        <p>
          The backend has not yet produced a metrics snapshot. This is normal for
          a fresh graph. The gauges will populate with real values once the
          first DIAGNOSTICS_SNAPSHOT event is emitted (after ingest + evolution).
        </p>

        <SubHeading id="faq-6">What keyboard shortcuts work?</SubHeading>
        <p>
          <span className="font-mono">⌘G</span> FIG View ·{" "}
          <span className="font-mono">⌘M</span> Cortex ·{" "}
          <span className="font-mono">⌘J</span> Journal ·{" "}
          <span className="font-mono">⌘K</span> API Keys ·{" "}
          <span className="font-mono">⌘S</span> Storage. These are global and
          work from anywhere in the dashboard.
        </p>

        <SubHeading id="faq-7">How do I know if evolution is actually doing something?</SubHeading>
        <p>
          Watch the Activity Log for <span className="font-mono text-emerald-300">EVOLVED</span>,
          <span className="font-mono text-blue-300">MERGE</span>,{" "}
          <span className="font-mono text-violet-300">MACRO</span>, and{" "}
          <span className="font-mono text-rose-300">PRUNE</span> events. The
          Evolution Engine panel status changes to <span className="text-cyan-300">running</span>
          while workers are active. After completion, the Topology Spectrum
          chart appends a new point with updated D/H/λ.
        </p>

        <SubHeading id="faq-8">My graph has thousands of nodes — will the 3D preview lag?</SubHeading>
        <p>
          The Command Center 3D panel caps the surface fetch at 30 nodes / 60
          edges, so it stays snappy regardless of total graph size. For the full
          graph, use the FIG view (<span className="font-mono">⌘G</span>), which
          supports progressive loading, clustering, and level-of-detail
          rendering.
        </p>

        <SubHeading id="faq-9">What happens to my data if I revoke an API key?</SubHeading>
        <p>
          Revoking a key only invalidates that credential — it does not delete
          any graph data, storage files, or events. The key's audit trail
          (created, rotated, revoked timestamps) is preserved in the API Keys
          page.
        </p>

        <SubHeading id="faq-10">How do I interpret a sudden spike in event velocity?</SubHeading>
        <p>
          A spike usually means one of: (1) a large file upload finished and
          ingest created many nodes, (2) an evolution pass ran and emitted merge/
          prune/ macro events, (3) a batch query touched many nodes. Check the
          Activity Log — the event kinds will tell you which.
        </p>
      </SectionHeading>
    </ManualShell>
  );
}
