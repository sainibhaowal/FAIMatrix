"use client";

import {
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
  Search,
  Share2,
  Zap,
} from "lucide-react";
import { useSession } from "next-auth/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

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
import FigFloatingCard from "@/components/graph/FigFloatingCard";
import FigInspector from "@/components/graph/FigInspector";
import FigLegend from "@/components/graph/FigLegend";
import FigMetricsBar from "@/components/graph/FigMetricsBar";
import FigRelationPanel from "@/components/graph/FigRelationPanel";
import FigSearch from "@/components/graph/FigSearch";
import {
  fetchGraphExplain,
  fetchGraphLatestEvent,
  fetchGraphNeighborhood,
  fetchGraphSurface,
} from "@/lib/figViewApi";
import { buildAdjacency, buildNodeIndex } from "@/lib/figViewGraphTransform";
import type { LayoutMode, OverlayMode } from "@/lib/figViewLayout";
import {
  clearStaleGraphState,
  loadGraphViewState,
  nodeStateClass,
  persistGraphViewState,
  safeNodeTitle,
} from "@/lib/figViewSafety";
import {
  createInitialTimelineSyncState,
  deriveTimelineSyncStatus,
  mergeTimelineResponse,
  nextTimelineCursor,
  shouldRebaseTimeline,
  type FigTimelineSyncState,
} from "@/lib/figViewTimelineSync";
import type {
  FigExplainResponse,
  FigLoadState,
  FigNeighborhoodExpansion,
  FigNode,
  FigSurfaceResponse,
} from "@/types/figView";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function classifyResponse(data: FigSurfaceResponse): FigLoadState {
  const warnings: string[] = [];
  if (data.truncated) {
    warnings.push(
      `Truncated: ${data.truncation_reason || "payload cap reached"}`,
    );
  }
  if (!data.snapshot.consistent_read) {
    warnings.push(
      "Snapshot assembled from multiple reads (eventual consistency)",
    );
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
    <div className="absolute right-0 sm:right-14 top-0 sm:top-14 bottom-0 sm:bottom-4 z-30 w-full sm:w-[360px] max-w-[90vw] sm:max-w-none p-4 sm:p-0">
      <div className="relative h-full overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-950/95 sm:bg-slate-950/85 shadow-[0_10px_40px_rgba(0,0,0,0.55)] backdrop-blur-xl sm:backdrop-blur-md">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800/60">
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-widest">
            {title}
          </span>
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
    {
      icon: <Network size={12} className="text-cyan-400" />,
      label: "Nodes",
      value: nodeCount,
      color: "text-cyan-200",
    },
    {
      icon: <Share2 size={12} className="text-violet-400" />,
      label: "Edges",
      value: edgeCount,
      color: "text-violet-200",
    },
    {
      icon: <Layers size={12} className="text-amber-400" />,
      label: "Opposition",
      value: oppCount,
      color: "text-amber-200",
    },
    {
      icon: <GitBranch size={12} className="text-emerald-400" />,
      label: "Inheritance",
      value: inhCount,
      color: "text-emerald-200",
    },
  ];

  return (
    <div className="flex flex-wrap items-center gap-0 rounded-xl border border-slate-700/60 bg-slate-950/80 backdrop-blur-md shadow-[0_4px_24px_rgba(0,0,0,0.4)] overflow-hidden divide-x divide-slate-700/40">
      {stats.map((s) => (
        <div
          key={s.label}
          className="flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2"
        >
          {s.icon}
          <span
            className={`font-mono text-[11px] sm:text-[13px] font-semibold ${s.color}`}
          >
            {s.value > 0 ? s.value : s.value === 0 ? "0" : "—"}
          </span>
          <span className="text-[8px] sm:text-[9px] uppercase tracking-widest text-slate-500">
            {s.label}
          </span>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Node & Edge Panels (same as before)
// ---------------------------------------------------------------------------

function NodePanel({ nodes }: { nodes: FigNode[] }) {
  if (nodes.length === 0)
    return (
      <p className="text-xs text-slate-500 text-center py-4">No nodes found</p>
    );
  return (
    <div className="flex flex-col gap-1.5">
      {nodes.map((node) => {
        const title = safeNodeTitle(node);
        const stateClass = nodeStateClass(node);
        const color = STATE_COLORS[stateClass] ?? STATE_COLORS.unknown;
        return (
          <div
            key={node.node_id}
            className="flex items-center justify-between rounded-lg bg-slate-900/40 border border-slate-800/60 px-3 py-2 text-sm"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span
                className={`inline-block h-2 w-2 rounded-full ${stateClass === "active" ? "bg-emerald-400" : stateClass === "cold" ? "bg-slate-500" : "bg-slate-600"}`}
              />
              <span
                className="truncate font-medium text-slate-200"
                title={title}
              >
                {title}
              </span>
              <Badge size="sm" variant="outline">
                {node.kind}
              </Badge>
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
  if (edges.length === 0)
    return (
      <p className="text-xs text-slate-500 text-center py-4">No edges found</p>
    );
  const kindCounts = edges.reduce<Record<string, number>>((acc, e) => {
    acc[e.kind] = (acc[e.kind] || 0) + 1;
    return acc;
  }, {});
  return (
    <div className="grid grid-cols-2 gap-2">
      {Object.entries(kindCounts).map(([kind, count]) => (
        <div
          key={kind}
          className="rounded-lg bg-slate-900/40 border border-slate-800/60 px-3 py-2 text-sm"
        >
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

type DrawerPanel =
  | "nodes"
  | "edges"
  | "snapshot"
  | "timeline"
  | "controls"
  | "inspector"
  | "relation"
  | "legend"
  | null;
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
  const [timelineSync, setTimelineSync] = useState<FigTimelineSyncState>(() =>
    createInitialTimelineSyncState(false),
  );
  const canvasRef = useRef<FigCanvasHandle>(null);
  const initializedRef = useRef(false);
  const graphDataRef = useRef<FigSurfaceResponse | null>(null);
  const graphIdRef = useRef<string>("");
  const timelineCursorRef = useRef<number>(0);
  const timelinePollInFlightRef = useRef(false);
  const timelinePollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const pollTimelineRef = useRef<() => void>(() => {});
  const timelineLiveEnabledRef = useRef(true);
  const timelineVisibleRef = useRef(false);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // --- Phase 6-7 state ---
  // Pinned node for relation/explain comparisons
  const [pinnedNodeId, setPinnedNodeId] = useState<string | null>(null);
  // Hover card
  const [hoverNode, setHoverNode] = useState<FigNode | null>(null);
  const [hoverPos, setHoverPos] = useState({ x: 0, y: 0 });
  // Explain result
  const [explainResult, setExplainResult] = useState<FigExplainResponse | null>(
    null,
  );
  const [explainLoading, setExplainLoading] = useState(false);
  // Search overlay
  const [searchOpen, setSearchOpen] = useState(false);
  // Client-side kind filters (never mutate backend data)
  const [hiddenNodeKinds, setHiddenNodeKinds] = useState<Set<string>>(
    new Set(),
  );
  const [hiddenEdgeKinds, setHiddenEdgeKinds] = useState<Set<string>>(
    new Set(),
  );
  const [timelineLiveEnabled, setTimelineLiveEnabled] = useState(true);
  const [timelineLastSyncedAt, setTimelineLastSyncedAt] = useState<
    string | null
  >(null);
  const [timelineError, setTimelineError] = useState<string | null>(null);
  const [neighborhoodExpansion, setNeighborhoodExpansion] =
    useState<FigNeighborhoodExpansion | null>(null);
  const [neighborhoodLoading, setNeighborhoodLoading] = useState(false);
  const [overlayMode, setOverlayMode] = useState<OverlayMode>("none");
  // Timeline step mode — null = scrolling list, number = step cursor
  const [timelineStepIdx, setTimelineStepIdx] = useState<number | null>(null);

  useEffect(() => {
    if (initializedRef.current) return;
    const sessionGraphId = (session as { graphId?: string } | null)?.graphId;
    if (sessionGraphId) {
      setGraphId(sessionGraphId);
      initializedRef.current = true;
    }
  }, [session]);

  useEffect(() => {
    graphIdRef.current = graphId;
  }, [graphId]);

  useEffect(() => {
    timelineLiveEnabledRef.current = timelineLiveEnabled;
  }, [timelineLiveEnabled]);

  useEffect(() => {
    timelineVisibleRef.current = activeDrawer === "timeline";
  }, [activeDrawer]);

  // Derived graph structures (stable between renders)
  const graphData =
    state.status === "loaded" || state.status === "degraded"
      ? state.data
      : null;
  const nodeIndex = useMemo(
    () => buildNodeIndex(graphData?.nodes ?? []),
    [graphData?.nodes],
  );
  const adj = useMemo(
    () => buildAdjacency(graphData?.edges ?? []),
    [graphData?.edges],
  );
  const nodeKinds = useMemo(
    () =>
      Array.from(new Set((graphData?.nodes ?? []).map((n) => n.kind))).sort(),
    [graphData?.nodes],
  );
  const edgeKinds = useMemo(
    () =>
      Array.from(new Set((graphData?.edges ?? []).map((e) => e.kind))).sort(),
    [graphData?.edges],
  );

  // Filtered view (respects hidden kinds for metrics bar dual view)
  const filteredNodes = useMemo(
    () => (graphData?.nodes ?? []).filter((n) => !hiddenNodeKinds.has(n.kind)),
    [graphData?.nodes, hiddenNodeKinds],
  );
  const filteredEdges = useMemo(
    () => (graphData?.edges ?? []).filter((e) => !hiddenEdgeKinds.has(e.kind)),
    [graphData?.edges, hiddenEdgeKinds],
  );

  // Explain path for canvas visualization — derived from explainResult.
  // Only the first path is visualized; amber-400 nodes/edges + particles.
  const explainPath = useMemo(() => {
    if (!explainResult?.path_found) return null;
    const firstPath = explainResult.paths[0];
    if (!firstPath) return null;
    return {
      nodeIdSet: new Set(firstPath.node_ids),
      edgeIdSet: new Set(firstPath.edges.map((e) => e.edge_id)),
    };
  }, [explainResult]);

  // Derive historyTs from current timeline step for graph-at-time visualization.
  // Null when not in step mode; canvas filters nodes/edges to created_at <= ts.
  const historyTs = useMemo(() => {
    if (timelineStepIdx === null) return null;
    const events = graphData?.timeline?.events ?? [];
    return events[timelineStepIdx]?.ts ?? null;
  }, [timelineStepIdx, graphData?.timeline?.events]);

  useEffect(() => {
    graphDataRef.current = graphData;
  }, [graphData]);

  // --- Phase 6-7 handlers ---

  const handlePinToggle = useCallback((nodeId: string) => {
    setPinnedNodeId((prev) => (prev === nodeId ? null : nodeId));
  }, []);

  const handleNavigateToNode = useCallback((nodeId: string) => {
    setSelectedNodeId(nodeId);
    canvasRef.current?.centerOnNode(nodeId);
  }, []);

  const handleRequestExplain = useCallback(
    async (fromNodeId: string, toNodeId: string) => {
      if (!graphId) return;
      setExplainLoading(true);
      setExplainResult(null);
      try {
        const result = await fetchGraphExplain(graphId, fromNodeId, toNodeId);
        setExplainResult(result);
      } catch (err) {
        toast.error(
          "Explain failed",
          err instanceof Error ? err.message : "Unknown error",
        );
      } finally {
        setExplainLoading(false);
      }
    },
    [graphId, toast],
  );

  const handleNodeHover = useCallback(
    (node: FigNode | null, x: number, y: number) => {
      setHoverNode(node);
      if (node) setHoverPos({ x, y });
    },
    [],
  );

  // "/" key opens search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "/" && !e.ctrlKey && !e.metaKey) {
        const active = document.activeElement;
        if (
          active &&
          (active.tagName === "INPUT" || active.tagName === "TEXTAREA")
        )
          return;
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Applies a persisted view-state payload back to component state.
  // All useState setters are stable references — empty dep array is correct.
  const applyPersistedViewState = useCallback(
    (payload: Record<string, unknown>) => {
      if (typeof payload.layoutMode === "string")
        setLayoutMode(payload.layoutMode as LayoutMode);
      if (typeof payload.topMode === "string")
        setTopMode(payload.topMode as TopMode);
      if (typeof payload.locked === "boolean") setLocked(payload.locked);
      if (Array.isArray(payload.hiddenNodeKinds))
        setHiddenNodeKinds(new Set(payload.hiddenNodeKinds as string[]));
      if (Array.isArray(payload.hiddenEdgeKinds))
        setHiddenEdgeKinds(new Set(payload.hiddenEdgeKinds as string[]));
      if (
        typeof payload.selectedNodeId === "string" ||
        payload.selectedNodeId === null
      )
        setSelectedNodeId(payload.selectedNodeId as string | null);
      if (
        typeof payload.activeDrawer === "string" ||
        payload.activeDrawer === null
      )
        setActiveDrawer(payload.activeDrawer as DrawerPanel | null);
      if (typeof payload.timelineLiveEnabled === "boolean")
        setTimelineLiveEnabled(payload.timelineLiveEnabled);
      if (typeof payload.overlayMode === "string")
        setOverlayMode(payload.overlayMode as OverlayMode);
    },
    [],
  );

  const loadSurface = useCallback(
    async (targetGraphId: string) => {
      if (!targetGraphId) return;
      setState({ status: "loading" });
      setTimelineError(null);
      setTimelineLastSyncedAt(null);
      try {
        const data = await fetchGraphSurface(targetGraphId, {
          timelineLimit: 20,
          includeTopology: true,
        });
        clearStaleGraphState(targetGraphId);
        graphDataRef.current = data;
        const nextCursor =
          data.timeline?.next_seq ?? data.timeline?.events?.at(-1)?.seq ?? 0;
        timelineCursorRef.current = nextCursor;
        setTimelineSync((prev) => ({
          ...prev,
          enabled: timelineLiveEnabledRef.current,
          status:
            data.timeline &&
            timelineLiveEnabledRef.current &&
            timelineVisibleRef.current
              ? "live"
              : "idle",
          lastAppliedSeq: nextCursor,
          lastSnapshotHash: data.snapshot.graph_hash,
          lastSnapshotVersion: data.snapshot.graph_version,
          lastSyncedAt: new Date().toISOString(),
          lastError: null,
          lastEventKind: data.timeline?.events?.at(-1)?.kind ?? null,
        }));
        setTimelineLastSyncedAt(new Date().toISOString());
        setState(classifyResponse(data));
        // Restore persisted view state only when graph version matches exactly.
        const saved = loadGraphViewState(
          targetGraphId,
          data.snapshot.graph_version,
        );
        if (saved) applyPersistedViewState(saved);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to load graph";
        setState({ status: "error", message });
        setTimelineSync((prev) => ({
          ...prev,
          status: "disconnected",
          lastError: message,
        }));
        setTimelineError(message);
        toast.error("Graph load failed", message);
      }
    },
    [toast, applyPersistedViewState],
  );

  useEffect(() => {
    if (graphId) loadSurface(graphId);
  }, [graphId, loadSurface]);

  const handleExpandNeighborhood = useCallback(
    async (nodeId: string, depth: number) => {
      const currentData = graphDataRef.current;
      if (!graphId || !currentData) return;
      setNeighborhoodLoading(true);
      try {
        const result = await fetchGraphNeighborhood(graphId, nodeId, { depth });
        const existingNodeIds = new Set(
          currentData.nodes.map((n) => n.node_id),
        );
        const existingEdgeIds = new Set(
          currentData.edges.map((e) => e.edge_id),
        );
        const newNodes = result.nodes.filter(
          (n) => !existingNodeIds.has(n.node_id),
        );
        const newEdges = result.edges.filter(
          (e) => !existingEdgeIds.has(e.edge_id),
        );
        const merged: FigSurfaceResponse = {
          ...currentData,
          nodes: [...currentData.nodes, ...newNodes],
          edges: [...currentData.edges, ...newEdges],
        };
        graphDataRef.current = merged;
        setState(classifyResponse(merged));
        setNeighborhoodExpansion({
          seedNodeId: nodeId,
          addedNodeCount: newNodes.length,
          addedEdgeCount: newEdges.length,
        });
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Neighborhood fetch failed";
        toast.error("Expand failed", message);
      } finally {
        setNeighborhoodLoading(false);
      }
    },
    [graphId, toast],
  );

  const handleClearNeighborhood = useCallback(() => {
    setNeighborhoodExpansion(null);
    void loadSurface(graphId);
  }, [graphId, loadSurface]);

  // Debounced view-state persistence: saves layout, filter, and selection
  // preferences to localStorage whenever they change. Restores on next load
  // of the same graph version. Debounced to 500 ms to avoid excess writes.
  useEffect(() => {
    const currentData = graphDataRef.current;
    if (!graphId || !currentData) return;
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      persistGraphViewState(graphId, currentData.snapshot.graph_version, {
        layoutMode,
        topMode,
        locked,
        hiddenNodeKinds: Array.from(hiddenNodeKinds),
        hiddenEdgeKinds: Array.from(hiddenEdgeKinds),
        selectedNodeId,
        activeDrawer,
        timelineLiveEnabled,
        overlayMode,
      });
    }, 500);
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, [
    graphId,
    layoutMode,
    topMode,
    locked,
    hiddenNodeKinds,
    hiddenEdgeKinds,
    selectedNodeId,
    activeDrawer,
    timelineLiveEnabled,
    overlayMode,
  ]);

  const toggleDrawer = (panel: DrawerPanel) =>
    setActiveDrawer((prev) => (prev === panel ? null : panel));
  const handleTopMode = (mode: TopMode) => {
    setTopMode(mode);
    setLayoutMode(mode); // Sync layout mode with top mode
    if (mode === "explore") setActiveDrawer("nodes");
    if (mode === "analyze") setActiveDrawer("snapshot");
    if (mode === "lineage") setActiveDrawer("edges");
  };

  // Auto-open inspector when a node is selected (Phase 6)
  const handleNodeSelect = useCallback((nodeId: string | null) => {
    setSelectedNodeId(nodeId);
    if (nodeId) {
      setActiveDrawer("inspector");
    }
  }, []);

  const timelineVisible = activeDrawer === "timeline";

  const stopTimelinePoll = useCallback(() => {
    if (timelinePollTimerRef.current) {
      clearTimeout(timelinePollTimerRef.current);
      timelinePollTimerRef.current = null;
    }
    timelinePollInFlightRef.current = false;
  }, []);

  const scheduleTimelinePoll = useCallback((delayMs: number) => {
    if (timelinePollTimerRef.current) {
      clearTimeout(timelinePollTimerRef.current);
    }
    timelinePollTimerRef.current = setTimeout(() => {
      timelinePollTimerRef.current = null;
      pollTimelineRef.current();
    }, delayMs);
  }, []);

  const pollTimeline = useCallback(async () => {
    const currentGraphId = graphIdRef.current;
    const liveEnabled = timelineLiveEnabledRef.current;
    const visible = timelineVisibleRef.current;

    if (!currentGraphId || !liveEnabled || !visible) {
      setTimelineSync((prev) => ({
        ...prev,
        enabled: liveEnabled,
        status: liveEnabled ? prev.status : "idle",
      }));
      return;
    }
    if (timelinePollInFlightRef.current) return;
    timelinePollInFlightRef.current = true;

    try {
      const latest = await fetchGraphLatestEvent(currentGraphId);
      const currentCursor = timelineCursorRef.current;
      const currentSnapshot = graphDataRef.current;
      const latestSeq = latest.last_seq ?? 0;

      if (latestSeq <= currentCursor) {
        setTimelineSync((prev) => ({
          ...prev,
          enabled: true,
          status: deriveTimelineSyncStatus(
            true,
            !!currentSnapshot,
            false,
            false,
          ),
          lastAppliedSeq: currentCursor,
          lastSnapshotHash:
            currentSnapshot?.snapshot.graph_hash ?? prev.lastSnapshotHash,
          lastSnapshotVersion:
            currentSnapshot?.snapshot.graph_version ?? prev.lastSnapshotVersion,
          lastSyncedAt: new Date().toISOString(),
          lastError: null,
          lastEventKind: latest.last_kind ?? prev.lastEventKind,
        }));
        setTimelineLastSyncedAt(new Date().toISOString());
        setTimelineError(null);
        scheduleTimelinePoll(2000);
        return;
      }

      setTimelineSync((prev) => ({
        ...prev,
        enabled: true,
        status: "catching_up",
        lastEventKind: latest.last_kind ?? prev.lastEventKind,
      }));

      let cursor = currentCursor;
      let nextSurface = currentSnapshot;
      let safety = 0;
      let sawRebase = false;

      while (!sawRebase && cursor < latestSeq && safety < 4) {
        const page = await fetchGraphSurface(currentGraphId, {
          timelineLimit: 50,
          afterSeq: cursor,
          includeTopology: true,
        });

        if (
          nextSurface &&
          shouldRebaseTimeline(
            nextSurface.snapshot.graph_hash,
            page.snapshot.graph_hash,
            nextSurface.snapshot.graph_version,
            page.snapshot.graph_version,
          )
        ) {
          sawRebase = true;
        }

        nextSurface = nextSurface
          ? mergeTimelineResponse(nextSurface, page, cursor)
          : page;

        cursor = nextTimelineCursor(
          cursor,
          latestSeq,
          nextSurface.timeline?.next_seq,
        );
        safety += 1;

        if (!page.timeline?.has_more) break;
      }

      if (nextSurface) {
        graphDataRef.current = nextSurface;
        timelineCursorRef.current = Math.max(
          cursor,
          nextSurface.timeline?.next_seq ?? 0,
          latestSeq,
        );
        setTimelineLastSyncedAt(new Date().toISOString());
        setTimelineError(null);
        setState(classifyResponse(nextSurface));
        setTimelineSync((prev) => ({
          ...prev,
          enabled: true,
          status: sawRebase ? "stale" : "live",
          lastAppliedSeq: timelineCursorRef.current,
          lastSnapshotHash: nextSurface.snapshot.graph_hash,
          lastSnapshotVersion: nextSurface.snapshot.graph_version,
          lastSyncedAt: new Date().toISOString(),
          lastError: null,
          lastEventKind: latest.last_kind ?? prev.lastEventKind,
        }));
      }

      scheduleTimelinePoll(2000);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Timeline sync failed";
      setTimelineSync((prev) => ({
        ...prev,
        enabled: liveEnabled,
        status: "disconnected",
        lastError: message,
      }));
      setTimelineError(message);
      scheduleTimelinePoll(4000);
    } finally {
      timelinePollInFlightRef.current = false;
    }
  }, [scheduleTimelinePoll]);

  useEffect(() => {
    pollTimelineRef.current = () => {
      void pollTimeline();
    };
  }, [pollTimeline]);

  useEffect(() => {
    if (!timelineVisible) {
      stopTimelinePoll();
      return;
    }
    if (!timelineLiveEnabled) {
      setTimelineSync((prev) => ({ ...prev, enabled: false, status: "idle" }));
      stopTimelinePoll();
      return;
    }
    setTimelineSync((prev) => ({
      ...prev,
      enabled: true,
      status: prev.status === "disconnected" ? "idle" : prev.status,
    }));
    void pollTimeline();
    return () => stopTimelinePoll();
  }, [timelineVisible, timelineLiveEnabled, pollTimeline, stopTimelinePoll]);

  useEffect(() => () => stopTimelinePoll(), [stopTimelinePoll]);

  const handleTimelineToggle = useCallback(() => {
    setActiveDrawer((prev) => (prev === "timeline" ? null : "timeline"));
  }, []);

  const handleLiveSyncToggle = useCallback(() => {
    setTimelineLiveEnabled((prev) => {
      const next = !prev;
      setTimelineSync((sync) => ({
        ...sync,
        enabled: next,
        status: next ? sync.status : "idle",
        lastError: next ? sync.lastError : null,
      }));
      if (!next) {
        stopTimelinePoll();
      } else if (activeDrawer === "timeline") {
        void pollTimeline();
      }
      return next;
    });
  }, [activeDrawer, pollTimeline, stopTimelinePoll]);

  const graphLabel = graphId
    ? graphId.slice(0, 12) + (graphId.length > 12 ? "…" : "")
    : "—";
  const data = graphData;

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
          hiddenNodeKinds={hiddenNodeKinds}
          hiddenEdgeKinds={hiddenEdgeKinds}
          overlayMode={overlayMode}
          explainPath={explainPath}
          historyTs={historyTs}
          onNodeSelect={handleNodeSelect}
          onNodeHover={handleNodeHover}
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center p-8 bg-slate-950">
          {state.status === "loading" && (
            <div className="flex flex-col items-center gap-4">
              <Spinner size="lg" />
              <p className="text-sm text-slate-500">Loading graph surface…</p>
            </div>
          )}
          {state.status === "error" && (
            <ErrorState
              title="Failed to load graph"
              message={state.message}
              onRetry={() => loadSurface(graphId)}
            />
          )}
          {state.status === "empty" && (
            <EmptyState
              title="No nodes in this graph"
              description="Ingest data via Storage or Memory to populate the graph."
            />
          )}
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
              {state.status === "degraded" && (
                <span className="text-[9px] text-amber-400 border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 rounded-full">
                  degraded
                </span>
              )}
            </span>
            <span className="text-[10px] text-slate-500 font-mono">
              {graphLabel}
            </span>
          </div>
          <div className="h-6 w-px bg-slate-700/60" />
          {neighborhoodExpansion && (
            <button
              onClick={handleClearNeighborhood}
              title="Neighborhood expanded — click to reset to surface snapshot"
              className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[10px] text-emerald-300 hover:bg-emerald-500/20 transition-colors"
            >
              <span>+{neighborhoodExpansion.addedNodeCount}n expanded</span>
              <span className="text-slate-500 text-[11px]">×</span>
            </button>
          )}
          <div className="flex items-center gap-1 rounded-lg border border-slate-700/50 bg-slate-950/70 p-0.5 backdrop-blur">
            {[
              { id: "explore", label: "Explore", icon: <Network size={11} /> },
              {
                id: "analyze",
                label: "Analyze",
                icon: <BarChart2 size={11} />,
              },
              {
                id: "lineage",
                label: "Lineage",
                icon: <GitBranch size={11} />,
              },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => handleTopMode(tab.id as TopMode)}
                className={[
                  "flex items-center gap-1 px-3 py-1 rounded-md text-[11px] font-medium transition-all duration-150",
                  topMode === tab.id
                    ? "bg-cyan-500/20 text-cyan-200 border border-cyan-500/25"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60",
                ].join(" ")}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-1 pointer-events-auto">
          <Badge
            size="sm"
            variant={
              timelineSync.status === "disconnected" ||
              timelineSync.status === "error"
                ? "error"
                : timelineSync.status === "catching_up"
                  ? "warning"
                  : "outline"
            }
          >
            {timelineSync.status}
          </Badge>
          <button
            onClick={() => setSearchOpen(true)}
            title="Search nodes (press /)"
            className="flex h-7 items-center gap-1.5 rounded-md border border-slate-700/60 bg-slate-950/60 px-2.5 text-slate-400 hover:text-cyan-300 hover:border-cyan-500/30 transition-all backdrop-blur text-[10px]"
          >
            <Search size={11} />
            <span className="hidden sm:inline">Search</span>
            <span className="text-[9px] text-slate-600 border border-slate-700/60 rounded px-1">
              /
            </span>
          </button>
          <button
            onClick={() => loadSurface(graphId)}
            className="flex h-7 w-7 items-center justify-center rounded-md border border-slate-700/60 bg-slate-950/60 text-slate-400 hover:text-cyan-300 hover:border-cyan-500/30 transition-all backdrop-blur"
          >
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {/* ===================================================================
          RIGHT FLOATING ICON RAIL
      =================================================================== */}
      <div className="absolute right-3 top-1/2 -translate-y-1/2 z-30 flex flex-col gap-1.5">
        {[
          {
            id: "inspector",
            icon: <Zap size={14} />,
            label: "Inspector",
            dot: !!selectedNodeId,
          },
          { id: "nodes", icon: <Network size={14} />, label: "Nodes" },
          { id: "edges", icon: <GitFork size={14} />, label: "Edges" },
          { id: "relation", icon: <Share2 size={14} />, label: "Relation" },
          { id: "legend", icon: <Layers size={14} />, label: "Legend" },
          { id: "snapshot", icon: <BarChart2 size={14} />, label: "Snapshot" },
          { id: "timeline", icon: <Hash size={14} />, label: "Timeline" },
          { id: "controls", icon: <Filter size={14} />, label: "Controls" },
        ].map((btn) => (
          <button
            key={btn.id}
            onClick={() => toggleDrawer(btn.id as DrawerPanel)}
            title={btn.label}
            className={[
              "relative flex h-8 w-8 items-center justify-center rounded-lg border transition-all duration-150 backdrop-blur-sm",
              activeDrawer === btn.id
                ? "border-cyan-400/50 bg-cyan-500/20 text-cyan-200 shadow-[0_0_10px_rgba(34,211,238,0.2)]"
                : "border-slate-700/60 bg-slate-950/70 text-slate-400 hover:border-cyan-400/30 hover:bg-slate-900/80 hover:text-slate-200",
            ].join(" ")}
          >
            {btn.icon}
            {/* Activity dot — shows when inspector has a selected node */}
            {"dot" in btn && btn.dot && activeDrawer !== btn.id && (
              <span className="absolute top-0.5 right-0.5 h-1.5 w-1.5 rounded-full bg-cyan-400" />
            )}
          </button>
        ))}
        <div className="my-1 h-px w-8 bg-slate-700/50" />
        <button
          onClick={() => setLocked((v) => !v)}
          className={[
            "flex h-8 w-8 items-center justify-center rounded-lg border transition-all duration-150 backdrop-blur-sm",
            locked
              ? "border-violet-400/40 bg-violet-500/15 text-violet-300"
              : "border-slate-700/60 bg-slate-950/70 text-slate-400 hover:text-violet-300",
          ].join(" ")}
        >
          <Move size={14} />
        </button>
      </div>

      {/* ===================================================================
          HOVER CARD (portal — renders over canvas)
      =================================================================== */}
      <FigFloatingCard node={hoverNode} x={hoverPos.x} y={hoverPos.y} />

      {/* ===================================================================
          SEARCH OVERLAY
      =================================================================== */}
      {searchOpen && data && (
        <FigSearch
          nodes={data.nodes}
          nodeIndex={nodeIndex}
          onSelectNode={handleNavigateToNode}
          onClose={() => setSearchOpen(false)}
        />
      )}

      {/* ===================================================================
          BOTTOM CENTER — Metrics bar (replaces legacy stats pill)
      =================================================================== */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-30">
        <FigMetricsBar
          topology={data?.topology ?? null}
          snapshot={data?.snapshot ?? null}
          nodeCount={data?.nodes?.length ?? 0}
          edgeCount={data?.edges?.length ?? 0}
          nodes={data?.nodes}
          edges={data?.edges}
          filteredNodeCount={filteredNodes.length}
          filteredEdgeCount={filteredEdges.length}
          filteredNodes={filteredNodes}
          filteredEdges={filteredEdges}
        />
      </div>

      {/* ===================================================================
          BOTTOM RIGHT — Zoom controls (improved styling & feedback)
      =================================================================== */}
      <div className="absolute right-3 bottom-4 z-20 flex flex-col gap-1.5 pointer-events-auto">
        {[
          {
            label: "Fit Graph",
            action: () => canvasRef.current?.fitGraph(),
            icon: <Box size={13} className="text-amber-400" />,
          },
          {
            label: "Zoom In",
            action: () => canvasRef.current?.zoomIn(),
            icon: (
              <span className="text-[16px] font-bold leading-none text-emerald-400">
                +
              </span>
            ),
          },
          {
            label: "Zoom Out",
            action: () => canvasRef.current?.zoomOut(),
            icon: (
              <span className="text-[16px] font-bold leading-none text-blue-400">
                −
              </span>
            ),
          },
        ].map((btn) => (
          <button
            key={btn.label}
            onClick={btn.action}
            title={btn.label}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-700/60 bg-slate-950/80 text-slate-400 hover:text-slate-100 hover:border-cyan-400/50 hover:bg-slate-900/90 transition-all duration-150 backdrop-blur-sm shadow-lg hover:shadow-[0_0_12px_rgba(34,211,238,0.2)]"
          >
            {btn.icon}
          </button>
        ))}
      </div>

      {/* ===================================================================
          DRAWERS
      =================================================================== */}
      {/* Inspector — auto-opens on node select */}
      <FloatingDrawer
        open={activeDrawer === "inspector"}
        onClose={() => setActiveDrawer(null)}
        title={
          selectedNodeId ? `Node — ${selectedNodeId.slice(0, 8)}…` : "Inspector"
        }
      >
        {selectedNodeId && nodeIndex.get(selectedNodeId) && data ? (
          <FigInspector
            node={nodeIndex.get(selectedNodeId)!}
            graphId={graphId}
            allEdges={data.edges}
            nodeIndex={nodeIndex}
            adj={adj}
            pinnedNodeId={pinnedNodeId}
            onPinToggle={handlePinToggle}
            onNavigateToNode={handleNavigateToNode}
            onRequestExplain={handleRequestExplain}
            explainResult={explainResult}
            explainLoading={explainLoading}
            onExpandNeighborhood={handleExpandNeighborhood}
            neighborhoodLoading={neighborhoodLoading}
            neighborhoodExpansion={neighborhoodExpansion}
          />
        ) : (
          <p className="text-xs text-slate-500 text-center py-6">
            Click a node in the graph to inspect it.
          </p>
        )}
      </FloatingDrawer>

      {/* Relation Explorer */}
      <FloatingDrawer
        open={activeDrawer === "relation"}
        onClose={() => setActiveDrawer(null)}
        title="Explore Relation"
      >
        {data ? (
          <FigRelationPanel
            graphId={graphId}
            nodes={data.nodes}
            nodeIndex={nodeIndex}
            initialFromId={pinnedNodeId}
            initialToId={selectedNodeId}
            onNavigateToNode={handleNavigateToNode}
            onRequestExplain={handleRequestExplain}
            explainResult={explainResult}
            explainLoading={explainLoading}
          />
        ) : (
          <p className="text-xs text-slate-500 text-center py-6">
            No graph data loaded.
          </p>
        )}
      </FloatingDrawer>

      {/* Legend + Filters */}
      <FloatingDrawer
        open={activeDrawer === "legend"}
        onClose={() => setActiveDrawer(null)}
        title="Legend & Filters"
      >
        <FigLegend
          nodeKinds={nodeKinds}
          edgeKinds={edgeKinds}
          hiddenNodeKinds={hiddenNodeKinds}
          hiddenEdgeKinds={hiddenEdgeKinds}
          onToggleNodeKind={(kind) =>
            setHiddenNodeKinds((prev) => {
              const next = new Set(prev);
              next.has(kind) ? next.delete(kind) : next.add(kind);
              return next;
            })
          }
          onToggleEdgeKind={(kind) =>
            setHiddenEdgeKinds((prev) => {
              const next = new Set(prev);
              next.has(kind) ? next.delete(kind) : next.add(kind);
              return next;
            })
          }
        />
      </FloatingDrawer>

      <FloatingDrawer
        open={activeDrawer === "nodes"}
        onClose={() => setActiveDrawer(null)}
        title={`Nodes (${data?.nodes?.length || 0})`}
      >
        <NodePanel nodes={data?.nodes || []} />
      </FloatingDrawer>
      <FloatingDrawer
        open={activeDrawer === "edges"}
        onClose={() => setActiveDrawer(null)}
        title={`Edges (${data?.edges?.length || 0})`}
      >
        <EdgePanel edges={data?.edges || []} />
      </FloatingDrawer>
      <FloatingDrawer
        open={activeDrawer === "snapshot"}
        onClose={() => setActiveDrawer(null)}
        title="Graph Snapshot"
      >
        {data ? (
          <div className="space-y-3 text-xs">
            <div className="flex items-center gap-2 text-slate-400">
              <Hash className="h-3 w-3" />
              <span>Version {data.snapshot.graph_version}</span>
            </div>
            <div className="font-mono text-slate-500 break-all">
              {data.snapshot.graph_hash}
            </div>
            <div className="text-slate-400">
              {formatTimestamp(data.snapshot.as_of)}
            </div>
          </div>
        ) : (
          <p className="text-xs text-slate-500">No snapshot data</p>
        )}
      </FloatingDrawer>
      <FloatingDrawer
        open={activeDrawer === "timeline"}
        onClose={() => setActiveDrawer(null)}
        title="Timeline"
      >
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="flex flex-col">
            <span className="text-[10px] uppercase tracking-widest text-slate-500">
              Live timeline
            </span>
            <span className="text-[10px] text-slate-400 font-mono">
              {timelineSync.lastSyncedAt
                ? `synced ${formatTimestamp(timelineSync.lastSyncedAt)}`
                : "waiting for event journal"}
            </span>
          </div>
          <button
            onClick={handleLiveSyncToggle}
            className={`rounded-md border px-2 py-1 text-[10px] font-medium transition-colors ${
              timelineLiveEnabled
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
                : "border-slate-700/60 bg-slate-900/50 text-slate-400"
            }`}
          >
            {timelineLiveEnabled ? "Pause live" : "Resume live"}
          </button>
        </div>
        {timelineError && (
          <div className="mb-3 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-[10px] text-red-200">
            {timelineError}
          </div>
        )}
        {data?.timeline?.events?.length ? (
          (() => {
            const events = data.timeline!.events;
            const total = events.length;
            const stepActive = timelineStepIdx !== null;
            const clampedStep = stepActive
              ? Math.min(timelineStepIdx!, total - 1)
              : null;
            const currentEv = clampedStep !== null ? events[clampedStep] : null;
            return (
              <div className="space-y-2 text-xs">
                {/* Step mode controls */}
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => {
                      setTimelineStepIdx(stepActive ? null : 0);
                    }}
                    className={`rounded px-2 py-0.5 text-[10px] border transition-colors ${stepActive ? "border-amber-500/40 bg-amber-950/30 text-amber-300" : "border-slate-700/60 text-slate-400 hover:text-cyan-300 hover:border-cyan-400/30"}`}
                  >
                    {stepActive ? "Exit step" : "Step mode"}
                  </button>
                  {stepActive && (
                    <>
                      <button
                        onClick={() =>
                          setTimelineStepIdx(Math.max(0, clampedStep! - 1))
                        }
                        disabled={clampedStep === 0}
                        className="rounded px-1.5 py-0.5 text-[10px] border border-slate-700/60 text-slate-400 hover:text-cyan-300 disabled:opacity-30 transition-colors"
                      >
                        ←
                      </button>
                      <span className="text-[9px] text-slate-500">
                        {clampedStep! + 1} / {total}
                      </span>
                      <button
                        onClick={() =>
                          setTimelineStepIdx(
                            Math.min(total - 1, clampedStep! + 1),
                          )
                        }
                        disabled={clampedStep === total - 1}
                        className="rounded px-1.5 py-0.5 text-[10px] border border-slate-700/60 text-slate-400 hover:text-cyan-300 disabled:opacity-30 transition-colors"
                      >
                        →
                      </button>
                    </>
                  )}
                </div>

                {/* Current step event detail */}
                {currentEv && (
                  <div className="rounded-lg border border-amber-500/30 bg-amber-950/20 px-2.5 py-2 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] text-amber-300">
                        #{currentEv.seq}
                      </span>
                      <Badge size="sm" variant="warning">
                        {currentEv.kind}
                      </Badge>
                    </div>
                    {currentEv.ts && (
                      <p className="text-[9px] text-slate-400">
                        {new Date(currentEv.ts).toLocaleString()}
                      </p>
                    )}
                    {currentEv.payload_keys.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {currentEv.payload_keys.map((k) => (
                          <span
                            key={k}
                            className="rounded bg-slate-800/60 px-1 py-0.5 text-[8px] font-mono text-slate-500"
                          >
                            {k}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Event list */}
                <div className="flex flex-col gap-0.5">
                  {events.map((ev, idx) => (
                    <button
                      key={ev.seq}
                      onClick={() => stepActive && setTimelineStepIdx(idx)}
                      className={`flex items-center justify-between rounded px-2 py-1.5 text-left transition-colors ${
                        stepActive && clampedStep === idx
                          ? "border border-amber-500/30 bg-amber-950/20"
                          : stepActive
                            ? "hover:bg-slate-800/40 cursor-pointer border border-transparent"
                            : "border border-transparent"
                      }`}
                    >
                      <span className="font-mono text-slate-500">
                        #{ev.seq}
                      </span>
                      <div className="flex items-center gap-1">
                        {ev.ts && (
                          <span className="text-[8px] text-slate-600">
                            {new Date(ev.ts).toLocaleTimeString()}
                          </span>
                        )}
                        <Badge size="sm" variant="outline">
                          {ev.kind}
                        </Badge>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            );
          })()
        ) : (
          <p className="text-xs text-slate-500">No events</p>
        )}
      </FloatingDrawer>
      <FloatingDrawer
        open={activeDrawer === "controls"}
        onClose={() => setActiveDrawer(null)}
        title="Graph Controls"
      >
        <FigControls
          layoutMode={layoutMode}
          onLayoutChange={setLayoutMode}
          locked={locked}
          onLockToggle={() => setLocked((v) => !v)}
          selectedNodeId={selectedNodeId}
          onFit={() => canvasRef.current?.fitGraph()}
          onCenter={() =>
            selectedNodeId && canvasRef.current?.centerOnNode(selectedNodeId)
          }
          onResetCamera={() => canvasRef.current?.resetCamera()}
          onZoomIn={() => canvasRef.current?.zoomIn()}
          onZoomOut={() => canvasRef.current?.zoomOut()}
          timelineVisible={timelineVisible}
          onTimelineToggle={handleTimelineToggle}
          liveSyncEnabled={timelineLiveEnabled}
          onLiveSyncToggle={handleLiveSyncToggle}
          liveSyncStatus={timelineSync.status}
          similarityMode={data?.controls?.similarity?.mode ?? "none"}
          overlayMode={overlayMode}
          onOverlayChange={setOverlayMode}
          topology={graphData?.topology}
          nodes={graphData?.nodes}
        />
      </FloatingDrawer>
    </div>
  );
}
