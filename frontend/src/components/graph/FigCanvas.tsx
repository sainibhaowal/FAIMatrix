"use client";

import dynamic from "next/dynamic";
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";

import type { FigNode } from "@/types/figView";

import {
  applyLayout,
  DEFAULT_CAMERA,
  edgeColorByKind,
  getLayoutConfig,
  nodeColorByEvolution,
  nodeColorByIdentity,
  nodeColorByLineageDepth,
  nodeColorByRetrieval,
  nodeColorByState,
  nodeColorByTemporal,
  nodeSizeByLevel,
  nodeSizeByRetrievalBoost,
} from "@/lib/figViewLayout";
import type { LayoutMode, OverlayMode } from "@/lib/figViewLayout";
import { safeNodeTitle } from "@/lib/figViewSafety";
import type { FigEdge, FigSurfaceResponse } from "@/types/figView";

// ---------------------------------------------------------------------------
// Dynamic import — ForceGraph3D requires window/WebGL (no SSR)
// ---------------------------------------------------------------------------

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full text-slate-600 text-xs font-mono">
      Initializing 3D engine…
    </div>
  ),
});

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type TopMode = "explore" | "analyze" | "lineage";

type GraphNode = FigNode & {
  id: string;
  x?: number;
  y?: number;
  z?: number;
};

type GraphLink = {
  source: string;
  target: string;
  kind: string;
  weight: number;
  edge_id: string;
};

type GraphData = {
  nodes: GraphNode[];
  links: GraphLink[];
};

export type FigCanvasHandle = {
  fitGraph: () => void;
  centerOnNode: (nodeId: string) => void;
  resetCamera: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
};

type FigCanvasProps = {
  data: FigSurfaceResponse;
  layoutMode: LayoutMode;
  topMode: TopMode;
  locked: boolean;
  selectedNodeId: string | null;
  hiddenNodeKinds?: Set<string>;
  hiddenEdgeKinds?: Set<string>;
  overlayMode?: OverlayMode;
  onNodeSelect: (nodeId: string | null) => void;
  onNodeHover?: (node: FigNode | null, x: number, y: number) => void;
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const FigCanvas = forwardRef<FigCanvasHandle, FigCanvasProps>(function FigCanvas(
  { data, layoutMode, topMode, locked, selectedNodeId, hiddenNodeKinds, hiddenEdgeKinds, overlayMode = "none", onNodeSelect, onNodeHover },
  ref,
) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const cursorPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });
  const prevLayoutRef = useRef<LayoutMode>(layoutMode);
  const [canvasReady, setCanvasReady] = useState(false);

  // -------------------------------------------------------------------------
  // Graph Adjacency / Lineage Mapping
  // -------------------------------------------------------------------------

  const adjacency = useMemo(() => {
    const adj = new Map<string, Set<string>>();
    const incoming = new Map<string, Set<string>>();

    data.edges.forEach((e) => {
      if (!adj.has(e.src_node_id)) adj.set(e.src_node_id, new Set());
      if (!incoming.has(e.dst_node_id)) incoming.set(e.dst_node_id, new Set());
      adj.get(e.src_node_id)!.add(e.dst_node_id);
      incoming.get(e.dst_node_id)!.add(e.src_node_id);
    });

    return { outgoing: adj, incoming };
  }, [data.edges]);

  // For Lineage mode: BFS depth from selected node (both directions).
  // depth 0 = selected, 1 = direct neighbors, etc. Missing id = not in lineage.
  const lineageDepths = useMemo(() => {
    const depths = new Map<string, number>();
    if (topMode !== "lineage" || !selectedNodeId) return depths;

    depths.set(selectedNodeId, 0);
    const queue: [string, number][] = [[selectedNodeId, 0]];
    while (queue.length > 0) {
      const [id, d] = queue.shift()!;
      const nextDepth = d + 1;
      const neighbors = new Set<string>();
      adjacency.outgoing.get(id)?.forEach((n) => neighbors.add(n));
      adjacency.incoming.get(id)?.forEach((n) => neighbors.add(n));
      for (const n of Array.from(neighbors)) {
        if (!depths.has(n)) {
          depths.set(n, nextDepth);
          queue.push([n, nextDepth]);
        }
      }
    }
    return depths;
  }, [topMode, selectedNodeId, adjacency]);

  // -------------------------------------------------------------------------
  // Graph transformation: filter by hidden kinds, apply layout
  // -------------------------------------------------------------------------

  const graphData = useMemo(() => {
    const filteredNodes = hiddenNodeKinds?.size
      ? data.nodes.filter((n) => !hiddenNodeKinds.has(n.kind))
      : data.nodes;
    const nodeIds = new Set(filteredNodes.map((n) => n.node_id));
    let filteredEdges = hiddenEdgeKinds?.size
      ? data.edges.filter((e) => !hiddenEdgeKinds.has(e.kind))
      : data.edges;
    // Also filter out edges whose source or target nodes are hidden
    filteredEdges = filteredEdges.filter(
      (e) => nodeIds.has(e.src_node_id) && nodeIds.has(e.dst_node_id)
    );
    return toGraphData(filteredNodes, filteredEdges);
  }, [data.nodes, data.edges, hiddenNodeKinds, hiddenEdgeKinds]);

  const config = getLayoutConfig(layoutMode);

  // -------------------------------------------------------------------------
  // Overlay normalization — computed once per overlay mode change or node list
  // change. Provides the min/max values needed to normalize node metrics into
  // [0, 1] scores for retrieval / evolution / temporal overlays.
  // Only populated when overlayMode !== "none".
  // -------------------------------------------------------------------------

  const overlayNorm = useMemo(() => {
    if (overlayMode === "none") return null;
    let maxResidual = 0;
    let maxTouchCount = 0;
    let minTs = Infinity;
    let maxTs = -Infinity;
    for (const n of data.nodes) {
      const m = n.metrics;
      if (!m) continue;
      if (m.residual > maxResidual) maxResidual = m.residual;
      if (m.touch_count > maxTouchCount) maxTouchCount = m.touch_count;
      if (m.last_access) {
        const ts = new Date(m.last_access).getTime();
        if (ts < minTs) minTs = ts;
        if (ts > maxTs) maxTs = ts;
      }
    }
    return { maxResidual, maxTouchCount, minTs, maxTs };
  }, [overlayMode, data.nodes]);

  // -------------------------------------------------------------------------
  // Mark canvas as ready when graph data loads
  // -------------------------------------------------------------------------

  useEffect(() => {
    if (graphData.nodes.length > 0 && fgRef.current) {
      setCanvasReady(true);
    }
  }, [graphData.nodes.length]);

  // -------------------------------------------------------------------------
  // Apply layout if it changed
  // -------------------------------------------------------------------------

  useEffect(() => {
    if (layoutMode !== prevLayoutRef.current && fgRef.current && canvasReady) {
      const layoutConfig = getLayoutConfig(layoutMode);
      applyLayout(fgRef, layoutConfig);
      prevLayoutRef.current = layoutMode;
    }
  }, [layoutMode, canvasReady]);

  // -------------------------------------------------------------------------
  // Responsive canvas dimensions
  // -------------------------------------------------------------------------

  useEffect(() => {
    const observer = new ResizeObserver(() => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    });

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => observer.disconnect();
  }, []);

  // -------------------------------------------------------------------------
  // Expose handle: fitGraph, centerOnNode, resetCamera, zoomIn, zoomOut
  // -------------------------------------------------------------------------

  useImperativeHandle(ref, () => ({
    fitGraph() {
      try {
        if (!fgRef.current) return;
        // Prefer built-in zoomToFit; fall back to resetting the camera if it
        // no-ops (e.g. when called before the force engine has positioned nodes).
        if (typeof fgRef.current.zoomToFit === "function") {
          fgRef.current.zoomToFit(400, 80);
        }
        // Force a controls update so the change is applied immediately.
        fgRef.current.controls?.().update?.();
      } catch (err) {
        console.error("fitGraph error:", err);
      }
    },
    centerOnNode(nodeId: string) {
      try {
        if (!fgRef.current) return;
        const node = graphData.nodes.find((n) => n.id === nodeId);
        if (!node || node.x == null || node.y == null || node.z == null) return;
        const dist = 120;
        fgRef.current.cameraPosition(
          { x: node.x, y: node.y, z: (node.z ?? 0) + dist },
          { x: node.x, y: node.y, z: node.z ?? 0 },
          600,
        );
      } catch (err) {
        console.error("centerOnNode error:", err);
      }
    },
    resetCamera() {
      try {
        if (!fgRef.current) return;
        fgRef.current.cameraPosition(
          DEFAULT_CAMERA,
          { x: 0, y: 0, z: 0 },
          600,
        );
      } catch (err) {
        console.error("resetCamera error:", err);
      }
    },
    zoomIn() {
      try {
        if (!fgRef.current) return;
        // Move camera toward its OrbitControls target (dolly in).
        const controls = fgRef.current.controls?.();
        const cam = fgRef.current.camera?.();
        if (!cam?.position) return;
        const target = controls?.target ?? { x: 0, y: 0, z: 0 };
        const dx = cam.position.x - target.x;
        const dy = cam.position.y - target.y;
        const dz = cam.position.z - target.z;
        const factor = 0.7; // 30% closer
        fgRef.current.cameraPosition(
          {
            x: target.x + dx * factor,
            y: target.y + dy * factor,
            z: target.z + dz * factor,
          },
          { x: target.x, y: target.y, z: target.z },
          250,
        );
      } catch (err) {
        console.error("zoomIn error:", err);
      }
    },
    zoomOut() {
      try {
        if (!fgRef.current) return;
        const controls = fgRef.current.controls?.();
        const cam = fgRef.current.camera?.();
        if (!cam?.position) return;
        const target = controls?.target ?? { x: 0, y: 0, z: 0 };
        const dx = cam.position.x - target.x;
        const dy = cam.position.y - target.y;
        const dz = cam.position.z - target.z;
        const factor = 1.4; // 40% farther
        fgRef.current.cameraPosition(
          {
            x: target.x + dx * factor,
            y: target.y + dy * factor,
            z: target.z + dz * factor,
          },
          { x: target.x, y: target.y, z: target.z },
          250,
        );
      } catch (err) {
        console.error("zoomOut error:", err);
      }
    },
  }));

  // -------------------------------------------------------------------------
  // Interaction callbacks
  // -------------------------------------------------------------------------

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    cursorPosRef.current = { x: e.clientX, y: e.clientY };
  }, []);

  const handleNodeHover = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (node: any) => {
      if (!onNodeHover) return;
      const { x, y } = cursorPosRef.current;
      onNodeHover(node ?? null, x, y);
    },
    [onNodeHover],
  );

  const handleNodeClick = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (node: any) => {
      onNodeSelect(node?.id ?? null);
    },
    [onNodeSelect],
  );

  const handleBackgroundClick = useCallback(() => {
    onNodeSelect(null);
  }, [onNodeSelect]);

  const handleEngineStop = useCallback(() => {
    setCanvasReady(true);
  }, []);

  // -------------------------------------------------------------------------
  // Computed colors/sizes for nodes and edges
  // -------------------------------------------------------------------------

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodeLabel = useCallback((node: any) => {
    const figNode = node as GraphNode;
    return safeNodeTitle(figNode);
  }, []);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodeColor = useCallback(
    (node: any) => {
      const figNode = node as GraphNode;
      const isSelected = selectedNodeId === figNode.id;

      // ------------------------------------------------------------------
      // OVERLAY MODE — takes precedence over topMode coloring.
      // Normalization values are pre-computed in overlayNorm.
      // ------------------------------------------------------------------
      if (overlayMode !== "none" && overlayNorm) {
        const m = figNode.metrics;
        const tsRange = overlayNorm.maxTs - overlayNorm.minTs;

        if (overlayMode === "retrieval") {
          const normR = overlayNorm.maxResidual > 0
            ? (m?.residual ?? 0) / overlayNorm.maxResidual
            : 0;
          const normT = overlayNorm.maxTouchCount > 0
            ? (m?.touch_count ?? 0) / overlayNorm.maxTouchCount
            : 0;
          return nodeColorByRetrieval(normR * 0.6 + normT * 0.4, isSelected);
        }

        if (overlayMode === "evolution") {
          const state = figNode.display?.state ?? "unknown";
          let freshnessScore = 0;
          if (m?.last_access) {
            const ts = new Date(m.last_access).getTime();
            freshnessScore = tsRange > 0
              ? (ts - overlayNorm.minTs) / tsRange
              : 1; // single timestamp → treat as fresh
          }
          return nodeColorByEvolution(state, freshnessScore, isSelected);
        }

        if (overlayMode === "temporal") {
          let temporalScore = 0;
          if (m?.last_access) {
            const ts = new Date(m.last_access).getTime();
            temporalScore = tsRange > 0
              ? (ts - overlayNorm.minTs) / tsRange
              : 1;
          }
          return nodeColorByTemporal(temporalScore, isSelected);
        }
      }

      // ------------------------------------------------------------------
      // ANALYZE mode → deterministic rainbow per node_id (guaranteed variety
      // even when all nodes share the same kind/level/state).
      // ------------------------------------------------------------------
      if (topMode === "analyze") {
        return nodeColorByIdentity(figNode.id, isSelected);
      }

      // LINEAGE mode → color by BFS depth from the selected node. Non-lineage
      // nodes dim only when a selection exists; otherwise show identity colors.
      if (topMode === "lineage") {
        if (!selectedNodeId) {
          return nodeColorByIdentity(figNode.id, false);
        }
        const depth = lineageDepths.get(figNode.id);
        if (depth === undefined) {
          return "rgba(100, 116, 139, 0.4)";
        }
        return nodeColorByLineageDepth(depth, isSelected);
      }

      // EXPLORE mode → state-based lifecycle colors.
      const stateClass = figNode.display?.state ?? "unknown";
      return nodeColorByState(stateClass, isSelected);
    },
    [topMode, lineageDepths, selectedNodeId, overlayMode, overlayNorm],
  );

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodeVal = useCallback(
    (node: any) => {
      const figNode = node as GraphNode;
      const baseSize = nodeSizeByLevel(figNode.level);
      if (overlayMode === "retrieval" && overlayNorm && overlayNorm.maxTouchCount > 0) {
        const normT = (figNode.metrics?.touch_count ?? 0) / overlayNorm.maxTouchCount;
        return nodeSizeByRetrievalBoost(baseSize, normT);
      }
      return baseSize;
    },
    [overlayMode, overlayNorm],
  );

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const linkColor = useCallback(
    (link: any) => {
      const graphLink = link as GraphLink;
      if (topMode === "lineage" && selectedNodeId) {
        const srcIn = lineageDepths.has(graphLink.source as unknown as string);
        const dstIn = lineageDepths.has(graphLink.target as unknown as string);
        if (!srcIn || !dstIn) return "rgba(100, 116, 139, 0.1)";
      }
      return edgeColorByKind(graphLink.kind);
    },
    [topMode, lineageDepths, selectedNodeId],
  );

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const linkWidth = useCallback(
    (link: any) => {
      const graphLink = link as GraphLink;
      const baseWidth = Math.max(0.5, Math.log(graphLink.weight) * 0.5);
      if (selectedNodeId && (graphLink.source === selectedNodeId || graphLink.target === selectedNodeId)) {
        return baseWidth * 1.5;
      }
      return baseWidth;
    },
    [selectedNodeId],
  );

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div
      ref={containerRef}
      className="relative h-full w-full overflow-hidden bg-transparent"
      onMouseMove={handleMouseMove}
    >
      <ForceGraph3D
        ref={fgRef}
        graphData={graphData}
        width={dimensions.width}
        height={dimensions.height}
        backgroundColor="rgba(0,0,0,0)"
        nodeId="id"
        nodeLabel={nodeLabel}
        nodeColor={nodeColor}
        nodeVal={nodeVal}
        nodeResolution={12}
        linkSource="source"
        linkTarget="target"
        linkColor={linkColor}
        linkWidth={linkWidth}
        linkDirectionalArrowLength={3}
        linkDirectionalArrowRelPos={1}
        dagMode={topMode === "lineage" ? "td" : (config.dagMode ?? undefined)}
        d3AlphaDecay={config.d3AlphaDecay}
        d3VelocityDecay={config.d3VelocityDecay}
        warmupTicks={50}
        cooldownTicks={100}
        enableNodeDrag={!locked}
        enableNavigationControls={true}
        showNavInfo={false}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        onBackgroundClick={handleBackgroundClick}
        onEngineStop={handleEngineStop}
      />
    </div>
  );
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function toGraphData(nodes: FigNode[], edges: FigEdge[]): GraphData {
  return {
    nodes: nodes.map((n) => ({ ...n, id: n.node_id })),
    links: edges.map((e) => ({
      source: e.src_node_id,
      target: e.dst_node_id,
      kind: e.kind,
      weight: e.weight,
      edge_id: e.edge_id,
    })),
  };
}

export default FigCanvas;
