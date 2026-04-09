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
  nodeColorByState,
  nodeSizeByLevel,
} from "@/lib/figViewLayout";
import type { LayoutMode } from "@/lib/figViewLayout";
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
  onNodeSelect: (nodeId: string | null) => void;
  onNodeHover?: (node: FigNode | null, x: number, y: number) => void;
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const FigCanvas = forwardRef<FigCanvasHandle, FigCanvasProps>(function FigCanvas(
  { data, layoutMode, topMode, locked, selectedNodeId, hiddenNodeKinds, hiddenEdgeKinds, onNodeSelect, onNodeHover },
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

  // For Lineage mode: recursive find all related nodes
  const lineageSet = useMemo(() => {
    if (topMode !== "lineage" || !selectedNodeId) return new Set<string>();

    const related = new Set<string>([selectedNodeId]);

    // Upwards (Ancestors)
    let currentStack = [selectedNodeId];
    while (currentStack.length > 0) {
      const id = currentStack.pop()!;
      adjacency.incoming.get(id)?.forEach((prev) => {
        if (!related.has(prev)) {
          related.add(prev);
          currentStack.push(prev);
        }
      });
    }

    // Downwards (Descendants)
    currentStack = [selectedNodeId];
    while (currentStack.length > 0) {
      const id = currentStack.pop()!;
      adjacency.outgoing.get(id)?.forEach((next) => {
        if (!related.has(next)) {
          related.add(next);
          currentStack.push(next);
        }
      });
    }

    return related;
  }, [topMode, selectedNodeId, adjacency]);

  // -------------------------------------------------------------------------
  // Graph transformation: filter by hidden kinds, apply layout
  // -------------------------------------------------------------------------

  const graphData = useMemo(() => {
    const filteredNodes = hiddenNodeKinds?.size
      ? data.nodes.filter((n) => !hiddenNodeKinds.has(n.kind))
      : data.nodes;
    const filteredEdges = hiddenEdgeKinds?.size
      ? data.edges.filter((e) => !hiddenEdgeKinds.has(e.kind))
      : data.edges;
    return toGraphData(filteredNodes, filteredEdges);
  }, [data.nodes, data.edges, hiddenNodeKinds, hiddenEdgeKinds]);

  const config = getLayoutConfig(layoutMode);

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
      if (!fgRef.current) {
        console.warn("Canvas not ready: fitGraph");
        return;
      }
      try {
        fgRef.current.zoomToFit(400, 60);
      } catch (err) {
        console.error("fitGraph error:", err);
      }
    },
    centerOnNode(nodeId: string) {
      if (!fgRef.current) {
        console.warn("Canvas not ready: centerOnNode");
        return;
      }
      try {
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
      if (!fgRef.current) {
        console.warn("Canvas not ready: resetCamera");
        return;
      }
      try {
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
      if (!fgRef.current) {
        console.warn("Canvas not ready: zoomIn");
        return;
      }
      try {
        const cam = fgRef.current.camera();
        if (!cam || !cam.position) {
          console.warn("Camera position unavailable");
          return;
        }
        const pos = cam.position;
        const newPos = {
          x: pos.x * 0.65,
          y: pos.y * 0.65,
          z: pos.z * 0.65,
        };
        fgRef.current.cameraPosition(newPos, undefined, 250);
      } catch (err) {
        console.error("zoomIn error:", err);
      }
    },
    zoomOut() {
      if (!fgRef.current) {
        console.warn("Canvas not ready: zoomOut");
        return;
      }
      try {
        const cam = fgRef.current.camera();
        if (!cam || !cam.position) {
          console.warn("Camera position unavailable");
          return;
        }
        const pos = cam.position;
        const newPos = {
          x: pos.x * 1.5,
          y: pos.y * 1.5,
          z: pos.z * 1.5,
        };
        fgRef.current.cameraPosition(newPos, undefined, 250);
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
      if (topMode === "lineage" && !lineageSet.has(figNode.id)) {
        return "rgba(100, 116, 139, 0.2)";
      }
      const stateClass = figNode.display?.state ?? "unknown";
      return nodeColorByState(stateClass, selectedNodeId === figNode.id);
    },
    [topMode, lineageSet, selectedNodeId],
  );

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodeVal = useCallback((node: any) => {
    const figNode = node as GraphNode;
    return nodeSizeByLevel(figNode.level);
  }, []);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const linkColor = useCallback(
    (link: any) => {
      const graphLink = link as GraphLink;
      if (topMode === "lineage") {
        const isInLineage =
          lineageSet.has(graphLink.source as unknown as string) &&
          lineageSet.has(graphLink.target as unknown as string);
        if (!isInLineage) return "rgba(100, 116, 139, 0.1)";
      }
      return edgeColorByKind(graphLink.kind);
    },
    [topMode, lineageSet],
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
