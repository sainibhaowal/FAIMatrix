"use client";

import {
  AlertTriangle,
  BarChart2,
  Box,
  Filter,
  GitBranch,
  GitFork,
  Hash,
  Layers,
  Move,
  Network,
  RefreshCw,
  Share2,
  Zap,
} from "lucide-react";
import { useSession } from "next-auth/react";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  Badge,
  EmptyState,
  ErrorState,
  Spinner,
  useToast,
} from "@/components/ui";
import FigCanvas from "@/components/graph/FigCanvas";
import type { FigCanvasHandle } from "@/components/graph/FigCanvas";
import FigControls from "@/components/graph/FigControls";
import { fetchGraphSurface } from "@/lib/figViewApi";
import type { LayoutMode } from "@/lib/figViewLayout";
import { clearStaleGraphState, nodeStateClass, safeNodeTitle } from "@/lib/figViewSafety";
import type { FigLoadState, FigNode, FigSurfaceResponse } from "@/types/figView";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function classifyResponse(data: FigSurfaceResponse): FigLoadState {
  const warnings: string[] = [];
  if (data.truncated) {
    warnings.push(`Truncated: ${data.truncation_reason || "payload cap reached"}`);
  }
  if (!data.snapshot.consistent_read) {
    warnings.push("Snapshot assembled from multiple reads (eventual consistency)");
  }

  if (data.nodes.length === 0) {
    return { status: "empty", snapshot: data.snapshot };
  }
  if (warnings.length > 0) {
    return { status: "degraded", data, warnings };
  }
  return { status: "loaded", data };
}

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

const STATE_COLORS: Record<string, string> = {
  active: "text-emerald-400",
  cold: "text-slate-500",
  unknown: "text-slate-400",
  historical: "text-amber-400",
  pruned: "text-red-400",
  compressed: "text-blue-400",
  deduplicated: "text-violet-400",
  deactivated: "text-slate-600",
};

// ---------------------------------------------------------------------------
// Floating Drawer
// ---------------------------------------------------------------------------

function FloatingDrawer({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="absolute right-14 top-14 bottom-4 z-30 w-[360px] max-w-[90vw]">
      <div className="relative h-full overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-950/85 shadow-[0_10px_40px_rgba(0,0,0,0.55)] backdrop-blur-md">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800/60">
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-widest">{title}</span>
          <button
            onClick={onClose}
            className="rounded-md px-2 py-1 text-[10px] text-slate-400 hover:text-cyan-200 border border-slate-700/60 hover:border-cyan-400/30 transition-colors"
          >
            Close
          </button>
        </div>
        <div className="h-full overflow-auto p-3 pb-10">{children}</div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Stats pill row
// ---------------------------------------------------------------------------

function StatsPill({ data }: { data?: FigSurfaceResponse | null }) {
  const topo = data?.topology;
  const edgeKinds = topo?.edge_counts_by_kind ?? {};
  const nodeCount = topo?.node_count ?? (data?.nodes?.length || 0);
  const edgeCount = topo?.edge_count ?? (data?.edges?.length || 0);
  const oppCount = edgeKinds["opposition"] ?? edgeKinds["OPPOSITION"] ?? 0;
  const inhCount = edgeKinds["inheritance"] ?? edgeKinds["INHERITANCE"] ?? 0;

  const stats = [
    { icon: <Network size={12} className="text-cyan-400" />, label: "Nodes", value: nodeCount, color: "text-cyan-200" },
    { icon: <Share2 size={12} className="text-violet-400" />, label: "Edges", value: edgeCount, color: "text-violet-200" },
    { icon: <Layers size={12} className="text-amber-400" />, label: "Opposition", value: oppCount, color: "text-amber-200" },
    { icon: <GitBranch size={12} className="text-emerald-400" />, label: "Inheritance", value: inhCount, color: "text-emerald-200" },
  ];

  return (
    <div className="flex items-center gap-0 rounded-xl border border-slate-700/60 bg-slate-950/80 backdrop-blur-md shadow-[0_4px_24px_rgba(0,0,0,0.4)] overflow-hidden divide-x divide-slate-700/40">
      {stats.map((s) => (
        <div key={s.label} className="flex items-center gap-2 px-4 py-2">
          {s.icon}
          <span className={`font-mono text-[13px] font-semibold ${s.color}`}>
            {s.value > 0 ? s.value : s.value === 0 ? "0" : "—"}
          </span>
          <span className="text-[9px] uppercase tracking-widest text-slate-500">{s.label}</span>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Node & Edge Panels (same as before)
// ---------------------------------------------------------------------------

function NodePanel({ nodes }: { nodes: FigNode[] }) {
  if (nodes.length === 0) return <p className="text-xs text-slate-500 text-center py-4">No nodes found</p>;
  return (
    <div className="flex flex-col gap-1.5">
      {nodes.map((node) => {
        const title = safeNodeTitle(node);
        const stateClass = nodeStateClass(node);
        const color = STATE_COLORS[stateClass] ?? STATE_COLORS.unknown;
        return (
          <div key={node.node_id} className="flex items-center justify-between rounded-lg bg-slate-900/40 border border-slate-800/60 px-3 py-2 text-sm">
            <div className="flex items-center gap-2 min-w-0">
              <span className={`inline-block h-2 w-2 rounded-full ${stateClass === "active" ? "bg-emerald-400" : stateClass === "cold" ? "bg-slate-500" : "bg-slate-600"}`} />
              <span className="truncate font-medium text-slate-200" title={title}>{title}</span>
              <Badge size="sm" variant="outline">{node.kind}</Badge>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-500 shrink-0">
              <span className={color}>{stateClass}</span>
              <span className="font-mono">{node.node_id.slice(0, 6)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function EdgePanel({ edges }: { edges: FigSurfaceResponse["edges"] }) {
  if (edges.length === 0) return <p className="text-xs text-slate-500 text-center py-4">No edges found</p>;
  const kindCounts = edges.reduce<Record<string, number>>((acc, e) => { acc[e.kind] = (acc[e.kind] || 0) + 1; return acc; }, {});
  return (
    <div className="grid grid-cols-2 gap-2">
      {Object.entries(kindCounts).map(([kind, count]) => (
        <div key={kind} className="rounded-lg bg-slate-900/40 border border-slate-800/60 px-3 py-2 text-sm">
          <p className="text-xs text-slate-500">{kind}</p>
          <p className="font-semibold text-slate-200">{count}</p>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

type DrawerPanel = "nodes" | "edges" | "snapshot" | "timeline" | "controls" | null;
type TopMode = "explore" | "analyze" | "lineage";

export default function FigViewPage() {
  const { data: session } = useSession();
  const { toast } = useToast();

  const [graphId, setGraphId] = useState<string>("");
  const [state, setState] = useState<FigLoadState>({ status: "idle" });
  const [layoutMode, setLayoutMode] = useState<LayoutMode>("explore");
  const [locked, setLocked] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [topMode, setTopMode] = useState<TopMode>("explore");
  const [activeDrawer, setActiveDrawer] = useState<DrawerPanel>(null);
  const canvasRef = useRef<FigCanvasHandle>(null);
  const initializedRef = useRef(false);

  useEffect(() => {
    if (initializedRef.current) return;
    const sessionGraphId = (session as { graphId?: string } | null)?.graphId;
    if (sessionGraphId) { setGraphId(sessionGraphId); initializedRef.current = true; }
  }, [session]);

  const loadSurface = useCallback(async (targetGraphId: string) => {
    if (!targetGraphId) return;
    setState({ status: "loading" });
    try {
      const data = await fetchGraphSurface(targetGraphId, { timelineLimit: 20, includeTopology: true });
      clearStaleGraphState(targetGraphId);
      setState(classifyResponse(data));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load graph";
      setState({ status: "error", message });
      toast.error("Graph load failed", message);
    }
  }, [toast]);

  useEffect(() => { if (graphId) loadSurface(graphId); }, [graphId, loadSurface]);

  const toggleDrawer = (panel: DrawerPanel) => setActiveDrawer((prev) => prev === panel ? null : panel);
  const handleTopMode = (mode: TopMode) => {
    setTopMode(mode);
    if (mode === "explore") setActiveDrawer("nodes");
    if (mode === "analyze") setActiveDrawer("snapshot");
    if (mode === "lineage") setActiveDrawer("edges");
  };

  const graphLabel = graphId ? graphId.slice(0, 12) + (graphId.length > 12 ? "…" : "") : "—";
  const data = state.status === "loaded" || state.status === "degraded" ? state.data : null;

  return (
    <div className="relative h-full w-full overflow-hidden bg-transparent">

      {/* ===================================================================
          GRAPH CANVAS OR STATUS OVERLAY
      =================================================================== */}
      {data ? (
        <FigCanvas
          ref={canvasRef}
          data={data}
          layoutMode={layoutMode}
          topMode={topMode}
          locked={locked}
          selectedNodeId={selectedNodeId}
          onNodeSelect={setSelectedNodeId}
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center p-8 bg-slate-950">
          {state.status === "loading" && (
            <div className="flex flex-col items-center gap-4">
              <Spinner size="lg" />
              <p className="text-sm text-slate-500">Loading graph surface…</p>
            </div>
          )}
          {state.status === "error" && <ErrorState title="Failed to load graph" message={state.message} onRetry={() => loadSurface(graphId)} />}
          {state.status === "empty" && <EmptyState title="No nodes in this graph" description="Ingest data via Storage or Memory to populate the graph." />}
        </div>
      )}

      {/* ===================================================================
          TOP FRAME BAR
      =================================================================== */}
      <div className="absolute top-0 left-0 right-0 z-30 flex items-center justify-between gap-2 px-6 py-4 pointer-events-none">
        <div className="flex items-center gap-3 min-w-0 pointer-events-auto">
          <div className="flex flex-col leading-tight">
            <span className="text-[13px] font-semibold text-slate-100 tracking-wide flex items-center gap-1.5">
              FIG View
              {state.status === "degraded" && <span className="text-[9px] text-amber-400 border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 rounded-full">degraded</span>}
            </span>
            <span className="text-[10px] text-slate-500 font-mono">{graphLabel}</span>
          </div>
          <div className="h-6 w-px bg-slate-700/60" />
          <div className="flex items-center gap-1 rounded-lg border border-slate-700/50 bg-slate-950/70 p-0.5 backdrop-blur">
            {([{ id: "explore", label: "Explore", icon: <Network size={11} /> }, { id: "analyze", label: "Analyze", icon: <BarChart2 size={11} /> }, { id: "lineage", label: "Lineage", icon: <GitBranch size={11} /> }]).map((tab) => (
              <button
                key={tab.id}
                onClick={() => handleTopMode(tab.id as TopMode)}
                className={[ "flex items-center gap-1 px-3 py-1 rounded-md text-[11px] font-medium transition-all duration-150", topMode === tab.id ? "bg-cyan-500/20 text-cyan-200 border border-cyan-500/25" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60" ].join(" ")}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>
        </div>
        <button onClick={() => loadSurface(graphId)} className="flex h-7 w-7 items-center justify-center rounded-md border border-slate-700/60 bg-slate-950/60 text-slate-400 hover:text-cyan-300 hover:border-cyan-500/30 transition-all backdrop-blur"><RefreshCw size={13} /></button>
      </div>

      {/* ===================================================================
          RIGHT FLOATING ICON RAIL
      =================================================================== */}
      <div className="absolute right-3 top-1/2 -translate-y-1/2 z-30 flex flex-col gap-1.5">
        {[
          { id: "nodes", icon: <Zap size={14} />, label: "Nodes" },
          { id: "edges", icon: <GitFork size={14} />, label: "Edges" },
          { id: "snapshot", icon: <BarChart2 size={14} />, label: "Snapshot" },
          { id: "timeline", icon: <Hash size={14} />, label: "Timeline" },
          { id: "controls", icon: <Filter size={14} />, label: "Controls" },
        ].map((btn) => (
          <button key={btn.id} onClick={() => toggleDrawer(btn.id as DrawerPanel)} className={[ "flex h-8 w-8 items-center justify-center rounded-lg border transition-all duration-150 backdrop-blur-sm", activeDrawer === btn.id ? "border-cyan-400/50 bg-cyan-500/20 text-cyan-200 shadow-[0_0_10px_rgba(34,211,238,0.2)]" : "border-slate-700/60 bg-slate-950/70 text-slate-400 hover:border-cyan-400/30 hover:bg-slate-900/80 hover:text-slate-200" ].join(" ")}>
            {btn.icon}
          </button>
        ))}
        <div className="my-1 h-px w-8 bg-slate-700/50" />
        <button onClick={() => setLocked((v) => !v)} className={[ "flex h-8 w-8 items-center justify-center rounded-lg border transition-all duration-150 backdrop-blur-sm", locked ? "border-violet-400/40 bg-violet-500/15 text-violet-300" : "border-slate-700/60 bg-slate-950/70 text-slate-400 hover:text-violet-300" ].join(" ")}><Move size={14} /></button>
      </div>

      {/* ===================================================================
          BOTTOM CENTER — Stats pill bar
      =================================================================== */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-30"><StatsPill data={data} /></div>

      {/* ===================================================================
          BOTTOM RIGHT — Zoom controls
      =================================================================== */}
      <div className="absolute right-3 bottom-4 z-20 flex flex-col gap-1">
        {[
          { label: "Fit", action: () => canvasRef.current?.fitGraph(), icon: <Box size={12} /> },
          { label: "Zoom In", action: () => canvasRef.current?.zoomIn(), icon: <span className="text-[13px] font-bold leading-none">+</span> },
          { label: "Zoom Out", action: () => canvasRef.current?.zoomOut(), icon: <span className="text-[13px] font-bold leading-none">−</span> }
        ].map((btn) => (
          <button key={btn.label} onClick={btn.action} className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-700/60 bg-slate-950/70 text-slate-400 hover:text-cyan-200 hover:border-cyan-400/30 transition-all backdrop-blur-sm">{btn.icon}</button>
        ))}
      </div>

      {/* ===================================================================
          DRAWERS
      =================================================================== */}
      <FloatingDrawer open={activeDrawer === "nodes"} onClose={() => setActiveDrawer(null)} title={`Nodes (${data?.nodes?.length || 0})`}><NodePanel nodes={data?.nodes || []} /></FloatingDrawer>
      <FloatingDrawer open={activeDrawer === "edges"} onClose={() => setActiveDrawer(null)} title={`Edges (${data?.edges?.length || 0})`}><EdgePanel edges={data?.edges || []} /></FloatingDrawer>
      <FloatingDrawer open={activeDrawer === "snapshot"} onClose={() => setActiveDrawer(null)} title="Graph Snapshot">
        {data ? (
          <div className="space-y-3 text-xs">
            <div className="flex items-center gap-2 text-slate-400"><Hash className="h-3 w-3" /><span>Version {data.snapshot.graph_version}</span></div>
            <div className="font-mono text-slate-500 break-all">{data.snapshot.graph_hash}</div>
            <div className="text-slate-400">{formatTimestamp(data.snapshot.as_of)}</div>
          </div>
        ) : <p className="text-xs text-slate-500">No snapshot data</p>}
      </FloatingDrawer>
      <FloatingDrawer open={activeDrawer === "timeline"} onClose={() => setActiveDrawer(null)} title="Timeline">
        {data?.timeline?.events?.length ? (
          <div className="flex flex-col gap-1 text-xs">
            {data.timeline.events.map((ev) => (
              <div key={ev.seq} className="flex items-center justify-between rounded bg-slate-900/30 px-2 py-1.5"><span className="font-mono text-slate-500">#{ev.seq}</span><Badge size="sm" variant="outline">{ev.kind}</Badge></div>
            ))}
          </div>
        ) : <p className="text-xs text-slate-500">No events</p>}
      </FloatingDrawer>
      <FloatingDrawer open={activeDrawer === "controls"} onClose={() => setActiveDrawer(null)} title="Graph Controls">
        <FigControls layoutMode={layoutMode} onLayoutChange={setLayoutMode} locked={locked} onLockToggle={() => setLocked((v) => !v)} selectedNodeId={selectedNodeId} onFit={() => canvasRef.current?.fitGraph()} onCenter={() => selectedNodeId && canvasRef.current?.centerOnNode(selectedNodeId)} onResetCamera={() => canvasRef.current?.resetCamera()} onZoomIn={() => canvasRef.current?.zoomIn()} onZoomOut={() => canvasRef.current?.zoomOut()} timelineVisible={false} onTimelineToggle={() => {}} similarityMode={data?.controls?.similarity?.mode ?? "none"} />
      </FloatingDrawer>

    </div>
  );
}
