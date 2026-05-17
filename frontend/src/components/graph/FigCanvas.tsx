"use client";

import * as THREE from "three";
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
  edgeColorByKind,
  getLayoutConfig,
  nodeColorByCausality,
  nodeColorByEvolution,
  nodeColorByIdentity,
  nodeColorByLineageDepth,
  nodeColorByRetrieval,
  nodeColorByState,
  nodeColorByTemporal,
  nodeSizeByLevel,
  nodeSizeByRetrievalBoost,
} from "@/lib/figViewLayout";
import type { LayoutMode } from "@/lib/figViewLayout";

export const DEFAULT_CAMERA = { x: 0, y: 0, z: 300 } as const;

// Extended overlay mode with cognitive constellation support
type OverlayMode =
  | "none"
  | "retrieval"
  | "evolution"
  | "temporal"
  | "causality"
  | "cognitive";

// Neural constellation color mapping by cognitive type
const COGNITIVE_COLORS: Record<string, string> = {
  fact: "#3b82f6", // blue-500
  event: "#22c55e", // green-500
  procedure: "#f97316", // orange-500
  prediction: "#eab308", // yellow-500
  contradiction: "#ef4444", // red-500
  source: "#f8fafc", // slate-50 (white-ish)
  work: "#a855f7", // purple-500
  unknown: "#64748b", // slate-500
};

function nodeColorByCognitiveType(
  cognitiveType: string,
  isSelected: boolean,
): string {
  const baseColor = COGNITIVE_COLORS[cognitiveType] || COGNITIVE_COLORS.unknown;
  if (isSelected) {
    // Lighten for selected nodes
    return "#ffffff";
  }
  return baseColor;
}
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

export type FigExplainPath = {
  nodeIdSet: Set<string>;
  edgeIdSet: Set<string>;
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
  /** When set, path nodes/edges are highlighted in amber-400 with directional particles. */
  explainPath?: FigExplainPath | null;
  /**
   * When set (ISO timestamp from a timeline step event), only nodes and edges
   * with created_at <= historyTs are rendered. This enables approximate
   * graph-at-time visualization when stepping through the event timeline.
   * Nodes/edges without created_at are always shown (safe fallback).
   */
  historyTs?: string | null;
  onNodeSelect: (nodeId: string | null) => void;
  onNodeHover?: (node: FigNode | null, x: number, y: number) => void;
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Reusable 3D Assets (Prevent GPU Memory Leaks)
// ---------------------------------------------------------------------------
const GLOW_GEOM = new THREE.SphereGeometry(1, 16, 16);
const GLOW_MAT = new THREE.MeshBasicMaterial({
  color: "#fbbf24",
  transparent: true,
  opacity: 0.3,
});
const EMPTY_GROUP = new THREE.Group();

const FigCanvas = forwardRef<FigCanvasHandle, FigCanvasProps>(
  function FigCanvas(
    {
      data,
      layoutMode,
      topMode,
      locked,
      selectedNodeId,
      hiddenNodeKinds,
      hiddenEdgeKinds,
      overlayMode = "none",
      explainPath,
      historyTs,
      onNodeSelect,
      onNodeHover,
    },
    ref,
  ) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const fgRef = useRef<any>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const cursorPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
    const [dimensions, setDimensions] = useState({ width: 800, height: 500 });
    const prevLayoutRef = useRef<LayoutMode>(layoutMode);
    const [canvasReady, setCanvasReady] = useState(false);
    // Set to true when leaving a DAG mode (Lineage) so handleEngineStop can
    // re-fit the camera once the scattered nodes have settled.
    const needsCameraFitRef = useRef(false);

    // -------------------------------------------------------------------------
    // Graph Adjacency / Lineage Mapping
    // -------------------------------------------------------------------------

    const adjacency = useMemo(() => {
      const adj = new Map<string, Set<string>>();
      const incoming = new Map<string, Set<string>>();

      data.edges.forEach((e) => {
        if (!adj.has(e.src_node_id)) adj.set(e.src_node_id, new Set());
        if (!incoming.has(e.dst_node_id))
          incoming.set(e.dst_node_id, new Set());
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
      const historyMs = historyTs ? new Date(historyTs).getTime() : null;
      let visibleNodes = historyMs
        ? data.nodes.filter(
            (n) =>
              !n.created_at || new Date(n.created_at).getTime() <= historyMs,
          )
        : data.nodes;
      const filteredNodes = hiddenNodeKinds?.size
        ? visibleNodes.filter((n) => !hiddenNodeKinds.has(n.kind))
        : visibleNodes;
      const nodeIds = new Set(filteredNodes.map((n) => n.node_id));
      let filteredEdges = hiddenEdgeKinds?.size
        ? data.edges.filter((e) => !hiddenEdgeKinds.has(e.kind))
        : data.edges;
      if (historyMs) {
        filteredEdges = filteredEdges.filter(
          (e) => !e.created_at || new Date(e.created_at).getTime() <= historyMs,
        );
      }
      // Also filter out edges whose source or target nodes are hidden
      filteredEdges = filteredEdges.filter(
        (e) => nodeIds.has(e.src_node_id) && nodeIds.has(e.dst_node_id),
      );
      return toGraphData(filteredNodes, filteredEdges);
    }, [data.nodes, data.edges, hiddenNodeKinds, hiddenEdgeKinds, historyTs]);

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
      if (
        layoutMode !== prevLayoutRef.current &&
        fgRef.current &&
        canvasReady
      ) {
        const layoutConfig = getLayoutConfig(layoutMode);
        const prevConfig = prevLayoutRef.current
          ? getLayoutConfig(prevLayoutRef.current)
          : undefined;
        prevLayoutRef.current = layoutMode;

        const leavingDag =
          prevConfig !== undefined &&
          prevConfig.dagMode !== null &&
          layoutConfig.dagMode === null;

        if (leavingDag) {
          // Flag that the camera needs re-fitting once the simulation settles.
          // The actual zoomToFit is triggered in handleEngineStop so the camera
          // moves AFTER the nodes have found their new 3D positions, not before.
          needsCameraFitRef.current = true;
          // Wait one rAF frame so React has committed dagMode=undefined to
          // ForceGraph3D before we touch node positions.
          requestAnimationFrame(() => {
            applyLayout(fgRef, layoutConfig, prevConfig);
          });
        } else {
          applyLayout(fgRef, layoutConfig, prevConfig);
        }
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
    // Shared Camera Logic (High Performance)
    // -------------------------------------------------------------------------
    const fitGraph = useCallback(() => {
      try {
        if (!fgRef.current) return;
        if (typeof fgRef.current.zoomToFit === "function") {
          fgRef.current.zoomToFit(800, 80);
        }
        fgRef.current.controls?.().update?.();
      } catch (err) {
        console.error("fitGraph error:", err);
      }
    }, []);

    useImperativeHandle(ref, () => ({
      fitGraph,
      centerOnNode(nodeId: string) {
        try {
          if (!fgRef.current) return;
          const node = graphData.nodes.find((n) => n.id === nodeId);
          if (!node || node.x == null || node.y == null || node.z == null)
            return;
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
          const controls = fgRef.current.controls?.();
          const cam = fgRef.current.camera?.();
          if (!cam?.position) return;
          const target = controls?.target ?? { x: 0, y: 0, z: 0 };
          const dx = cam.position.x - target.x;
          const dy = cam.position.y - target.y;
          const dz = cam.position.z - target.z;
          const factor = 0.7;
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
          const factor = 1.4;
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

    const handleMouseMove = useCallback(
      (e: React.MouseEvent<HTMLDivElement>) => {
        cursorPosRef.current = { x: e.clientX, y: e.clientY };
      },
      [],
    );

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

    const engineStopTimerRef = useRef<NodeJS.Timeout | null>(null);
    const handleEngineStop = useCallback(() => {
      setCanvasReady(true);
      if (needsCameraFitRef.current) {
        if (engineStopTimerRef.current) clearTimeout(engineStopTimerRef.current);
        engineStopTimerRef.current = setTimeout(() => {
          fitGraph();
          needsCameraFitRef.current = false;
          engineStopTimerRef.current = null;
        }, 150);
      }
    }, [fitGraph]);

    useEffect(() => {
      return () => {
        if (engineStopTimerRef.current) clearTimeout(engineStopTimerRef.current);
      };
    }, []);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const nodeThreeObject = useCallback(
      (node: any) => {
        const inPath = explainPath?.nodeIdSet.has(node.id);
        if (inPath) {
          const size = nodeSizeByLevel(node.level) * 1.5;
          const glow = new THREE.Mesh(GLOW_GEOM, GLOW_MAT);
          glow.scale.set(size, size, size);
          // -----------------------------------------------------------------
          // OPTIMIZATION: Disable raycasting on the glow so it doesn't 
          // interfere with the native elastic dragging of the atom.
          // -----------------------------------------------------------------
          glow.raycast = () => {}; 
          return glow;
        }
        return EMPTY_GROUP;
      },
      [explainPath],
    );

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
        // EXPLAIN PATH — highest priority: highlight path nodes in amber.
        // Explicit user action (Find Path) overrides all other coloring.
        // ------------------------------------------------------------------
        if (explainPath?.nodeIdSet.has(figNode.id)) {
          return isSelected ? "#fde68a" : "#f59e0b"; // amber-200 selected / amber-400 path
        }

        // ------------------------------------------------------------------
        // COGNITIVE MODE — neural constellation coloring by memory type.
        // Takes highest priority for brain map visualization.
        // ------------------------------------------------------------------
        if (overlayMode === "cognitive") {
          return nodeColorByCognitiveType(
            figNode.cognitive_type ?? "unknown",
            isSelected,
          );
        }

        // ------------------------------------------------------------------
        // OVERLAY MODE — takes precedence over topMode coloring.
        // Normalization values are pre-computed in overlayNorm.
        // ------------------------------------------------------------------
        if (overlayMode !== "none" && overlayNorm) {
          const m = figNode.metrics;
          const tsRange = overlayNorm.maxTs - overlayNorm.minTs;

          if (overlayMode === "retrieval") {
            const normR =
              overlayNorm.maxResidual > 0
                ? (m?.residual ?? 0) / overlayNorm.maxResidual
                : 0;
            const normT =
              overlayNorm.maxTouchCount > 0
                ? (m?.touch_count ?? 0) / overlayNorm.maxTouchCount
                : 0;
            return nodeColorByRetrieval(normR * 0.6 + normT * 0.4, isSelected);
          }

          if (overlayMode === "evolution") {
            const state = figNode.display?.state ?? "unknown";
            let freshnessScore = 0;
            if (m?.last_access) {
              const ts = new Date(m.last_access).getTime();
              freshnessScore =
                tsRange > 0 ? (ts - overlayNorm.minTs) / tsRange : 1;
            }
            return nodeColorByEvolution(state, freshnessScore, isSelected);
          }

          if (overlayMode === "temporal") {
            let temporalScore = 0;
            if (m?.last_access) {
              const ts = new Date(m.last_access).getTime();
              temporalScore =
                tsRange > 0 ? (ts - overlayNorm.minTs) / tsRange : 1;
            }
            return nodeColorByTemporal(temporalScore, isSelected);
          }

          if (overlayMode === "causality") {
            const m2 = figNode.metrics;
            const normT =
              overlayNorm.maxTouchCount > 0
                ? (m2?.touch_count ?? 0) / overlayNorm.maxTouchCount
                : 0;
            let recencyScore = 0;
            if (m2?.last_access) {
              const ts = new Date(m2.last_access).getTime();
              recencyScore =
                tsRange > 0 ? (ts - overlayNorm.minTs) / tsRange : 1;
            }
            return nodeColorByCausality(
              normT * 0.5 + recencyScore * 0.5,
              isSelected,
            );
          }
        }

        // ------------------------------------------------------------------
        // ANALYZE mode → deterministic rainbow per node_id.
        // ------------------------------------------------------------------
        if (topMode === "analyze") {
          return nodeColorByIdentity(figNode.id, isSelected);
        }

        // LINEAGE mode → color by BFS depth from the selected node.
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
      [
        topMode,
        lineageDepths,
        selectedNodeId,
        overlayMode,
        overlayNorm,
        explainPath,
      ],
    );

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const nodeVal = useCallback(
      (node: any) => {
        const figNode = node as GraphNode;
        const baseSize = nodeSizeByLevel(figNode.level);
        if (
          overlayMode === "retrieval" &&
          overlayNorm &&
          overlayNorm.maxTouchCount > 0
        ) {
          const normT =
            (figNode.metrics?.touch_count ?? 0) / overlayNorm.maxTouchCount;
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
        // Explain path edges — amber, overrides all other coloring.
        if (explainPath?.edgeIdSet.has(graphLink.edge_id)) return "#f59e0b";
        if (topMode === "lineage") {
          if (selectedNodeId) {
            // Node selected: highlight lineage path, fade everything else.
            const srcIn = lineageDepths.has(
              graphLink.source as unknown as string,
            );
            const dstIn = lineageDepths.has(
              graphLink.target as unknown as string,
            );
            if (!srcIn || !dstIn) return "rgba(148, 163, 184, 0.08)";
            return edgeColorByKind(graphLink.kind);
          }
          // No node selected: inheritance edges bright, everything else dimmed.
          const k = (graphLink.kind ?? "").toLowerCase();
          if (k === "inheritance") return "#22d3ee";
          return "rgba(148, 163, 184, 0.2)";
        }
        return edgeColorByKind(graphLink.kind);
      },
      [topMode, lineageDepths, selectedNodeId, explainPath],
    );

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const linkParticles = useCallback(
      (link: any) => {
        const graphLink = link as GraphLink;
        return explainPath?.edgeIdSet.has(graphLink.edge_id) ? 4 : 0;
      },
      [explainPath],
    );

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const linkParticleColor = useCallback(
      (link: any) => {
        const graphLink = link as GraphLink;
        return explainPath?.edgeIdSet.has(graphLink.edge_id)
          ? "#fbbf24"
          : "#94a3b8";
      },
      [explainPath],
    );

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const linkWidth = useCallback(
      (link: any) => {
        const graphLink = link as GraphLink;
        const minWidth = topMode === "lineage" ? 1.0 : 0.8;
        const baseWidth = Math.max(
          minWidth,
          Math.log1p(graphLink.weight ?? 1) * 0.6,
        );
        if (
          selectedNodeId &&
          (graphLink.source === selectedNodeId ||
            graphLink.target === selectedNodeId)
        ) {
          return baseWidth * 2;
        }
        return baseWidth;
      },
      [selectedNodeId, topMode],
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
          linkDirectionalParticles={linkParticles}
          linkDirectionalParticleSpeed={0.004}
          linkDirectionalParticleColor={linkParticleColor}
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
          nodeThreeObject={nodeThreeObject}
          nodeThreeObjectExtend={true}
        />
      </div>
    );
  },
);

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
