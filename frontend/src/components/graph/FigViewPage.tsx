"use client";

import {
  AlertTriangle,
  Box,
  GitFork,
  Hash,
  Layers,
  RefreshCw,
  Zap,
} from "lucide-react";
import { useSession } from "next-auth/react";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
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
// Sub-components
// ---------------------------------------------------------------------------

function SnapshotBanner({ data }: { data: FigSurfaceResponse }) {
  const snap = data.snapshot;
  return (
    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
      <span className="flex items-center gap-1">
        <Hash className="h-3 w-3" />
        v{snap.graph_version}
      </span>
      {snap.graph_hash && (
        <span className="font-mono" title="Graph hash">
          {snap.graph_hash.slice(0, 12)}…
        </span>
      )}
      <span title="Snapshot time">{formatTimestamp(snap.as_of)}</span>
      {!snap.consistent_read && (
        <Badge variant="warning" size="sm">eventual</Badge>
      )}
    </div>
  );
}

function TopologyStrip({ data }: { data: FigSurfaceResponse }) {
  const topo = data.topology;
  const edgeKinds = topo?.edge_counts_by_kind ?? {};
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <StatCard
        icon={<Box className="h-4 w-4 text-cyan-400" />}
        label="Nodes"
        value={topo?.node_count ?? data.nodes.length}
      />
      <StatCard
        icon={<GitFork className="h-4 w-4 text-violet-400" />}
        label="Edges"
        value={topo?.edge_count ?? data.edges.length}
      />
      {Object.entries(edgeKinds).map(([kind, count]) => (
        <StatCard
          key={kind}
          icon={<Layers className="h-4 w-4 text-slate-400" />}
          label={kind}
          value={count}
        />
      ))}
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div className="flex items-center gap-2 rounded-xl bg-slate-900/60 border border-slate-800 px-3 py-2">
      {icon}
      <div>
        <p className="text-xs text-slate-500">{label}</p>
        <p className="text-sm font-semibold text-slate-200">{value.toLocaleString()}</p>
      </div>
    </div>
  );
}

function NodeRow({ node }: { node: FigNode }) {
  const title = safeNodeTitle(node);
  const stateClass = nodeStateClass(node);
  const color = STATE_COLORS[stateClass] ?? STATE_COLORS.unknown;
  return (
    <div className="flex items-center justify-between rounded-lg bg-slate-900/40 border border-slate-800/60 px-3 py-2 text-sm">
      <div className="flex items-center gap-2 min-w-0">
        <span className={`inline-block h-2 w-2 rounded-full ${stateClass === "active" ? "bg-emerald-400" : stateClass === "cold" ? "bg-slate-500" : "bg-slate-600"}`} />
        <span className="truncate font-medium text-slate-200" title={title}>
          {title}
        </span>
        <Badge size="sm" variant="outline">{node.kind}</Badge>
        {node.level > 0 && (
          <span className="text-xs text-slate-500">L{node.level}</span>
        )}
      </div>
      <div className="flex items-center gap-3 text-xs text-slate-500 shrink-0">
        <span className={color}>{stateClass}</span>
        {node.metrics?.touch_count != null && (
          <span title="Touch count">×{node.metrics.touch_count}</span>
        )}
        <span className="font-mono" title={node.node_id}>
          {node.node_id.slice(0, 8)}
        </span>
      </div>
    </div>
  );
}

function TruncationBanner({ warnings }: { warnings: string[] }) {
  return (
    <div className="rounded-xl border border-amber-800/60 bg-amber-950/30 px-4 py-3 text-sm text-amber-300 flex items-start gap-2">
      <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
      <div>
        {warnings.map((w, i) => (
          <p key={i}>{w}</p>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function FigViewPage() {
  const { data: session } = useSession();
  const { toast } = useToast();

  const [graphId, setGraphId] = useState<string>("");
  const [state, setState] = useState<FigLoadState>({ status: "idle" });
  const [layoutMode, setLayoutMode] = useState<LayoutMode>("explore");
  const [locked, setLocked] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [timelineVisible, setTimelineVisible] = useState(false);
  const canvasRef = useRef<FigCanvasHandle>(null);
  const initializedRef = useRef(false);

  // Resolve graphId from session (same pattern as evolution page).
  useEffect(() => {
    if (initializedRef.current) return;
    const sessionGraphId = (session as { graphId?: string } | null)?.graphId;
    if (sessionGraphId) {
      setGraphId(sessionGraphId);
      initializedRef.current = true;
    }
  }, [session]);

  const loadSurface = useCallback(
    async (targetGraphId: string) => {
      if (!targetGraphId) return;
      setState({ status: "loading" });
      try {
        const data = await fetchGraphSurface(targetGraphId, {
          timelineLimit: 20,
          includeTopology: true,
        });
        clearStaleGraphState(targetGraphId);
        setState(classifyResponse(data));
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to load graph";
        setState({ status: "error", message });
        toast.error("Graph load failed", message);
      }
    },
    [toast],
  );

  // Load on graphId change.
  useEffect(() => {
    if (graphId) {
      loadSurface(graphId);
    }
  }, [graphId, loadSurface]);

  // -------------------------------------------------------------------------
  // Render states
  // -------------------------------------------------------------------------

  // Waiting for session
  if (!graphId) {
    return (
      <div className="space-y-6 pb-8 text-slate-100">
        <Header graphId="" />
        <div className="flex items-center justify-center min-h-[400px]">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  // Loading
  if (state.status === "idle" || state.status === "loading") {
    return (
      <div className="space-y-6 pb-8 text-slate-100">
        <Header graphId={graphId} />
        <div className="flex flex-col items-center justify-center min-h-[400px] gap-3">
          <Spinner size="lg" />
          <p className="text-sm text-slate-400">Loading graph surface…</p>
        </div>
      </div>
    );
  }

  // Error
  if (state.status === "error") {
    return (
      <div className="space-y-6 pb-8 text-slate-100">
        <Header graphId={graphId} />
        <ErrorState
          title="Failed to load graph"
          message={state.message}
          onRetry={() => loadSurface(graphId)}
        />
      </div>
    );
  }

  // Empty
  if (state.status === "empty") {
    return (
      <div className="space-y-6 pb-8 text-slate-100">
        <Header graphId={graphId} />
        <EmptyState
          title="No nodes in this graph"
          description="Ingest data via Storage or Memory to populate the graph."
        />
      </div>
    );
  }

  // Loaded or Degraded
  const data = state.data;
  const warnings = state.status === "degraded" ? state.warnings : [];

  return (
    <div className="space-y-5 pb-8 text-slate-100">
      <Header graphId={graphId}>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => loadSurface(graphId)}
          title="Refresh graph"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </Button>
      </Header>

      <SnapshotBanner data={data} />

      {warnings.length > 0 && <TruncationBanner warnings={warnings} />}

      <TopologyStrip data={data} />

      {/* Controls */}
      <FigControls
        layoutMode={layoutMode}
        onLayoutChange={setLayoutMode}
        locked={locked}
        onLockToggle={() => setLocked((v) => !v)}
        selectedNodeId={selectedNodeId}
        onFit={() => canvasRef.current?.fitGraph()}
        onCenter={() => selectedNodeId && canvasRef.current?.centerOnNode(selectedNodeId)}
        onResetCamera={() => canvasRef.current?.resetCamera()}
        onZoomIn={() => canvasRef.current?.zoomIn()}
        onZoomOut={() => canvasRef.current?.zoomOut()}
        timelineVisible={timelineVisible}
        onTimelineToggle={() => setTimelineVisible((v) => !v)}
        similarityMode={data.controls?.similarity?.mode ?? "none"}
      />

      {/* 3D Graph Canvas */}
      <FigCanvas
        ref={canvasRef}
        data={data}
        layoutMode={layoutMode}
        locked={locked}
        selectedNodeId={selectedNodeId}
        onNodeSelect={setSelectedNodeId}
      />

      {/* Timeline (toggled via controls) */}
      {timelineVisible && data.timeline && data.timeline.events.length > 0 && (
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-slate-200">
              Recent Events ({data.timeline.events.length})
              {data.timeline.has_more && (
                <span className="ml-1 text-xs text-slate-500">+ more</span>
              )}
            </h3>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-1 max-h-[240px] overflow-y-auto text-xs">
              {data.timeline.events.map((ev) => (
                <div
                  key={ev.seq}
                  className="flex items-center justify-between rounded bg-slate-900/30 px-2 py-1"
                >
                  <span className="font-mono text-slate-500">#{ev.seq}</span>
                  <Badge size="sm" variant="outline">{ev.kind}</Badge>
                  {ev.ts && (
                    <span className="text-slate-500">{formatTimestamp(ev.ts)}</span>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Node list */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-cyan-400" />
            <h3 className="text-sm font-semibold text-slate-200">
              Nodes ({data.nodes.length})
            </h3>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-1.5 max-h-[480px] overflow-y-auto pr-1">
            {data.nodes.map((node) => (
              <NodeRow key={node.node_id} node={node} />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Edge summary */}
      {data.edges.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <GitFork className="h-4 w-4 text-violet-400" />
              <h3 className="text-sm font-semibold text-slate-200">
                Edges ({data.edges.length})
              </h3>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {Object.entries(
                data.edges.reduce<Record<string, number>>((acc, e) => {
                  acc[e.kind] = (acc[e.kind] || 0) + 1;
                  return acc;
                }, {}),
              ).map(([kind, count]) => (
                <div
                  key={kind}
                  className="rounded-lg bg-slate-900/40 border border-slate-800/60 px-3 py-2 text-sm"
                >
                  <p className="text-xs text-slate-500">{kind}</p>
                  <p className="font-semibold text-slate-200">{count}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------

function Header({
  graphId,
  children,
}: {
  graphId: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="flex items-center justify-between">
      <div>
        <h1 className="text-xl font-semibold">FIG View</h1>
        {graphId && (
          <p className="mt-0.5 text-xs text-slate-500 font-mono">{graphId}</p>
        )}
      </div>
      {children}
    </header>
  );
}
