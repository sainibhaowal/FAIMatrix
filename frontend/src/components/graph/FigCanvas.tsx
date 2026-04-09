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
// Helpers
// ---------------------------------------------------------------------------

function toGraphData(nodes: FigNode[], edges: FigEdge[]): GraphData {
  const nodeIds = new Set(nodes.map((n) => n.node_id));
  return {
    nodes: nodes.map((n) => ({ ...n, id: n.node_id })),
    links: edges
      .filter((e) => nodeIds.has(e.src_node_id) && nodeIds.has(e.dst_node_id))
      .map((e) => ({
        source: e.src_node_id,
        target: e.dst_node_id,
        kind: e.kind,
        weight: e.weight,
        edge_id: e.edge_id,
      })),
  };
}

// Deterministic color for block/shard IDs
function getShardColor(blockId?: string): string {
  if (!blockId) return "#475569"; // slate-600
  const colors = [
    "#38bdf8", "#818cf8", "#c084fc", "#f472b6", "#fb7185", 
    "#fb923c", "#fbbf24", "#a3e635", "#4ade80", "#2dd4bf"
  ];
  let hash = 0;
  for (let i = 0; i < blockId.length; i++) {
    hash = blockId.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length]!;
}

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
  // Track cursor position separately — ForceGraph3D's onNodeHover doesn't pass a MouseEvent
  const cursorPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });
  const prevLayoutRef = useRef<LayoutMode>(layoutMode);

  // -------------------------------------------------------------------------
  // Graph Adjacency / Lineage Mapping
  // -------------------------------------------------------------------------

  const adjacency = useMemo(() => {
    const adj = new Map<string, Set<string>>();
    const incoming = new Map<string, Set<string>>();
    
    data.edges.forEach(e => {
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
    const stack = [selectedNodeId];
    
    // Upwards (Ancestors)
    let currentStack = [selectedNodeId];
    while (currentStack.length > 0) {
      const id = currentStack.pop()!;
      adjacency.incoming.get(id)?.forEach(prev => {
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
      adjacency.outgoing.get(id)?.forEach(next => {
        if (!related.has(next)) {
          related.add(next);
          currentStack.push(next);
        }
      });
    }

    return related;
  }, [topMode, selectedNodeId, adjacency]);

  // Highlighted neighbors for Explore mode
  const neighbors = useMemo(() => {
    if (topMode !== "explore" || !selectedNodeId) return new Set<string>();
    const n = new Set<string>([selectedNodeId]);
    adjacency.outgoing.get(selectedNodeId)?.forEach(id => n.add(id));
    adjacency.incoming.get(selectedNodeId)?.forEach(id => n.add(id));
    return n;
  }, [topMode, selectedNodeId, adjacency]);

  // -------------------------------------------------------------------------
  // Responsive sizing via ResizeObserver
  // -------------------------------------------------------------------------

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        const { width, height } = entry.contentRect;
        setDimensions({
          width: Math.max(400, Math.floor(width)),
          height: Math.max(300, Math.floor(height)),
        });
      }
    });

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // -------------------------------------------------------------------------
  // Graph data
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

  // -------------------------------------------------------------------------
  // Layout mode changes
  // -------------------------------------------------------------------------

  useEffect(() => {
    if (!fgRef.current) return;
    const config = getLayoutConfig(layoutMode);
    applyLayout(fgRef, config);
    prevLayoutRef.current = layoutMode;
  }, [layoutMode]);

  // -------------------------------------------------------------------------
  // Lock / unlock
  // -------------------------------------------------------------------------

  useEffect(() => {
    if (!fgRef.current) return;
    if (locked) {
      fgRef.current.pauseAnimation();
    } else {
      fgRef.current.resumeAnimation();
    }
  }, [locked]);

  // -------------------------------------------------------------------------
  // Fit to view after initial data load
  // -------------------------------------------------------------------------

  const hasInitialFit = useRef(false);
  useEffect(() => {
    if (!fgRef.current || hasInitialFit.current) return;
    if (graphData.nodes.length > 0) {
      const timer = setTimeout(() => {
        fgRef.current?.zoomToFit(400, 60);
        hasInitialFit.current = true;
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [graphData.nodes.length]);

  // -------------------------------------------------------------------------
  // Imperative handle
  // -------------------------------------------------------------------------

  useImperativeHandle(ref, () => ({
    fitGraph() {
      fgRef.current?.zoomToFit(400, 60);
    },
    centerOnNode(nodeId: string) {
      const node = graphData.nodes.find((n) => n.id === nodeId);
      if (!node || node.x == null || node.y == null || node.z == null) return;
      const dist = 120;
      fgRef.current?.cameraPosition(
        { x: node.x, y: node.y, z: (node.z ?? 0) + dist },
        { x: node.x, y: node.y, z: node.z ?? 0 },
        600,
      );
    },
    resetCamera() {
      fgRef.current?.cameraPosition(
        DEFAULT_CAMERA,
        { x: 0, y: 0, z: 0 },
        600,
      );
    },
    zoomIn() {
      const cam = fgRef.current?.camera();
      if (!cam) return;
      const pos = cam.position;
      // Zoom in = move closer (multiply by 0.65 instead of 0.75)
      const newPos = {
        x: pos.x * 0.65,
        y: pos.y * 0.65,
        z: pos.z * 0.65,
      };
      fgRef.current?.cameraPosition(newPos, undefined, 250);
    },
    zoomOut() {
      const cam = fgRef.current?.camera();
      if (!cam) return;
      const pos = cam.position;
      // Zoom out = move away (multiply by 1.5 instead of 1.33)
      const newPos = {
        x: pos.x * 1.5,
        y: pos.y * 1.5,
        z: pos.z * 1.5,
      };
      fgRef.current?.cameraPosition(newPos, undefined, 250);
    },
  }));

  // -------------------------------------------------------------------------
  // Interaction callbacks
  // -------------------------------------------------------------------------

  // Track cursor position for hover card placement
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    cursorPosRef.current = { x: e.clientX, y: e.clientY };
  }, []);

  // ForceGraph3D onNodeHover — use stored cursor position for card coords
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

  // -------------------------------------------------------------------------
  // Accessors
  // -------------------------------------------------------------------------

  const nodeColor = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (node: any) => {
      let baseColor = "#ffffff";
      
      // Analyze Mode: Shard Coloring
      if (topMode === "analyze") {
         baseColor = getShardColor(node?.provenance?.block_id);
      } else {
        const state = node?.display?.state ?? "unknown";
        baseColor = nodeColorByState(state, node?.id === selectedNodeId);
      }

      // Ensure we have a clean 6-digit hex (strip existing alpha if any)
      const cleanBase = baseColor.length > 7 ? baseColor.slice(0, 7) : baseColor;

      // Opacity Calculation
      if (!selectedNodeId) return cleanBase;
      
      let opacity = 0.95;
      if (topMode === "explore") {
        opacity = neighbors.has(node.id) ? 0.95 : 0.1;
      } else if (topMode === "lineage") {
        opacity = lineageSet.has(node.id) ? 0.95 : 0.05;
      }

      // Simple alpha hex conversion or rgba
      const alpha = Math.round(opacity * 255).toString(16).padStart(2, '0');
      return `${cleanBase}${alpha}`;
    },
    [selectedNodeId, topMode, neighbors, lineageSet],
  );

  const nodeVal = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (node: any) => nodeSizeByLevel(node?.level ?? 0),
    [],
  );

  const nodeLabel = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (node: any) => safeNodeTitle(node),
    [],
  );

  const linkColor = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (link: any) => {
      const rawColor = edgeColorByKind(link?.kind ?? "");
      // Ensure we have a clean 6-digit hex
      const baseColor = rawColor.length > 7 ? rawColor.slice(0, 7) : rawColor;
      
      let opacity = 0.85;

      if (selectedNodeId) {
        if (topMode === "explore") {
          opacity = (neighbors.has(link.source.id) && neighbors.has(link.target.id)) ? 0.85 : 0.08;
        } else if (topMode === "lineage") {
          opacity = (lineageSet.has(link.source.id) && lineageSet.has(link.target.id)) ? 0.85 : 0.05;
        }
      }

      if (baseColor.startsWith("#")) {
        const alpha = Math.round(opacity * 255).toString(16).padStart(2, '0');
        return `${baseColor}${alpha}`;
      }
      return baseColor;
    },
    [selectedNodeId, topMode, neighbors, lineageSet],
  );

  const linkWidth = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (link: any) => Math.max(0.3, (link?.weight ?? 0) * 2),
    [],
  );

  // -------------------------------------------------------------------------
  // Engine ready — apply initial layout forces
  // -------------------------------------------------------------------------

  const handleEngineStop = useCallback(() => {
    // no-op for now; could persist positions
  }, []);

  const config = getLayoutConfig(layoutMode);

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

export default FigCanvas;
