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
import type { FigEdge, FigNode, FigSurfaceResponse } from "@/types/figView";

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
  locked: boolean;
  selectedNodeId: string | null;
  onNodeSelect: (nodeId: string | null) => void;
};

// ---------------------------------------------------------------------------
// Data transform — FigNode/FigEdge → ForceGraph format
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

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const FigCanvas = forwardRef<FigCanvasHandle, FigCanvasProps>(function FigCanvas(
  { data, layoutMode, locked, selectedNodeId, onNodeSelect },
  ref,
) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });
  const prevLayoutRef = useRef<LayoutMode>(layoutMode);

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

  const graphData = useMemo(
    () => toGraphData(data.nodes, data.edges),
    [data.nodes, data.edges],
  );

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
      fgRef.current?.cameraPosition(
        { x: pos.x * 0.75, y: pos.y * 0.75, z: pos.z * 0.75 },
        undefined,
        300,
      );
    },
    zoomOut() {
      const cam = fgRef.current?.camera();
      if (!cam) return;
      const pos = cam.position;
      fgRef.current?.cameraPosition(
        { x: pos.x * 1.33, y: pos.y * 1.33, z: pos.z * 1.33 },
        undefined,
        300,
      );
    },
  }));

  // -------------------------------------------------------------------------
  // Interaction callbacks
  // -------------------------------------------------------------------------

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
      const state = node?.display?.state ?? "unknown";
      return nodeColorByState(state, node?.id === selectedNodeId);
    },
    [selectedNodeId],
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
    (link: any) => edgeColorByKind(link?.kind ?? ""),
    [],
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
        nodeOpacity={0.9}
        nodeResolution={12}
        linkSource="source"
        linkTarget="target"
        linkColor={linkColor}
        linkWidth={linkWidth}
        linkOpacity={0.6}
        linkDirectionalArrowLength={3}
        linkDirectionalArrowRelPos={1}
        dagMode={config.dagMode ?? undefined}
        d3AlphaDecay={config.d3AlphaDecay}
        d3VelocityDecay={config.d3VelocityDecay}
        warmupTicks={50}
        cooldownTicks={100}
        enableNodeDrag={!locked}
        enableNavigationControls={true}
        showNavInfo={false}
        onNodeClick={handleNodeClick}
        onBackgroundClick={handleBackgroundClick}
        onEngineStop={handleEngineStop}
      />
    </div>
  );
});

export default FigCanvas;
