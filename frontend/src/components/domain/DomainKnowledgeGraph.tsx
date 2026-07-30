"use client";

import dynamic from "next/dynamic";
import * as THREE from "three";
import {
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  forwardRef,
} from "react";
import {
  ArrowUpRight,
  Focus,
  Layers3,
  Orbit,
  RefreshCw,
  Sparkles,
  Search,
  ZoomIn,
  ZoomOut,
} from "lucide-react";

import { Badge, Button, Spinner } from "@/components/ui";
import { safeNodeTitle } from "@/lib/figViewSafety";
import type { FigEdge, FigNode } from "@/types/figView";

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[620px] items-center justify-center text-xs font-mono text-slate-500">
      Initializing knowledge canvas...
    </div>
  ),
});
const ForceGraph3DCanvas = ForceGraph3D as unknown as any;

type DomainGraphNode = {
  id: string;
  label: string;
  type: string;
  pack?: string | null;
  kind?: string | null;
  score?: number | null;
  support_count?: number | null;
  canonical_form?: string | null;
  cognitive_type?: string | null;
  cluster_id?: number | null;
  node_id?: string | null;
  source?: "domain" | "neighborhood";
  level?: number | null;
  vector_hash?: string | null;
  residual?: number | null;
  touch_count?: number | null;
  created_at?: string | null;
  display_state?: string | null;
};

type DomainGraphEdge = {
  id: string;
  source: string;
  target: string;
  kind: string;
  weight: number;
};

type NeighborhoodResponse = {
  seed_node_id: string;
  depth_requested: number;
  depth_effective: number;
  nodes: FigNode[];
  edges: FigEdge[];
  distances: Record<string, number>;
  truncated: boolean;
  truncation_reason: string | null;
};

export type DomainKnowledgeGraphHandle = {
  fitGraph: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
  resetCamera: () => void;
};

type DomainKnowledgeGraphProps = {
  graphId: string;
  nodes: DomainGraphNode[];
  edges: DomainGraphEdge[];
};

const META = {
  pack: { color: "#F5B461", glow: "rgba(245,180,97,0.45)" },
  canonical: { color: "#A78BFA", glow: "rgba(167,139,250,0.45)" },
  term: { color: "#5EEAD4", glow: "rgba(94,234,212,0.45)" },
  graph: { color: "#FB7185", glow: "rgba(251,113,133,0.45)" },
  neighborhood: { color: "#38BDF8", glow: "rgba(56,189,248,0.45)" },
  portal: { color: "#FDE68A", glow: "rgba(253,230,138,0.45)" },
} as const;

type NormalizedNode = DomainGraphNode & {
  id: string;
  label: string;
  source: "domain" | "neighborhood";
  portal?: boolean;
};

type NormalizedEdge = DomainGraphEdge;

const GLOW_GEOM = new THREE.SphereGeometry(1, 16, 16);

function nodeCategory(node: NormalizedNode): keyof typeof META {
  if (node.portal) return "portal";
  if (node.source === "neighborhood") return "neighborhood";
  if (node.type === "pack") return "pack";
  if (node.type === "canonical") return "canonical";
  if (node.type === "term") return "term";
  return "graph";
}

function nodeLabel(node: NormalizedNode): string {
  if (node.label) return node.label;
  if (node.canonical_form) return node.canonical_form;
  return node.id;
}

function normalizeDomainNode(node: DomainGraphNode): NormalizedNode {
  return {
    ...node,
    label: node.label || node.id,
    source: node.source || "domain",
  };
}

function normalizeNeighborhoodNode(node: FigNode): NormalizedNode {
  return {
    id: node.node_id,
    label: safeNodeTitle(node),
    type: "graph",
    kind: node.kind,
    score: node.metrics?.touch_count ?? node.metrics?.residual ?? 0,
    support_count: node.metrics?.touch_count,
    cognitive_type: node.cognitive_type,
    cluster_id: node.cluster_id,
    source: "neighborhood",
    level: node.level,
    vector_hash: node.vector_hash,
    residual: node.metrics?.residual,
    touch_count: node.metrics?.touch_count,
    created_at: node.created_at,
    display_state: node.display?.state,
  };
}

function normalizeNeighborhoodEdge(edge: FigEdge): NormalizedEdge {
  return {
    id: edge.edge_id,
    source: edge.src_node_id,
    target: edge.dst_node_id,
    kind: edge.kind,
    weight: edge.weight,
  };
}

function mergeGraph(
  baseNodes: NormalizedNode[],
  baseEdges: NormalizedEdge[],
  extraNodes: NormalizedNode[],
  extraEdges: NormalizedEdge[],
) {
  const nodeMap = new Map<string, NormalizedNode>();
  for (const node of baseNodes) nodeMap.set(node.id, node);
  for (const node of extraNodes) nodeMap.set(node.id, node);
  const edgeMap = new Map<string, NormalizedEdge>();
  for (const edge of baseEdges) edgeMap.set(edge.id, edge);
  for (const edge of extraEdges) edgeMap.set(edge.id, edge);
  return { nodes: Array.from(nodeMap.values()), edges: Array.from(edgeMap.values()) };
}

export const DomainKnowledgeGraph = forwardRef<
  DomainKnowledgeGraphHandle,
  DomainKnowledgeGraphProps
>(function DomainKnowledgeGraph({ graphId, nodes, edges }, ref) {
  const graphRef = useRef<any>(null);
  const frameRef = useRef<HTMLDivElement>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<NormalizedNode[]>([]);
  const [expandedEdges, setExpandedEdges] = useState<NormalizedEdge[]>([]);
  const [loadingNeighborhood, setLoadingNeighborhood] = useState(false);
  const [neighborhoodNotice, setNeighborhoodNotice] = useState<string | null>(null);
  const [lastLiveSeq, setLastLiveSeq] = useState<number | null>(null);
  const [liveState, setLiveState] = useState<"live" | "connecting" | "idle">(
    "idle",
  );

  const baseNodes = useMemo(() => nodes.map(normalizeDomainNode), [nodes]);
  const baseEdges = useMemo(() => edges.map((edge) => ({ ...edge })), [edges]);

  const graphData = useMemo(
    () => mergeGraph(baseNodes, baseEdges, expandedNodes, expandedEdges),
    [baseNodes, baseEdges, expandedNodes, expandedEdges],
  );

  const adjacency = useMemo(() => {
    const map = new Map<string, Set<string>>();
    for (const edge of graphData.edges) {
      if (!map.has(edge.source)) map.set(edge.source, new Set());
      if (!map.has(edge.target)) map.set(edge.target, new Set());
      map.get(edge.source)!.add(edge.target);
      map.get(edge.target)!.add(edge.source);
    }
    return map;
  }, [graphData.edges]);

  const selectedNode = useMemo(
    () => graphData.nodes.find((node) => node.id === selectedId) ?? null,
    [graphData.nodes, selectedId],
  );

  const selectedNeighbors = useMemo(() => {
    if (!selectedNode) return [];
    const ids = Array.from(adjacency.get(selectedNode.id) ?? []);
    return ids
      .map((id) => graphData.nodes.find((node) => node.id === id))
      .filter(Boolean)
      .slice(0, 8) as NormalizedNode[];
  }, [adjacency, graphData.nodes, selectedNode]);

  const fitGraph = useCallback(() => {
    try {
      graphRef.current?.zoomToFit?.(700, 72);
      graphRef.current?.controls?.().update?.();
    } catch {
      // best effort
    }
  }, []);

  const zoom = useCallback((factor: number) => {
    try {
      const controls = graphRef.current?.controls?.();
      const cam = graphRef.current?.camera?.();
      if (!cam?.position) return;
      const target = controls?.target ?? { x: 0, y: 0, z: 0 };
      const dx = cam.position.x - target.x;
      const dy = cam.position.y - target.y;
      const dz = cam.position.z - target.z;
      graphRef.current?.cameraPosition?.(
        {
          x: target.x + dx * factor,
          y: target.y + dy * factor,
          z: target.z + dz * factor,
        },
        { x: target.x, y: target.y, z: target.z },
        220,
      );
    } catch {
      // best effort
    }
  }, []);

  useImperativeHandle(ref, () => ({
    fitGraph,
    zoomIn: () => zoom(0.72),
    zoomOut: () => zoom(1.35),
    resetCamera: () => {
      try {
        graphRef.current?.cameraPosition?.({ x: 0, y: 0, z: 320 }, { x: 0, y: 0, z: 0 }, 500);
      } catch {
        // best effort
      }
    },
  }));

  useEffect(() => {
    setSelectedId(null);
    setExpandedNodes([]);
    setExpandedEdges([]);
    setNeighborhoodNotice(null);
  }, [graphId]);

  useEffect(() => {
    if (!graphData.nodes.length) return;
    const timer = window.setTimeout(() => {
      fitGraph();
    }, 250);
    return () => window.clearTimeout(timer);
  }, [fitGraph, graphData.nodes.length]);

  const expandNeighborhood = useCallback(
    async (node: NormalizedNode) => {
      const nodeId =
        node.node_id || (node.id.startsWith("graph:") ? node.id.slice(6) : "");
      if (!nodeId) return;

      setLoadingNeighborhood(true);
      setNeighborhoodNotice(null);
      try {
        const response = await fetch(
          `/api/v1/graph/neighborhood?graph_id=${encodeURIComponent(
            graphId,
          )}&node_id=${encodeURIComponent(nodeId)}&depth=2&node_limit=96&edge_limit=220`,
          {
            cache: "no-store",
          },
        );
        const text = await response.text();
        const payload = text ? (JSON.parse(text) as NeighborhoodResponse) : null;
        if (!response.ok || !payload) {
          throw new Error(payload ? "Neighborhood fetch failed" : "Empty neighborhood response");
        }

        const neighborhoodNodes = payload.nodes.map(normalizeNeighborhoodNode);
        const neighborhoodEdges = payload.edges.map(normalizeNeighborhoodEdge);
        const portalNode: NormalizedNode = {
          id: `graph:${payload.seed_node_id}`,
          label: node.label || payload.seed_node_id.slice(0, 12),
          type: "graph",
          kind: "linked_graph_node",
          source: "domain",
          node_id: payload.seed_node_id,
          portal: true,
        };

        const portalEdge: NormalizedEdge = {
          id: `expand:${payload.seed_node_id}`,
          source: portalNode.id,
          target: payload.seed_node_id,
          kind: "expands_to",
          weight: 1,
        };

        setExpandedNodes((prev) => {
          const next = new Map(prev.map((item) => [item.id, item]));
          next.set(portalNode.id, portalNode);
          for (const item of neighborhoodNodes) next.set(item.id, item);
          return Array.from(next.values());
        });
        setExpandedEdges((prev) => {
          const next = new Map(prev.map((item) => [item.id, item]));
          next.set(portalEdge.id, portalEdge);
          for (const item of neighborhoodEdges) next.set(item.id, item);
          return Array.from(next.values());
        });
        setNeighborhoodNotice(
          payload.truncated
            ? `Expanded ${payload.nodes.length} nodes, trimmed by ${payload.truncation_reason}.`
            : `Expanded ${payload.nodes.length} nodes around this point.`,
        );
        fitGraph();
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Unable to expand neighborhood";
        setNeighborhoodNotice(message);
      } finally {
        setLoadingNeighborhood(false);
      }
    },
    [fitGraph, graphId],
  );

  const handleNodeClick = useCallback(
    (node: NormalizedNode) => {
      setSelectedId(node.id);
      if (node.portal || node.source === "neighborhood" || node.id.startsWith("graph:")) {
        void expandNeighborhood(node);
      }
    },
    [expandNeighborhood],
  );

  useEffect(() => {
    const handleRefresh = (event: Event) => {
      const custom = event as CustomEvent<{ graphId?: string; seq?: number }>;
      if (custom.detail?.graphId && custom.detail.graphId !== graphId) return;
      setLiveState("live");
      if (typeof custom.detail?.seq === "number") {
        setLastLiveSeq(custom.detail.seq);
      }
    };

    const handleIdle = () => {
      setLiveState("connecting");
    };

    window.addEventListener("faim:domain-live-refresh", handleRefresh);
    window.addEventListener("faim:domain-live-connecting", handleIdle);
    return () => {
      window.removeEventListener("faim:domain-live-refresh", handleRefresh);
      window.removeEventListener("faim:domain-live-connecting", handleIdle);
    };
  }, [graphId]);

  const rootNodeCount = graphData.nodes.length;
  const rootEdgeCount = graphData.edges.length;
  if (!rootNodeCount) {
    return (
      <div
        className="relative min-h-[720px] overflow-hidden rounded-[22px] border border-white/8 bg-[radial-gradient(circle_at_20%_12%,rgba(245,180,97,0.14),transparent_22%),radial-gradient(circle_at_78%_18%,rgba(94,234,212,0.10),transparent_20%),radial-gradient(circle_at_50%_52%,rgba(167,139,250,0.12),transparent_26%),linear-gradient(180deg,rgba(4,8,16,0.99),rgba(6,10,18,0.97))] text-center shadow-[0_18px_60px_rgba(0,0,0,0.34)]"
      >
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(148,163,184,0.06)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.06)_1px,transparent_1px)] bg-[size:44px_44px] opacity-40" />
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-amber-300/30 to-transparent" />
        <div className="pointer-events-none absolute left-1/2 top-1/2 h-[30rem] w-[30rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/8" />
        <div className="pointer-events-none absolute left-1/2 top-1/2 h-[22rem] w-[22rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-white/10" />
        <div className="pointer-events-none absolute left-1/2 top-1/2 h-[12rem] w-[12rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-amber-300/20 bg-amber-300/6 blur-[1px]" />
        <div className="pointer-events-none absolute left-[12%] top-[18%] h-3 w-3 rounded-full bg-amber-200/80 shadow-[0_0_24px_rgba(245,180,97,0.75)]" />
        <div className="pointer-events-none absolute right-[16%] top-[22%] h-2.5 w-2.5 rounded-full bg-teal-200/70 shadow-[0_0_22px_rgba(94,234,212,0.6)]" />
        <div className="pointer-events-none absolute left-[18%] bottom-[18%] h-2 w-2 rounded-full bg-violet-200/70 shadow-[0_0_22px_rgba(167,139,250,0.55)]" />
        <div className="pointer-events-none absolute right-[14%] bottom-[20%] h-2.5 w-2.5 rounded-full bg-rose-200/70 shadow-[0_0_20px_rgba(251,113,133,0.5)]" />

        <div className="relative mx-auto flex min-h-[720px] max-w-5xl flex-col justify-between px-5 py-5 sm:px-8 sm:py-8">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 rounded-full border border-white/8 bg-slate-950/55 px-3 py-1.5 text-[11px] text-slate-300 backdrop-blur-md">
              <Orbit size={12} className="text-amber-200" />
              Canvas idle
            </div>
            <div className="flex items-center gap-2">
              <Badge size="xs" variant="default">
                {lastLiveSeq ?? 0} events
              </Badge>
              <Badge size="xs" variant="default">
                {rootEdgeCount} links
              </Badge>
            </div>
          </div>

          <div className="flex flex-1 items-center justify-center">
            <div className="w-full max-w-2xl rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(6,10,18,0.72),rgba(8,12,20,0.88))] px-6 py-8 shadow-[0_20px_70px_rgba(0,0,0,0.35)] backdrop-blur-md sm:px-10 sm:py-10">
              <div className="mx-auto flex max-w-xl flex-col items-center gap-4">
                <div className="relative flex h-20 w-20 items-center justify-center rounded-full border border-amber-300/20 bg-amber-300/8">
                  <div className="absolute inset-[-18px] rounded-full border border-dashed border-white/10" />
                  <div className="absolute inset-[-34px] rounded-full border border-white/5" />
                  <Orbit size={26} className="text-amber-200" />
                </div>
                <div className="space-y-2">
                  <p className="text-[11px] font-mono uppercase tracking-[0.42em] text-amber-200/80">
                    Infinite canvas ready
                  </p>
                  <p className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                    This constellation has not formed yet.
                  </p>
                  <p className="mx-auto max-w-xl text-sm leading-7 text-slate-400 sm:text-[15px]">
                    Upload memory, refresh the graph, or wait for live events. When the first domain
                    links arrive, the canvas will bloom into a clickable knowledge map.
                  </p>
                </div>

                <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
                  <span className="rounded-full border border-white/8 bg-white/[0.04] px-3 py-1 text-[11px] text-slate-300">
                    Upload memory
                  </span>
                  <span className="rounded-full border border-white/8 bg-white/[0.04] px-3 py-1 text-[11px] text-slate-300">
                    Refresh graph
                  </span>
                  <span className="rounded-full border border-white/8 bg-white/[0.04] px-3 py-1 text-[11px] text-slate-300">
                    Click nodes to expand
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="grid gap-3 border-t border-white/6 pt-4 sm:grid-cols-3">
            <div className="rounded-[18px] border border-white/8 bg-slate-950/55 px-4 py-3 text-left backdrop-blur-sm">
              <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-slate-500">
                Canvas layer
              </p>
              <p className="mt-1 text-sm font-medium text-slate-100">Visible, but empty by design.</p>
            </div>
            <div className="rounded-[18px] border border-white/8 bg-slate-950/55 px-4 py-3 text-left backdrop-blur-sm">
              <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-slate-500">
                Live state
              </p>
              <p className="mt-1 text-sm font-medium text-slate-100">
                {liveState === "live" ? "Streaming events" : "Waiting for graph activity"}
              </p>
            </div>
            <div className="rounded-[18px] border border-white/8 bg-slate-950/55 px-4 py-3 text-left backdrop-blur-sm">
              <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-slate-500">
                Interaction
              </p>
              <p className="mt-1 text-sm font-medium text-slate-100">Canvas will become clickable once data lands.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={frameRef}
      className="relative overflow-hidden rounded-[22px] border border-white/8 bg-[radial-gradient(circle_at_20%_12%,rgba(245,180,97,0.10),transparent_24%),radial-gradient(circle_at_84%_14%,rgba(167,139,250,0.10),transparent_24%),linear-gradient(180deg,rgba(3,6,14,0.98),rgba(6,10,18,0.96))] shadow-[0_18px_60px_rgba(0,0,0,0.34)]"
    >
      <div className="grid gap-0 xl:grid-cols-[minmax(0,1.45fr)_360px]">
        <div className="relative min-h-[680px] overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/6 px-4 py-3">
            <div>
              <p className="font-mono text-[10px] font-bold uppercase tracking-[0.32em] text-amber-200/80">
                Infinite knowledge canvas
              </p>
              <p className="mt-1 text-sm font-semibold text-white">
                Click a node to inspect it. Click linked graph nodes to expand neighborhood.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Badge size="xs" variant="info">
                {liveState === "live" ? "live" : liveState}
              </Badge>
              <Badge size="xs" variant="default">
                {rootNodeCount} nodes
              </Badge>
              <Badge size="xs" variant="default">
                {rootEdgeCount} links
              </Badge>
              <Button size="sm" variant="ghost" leftIcon={<RefreshCw size={12} />} onClick={fitGraph}>
                Recenter
              </Button>
            </div>
          </div>

          <div className="absolute left-4 top-16 z-10 flex flex-wrap gap-2">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-slate-950/85 px-3 py-2 text-xs font-medium text-slate-200 shadow-[0_8px_24px_rgba(0,0,0,0.28)] backdrop-blur-xl"
              onClick={() => fitGraph()}
            >
              <Focus size={13} />
              Fit canvas
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-slate-950/85 px-3 py-2 text-xs font-medium text-slate-200 shadow-[0_8px_24px_rgba(0,0,0,0.28)] backdrop-blur-xl"
              onClick={() => graphRef.current?.zoomToFit?.(250, 64)}
            >
              <Layers3 size={13} />
              Reset spread
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-slate-950/85 px-3 py-2 text-xs font-medium text-slate-200 shadow-[0_8px_24px_rgba(0,0,0,0.28)] backdrop-blur-xl"
              onClick={() => zoom(0.74)}
            >
              <ZoomIn size={13} />
              Zoom in
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-slate-950/85 px-3 py-2 text-xs font-medium text-slate-200 shadow-[0_8px_24px_rgba(0,0,0,0.28)] backdrop-blur-xl"
              onClick={() => zoom(1.34)}
            >
              <ZoomOut size={13} />
              Zoom out
            </button>
          </div>

          <div className="h-[680px] w-full">
            <ForceGraph3DCanvas
              ref={graphRef}
              graphData={{ nodes: graphData.nodes, links: graphData.edges }}
              nodeId="id"
              nodeLabel={(node: NormalizedNode) => nodeLabel(node)}
              backgroundColor="rgba(0,0,0,0)"
              nodeResolution={10}
              nodeRelSize={4}
              linkSource="source"
              linkTarget="target"
              linkWidth={(link: NormalizedEdge) => {
                const base = Math.max(0.8, Math.log1p(link.weight ?? 1));
                return selectedId &&
                  (link.source === selectedId || link.target === selectedId)
                  ? base * 2.1
                  : base;
              }}
              linkColor={(link: NormalizedEdge) => {
                if (selectedId && !(link.source === selectedId || link.target === selectedId)) {
                  return "rgba(148,163,184,0.08)";
                }
                if (link.kind === "graph_link") return "#FB7185";
                if (link.kind === "canonicalizes_to") return "#A78BFA";
                if (link.kind === "pack_term") return "#F5B461";
                if (link.kind === "expands_to") return "#38BDF8";
                return "#5EEAD4";
              }}
              linkDirectionalParticles={(link: NormalizedEdge) =>
                link.kind === "expands_to" ? 6 : selectedId ? 2 : 0
              }
              linkDirectionalParticleSpeed={0.004}
              linkDirectionalParticleWidth={2}
              linkDirectionalArrowLength={(link: NormalizedEdge) =>
                link.kind === "expands_to" ? 3.5 : 1.8
              }
              linkDirectionalArrowRelPos={1}
              nodeVal={(node: NormalizedNode) => {
                if (node.portal) return 16;
                if (node.source === "neighborhood") return 13 + Math.min(8, node.level ?? 0);
                if (node.type === "pack") return 18;
                if (node.type === "canonical") return 12;
                return 10;
              }}
              nodeColor={(node: NormalizedNode) => {
                const category = nodeCategory(node);
                return META[category].color;
              }}
              nodeThreeObject={(node: NormalizedNode) => {
                const category = nodeCategory(node);
                const color = META[category].color;
                const glow = META[category].glow;
                const size = node.portal ? 1.4 : node.type === "pack" ? 1.55 : 1;
                const mesh = new THREE.Mesh(
                  new THREE.SphereGeometry(size, 18, 18),
                  new THREE.MeshBasicMaterial({
                    color,
                    transparent: true,
                    opacity: selectedNode?.id === node.id ? 1 : 0.92,
                  }),
                );
                const glowMesh = new THREE.Mesh(
                  GLOW_GEOM,
                  new THREE.MeshBasicMaterial({
                    color,
                    transparent: true,
                    opacity: 0.12,
                  }),
                );
                glowMesh.scale.set(size * 4.2, size * 4.2, size * 4.2);
                const group = new THREE.Group();
                group.add(mesh);
                group.add(glowMesh);
                group.userData = { glow };
                return group;
              }}
              nodeThreeObjectExtend={true}
              onNodeClick={(node: NormalizedNode) => {
                handleNodeClick(node);
              }}
              onNodeHover={(node: NormalizedNode | null) => {
                if (frameRef.current) {
                  frameRef.current.dataset.hover = node?.id || "";
                }
              }}
              onBackgroundClick={() => setSelectedId(null)}
              onEngineStop={() => fitGraph()}
              enableNavigationControls={true}
              warmupTicks={40}
              cooldownTicks={110}
              d3AlphaDecay={0.025}
              d3VelocityDecay={0.32}
            />
          </div>
        </div>

        <div className="border-t border-white/6 xl:border-l xl:border-t-0">
          <div className="flex items-center justify-between gap-3 border-b border-white/6 px-4 py-3">
            <div>
              <p className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-slate-500">
                Node inspector
              </p>
              <p className="mt-1 text-sm font-semibold text-white">
                {selectedNode ? nodeLabel(selectedNode) : "Click a node to inspect it"}
              </p>
            </div>
            {selectedNode ? (
              <Button size="sm" variant="ghost" onClick={() => setSelectedId(null)}>
                Clear
              </Button>
            ) : null}
          </div>

          <div className="space-y-3 p-4">
            {!selectedNode ? (
              <div className="rounded-[18px] border border-white/8 bg-white/[0.03] p-4">
                <p className="text-sm font-medium text-slate-100">
                  The canvas becomes explorable the moment you click a node.
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  Linked graph nodes can expand into live neighborhoods. Domain nodes can be focused
                  and inspected directly from the same control surface.
                </p>
              </div>
            ) : (
              <>
                <div
                  className="rounded-[18px] border border-white/8 p-4"
                  style={{
                    background: `linear-gradient(180deg, ${META[nodeCategory(selectedNode)].glow}, rgba(3,6,14,0.96))`,
                  }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-mono text-[10px] font-bold uppercase tracking-[0.26em] text-slate-400">
                        {selectedNode.portal ? "Portal node" : selectedNode.source === "neighborhood" ? "Expanded graph node" : "Domain node"}
                      </p>
                      <h3 className="mt-1 truncate text-lg font-semibold text-white">
                        {nodeLabel(selectedNode)}
                      </h3>
                      <p className="mt-1 text-xs text-slate-400">
                        {selectedNode.kind || selectedNode.type}
                      </p>
                    </div>
                    <span
                      className="flex h-10 w-10 items-center justify-center rounded-full"
                      style={{
                        backgroundColor: `${META[nodeCategory(selectedNode)].color}18`,
                        color: META[nodeCategory(selectedNode)].color,
                        boxShadow: `0 0 18px ${META[nodeCategory(selectedNode)].glow}`,
                      }}
                    >
                      {selectedNode.source === "neighborhood" ? <Sparkles size={16} /> : <Orbit size={16} />}
                    </span>
                  </div>

                  <div className="mt-4 grid gap-2 sm:grid-cols-2">
                    <Badge size="xs" variant="default">
                      {selectedNode.type}
                    </Badge>
                    {selectedNode.pack ? (
                      <Badge size="xs" variant="info">
                        {selectedNode.pack}
                      </Badge>
                    ) : null}
                    {selectedNode.cognitive_type ? (
                      <Badge size="xs" variant="success">
                        {selectedNode.cognitive_type}
                      </Badge>
                    ) : null}
                    {selectedNode.cluster_id != null ? (
                      <Badge size="xs" variant="warning">
                        cluster {selectedNode.cluster_id}
                      </Badge>
                    ) : null}
                  </div>

                  <div className="mt-4 grid gap-2 sm:grid-cols-2">
                    <div className="rounded-[14px] border border-white/8 bg-slate-950/50 p-3">
                      <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
                        Score
                      </p>
                      <p className="mt-1 text-lg font-semibold text-white">
                        {selectedNode.score != null ? selectedNode.score.toFixed(2) : "—"}
                      </p>
                    </div>
                    <div className="rounded-[14px] border border-white/8 bg-slate-950/50 p-3">
                      <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
                        Support
                      </p>
                      <p className="mt-1 text-lg font-semibold text-white">
                        {selectedNode.support_count ?? selectedNode.touch_count ?? "—"}
                      </p>
                    </div>
                  </div>

                  {selectedNode.node_id ? (
                    <div className="mt-4 rounded-[14px] border border-white/8 bg-slate-950/50 p-3 font-mono text-[11px] text-slate-400">
                      <p className="uppercase tracking-[0.22em] text-slate-500">Node id</p>
                      <p className="mt-1 break-all text-slate-200">{selectedNode.node_id}</p>
                    </div>
                  ) : null}
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button size="sm" leftIcon={<Focus size={12} />} onClick={fitGraph}>
                    Fit graph
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setSelectedId(null)}>
                    Clear focus
                  </Button>
                  {(selectedNode.portal || selectedNode.source === "neighborhood" || selectedNode.node_id) ? (
                    <Button
                      size="sm"
                      leftIcon={
                        loadingNeighborhood ? <Spinner size={12} /> : <ArrowUpRight size={12} />
                      }
                      onClick={() => void expandNeighborhood(selectedNode)}
                      disabled={loadingNeighborhood}
                    >
                      {loadingNeighborhood ? "Expanding..." : "Expand neighborhood"}
                    </Button>
                  ) : null}
                </div>

                {neighborhoodNotice ? (
                  <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3 text-sm text-slate-300">
                    {neighborhoodNotice}
                  </div>
                ) : null}

                <div className="rounded-[18px] border border-white/8 bg-white/[0.03] p-4">
                  <div className="flex items-center gap-2">
                    <Search size={13} className="text-teal-300" />
                    <p className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
                      Connected neighbors
                    </p>
                  </div>
                  <div className="mt-3 space-y-2">
                    {selectedNeighbors.length ? (
                      selectedNeighbors.map((node) => (
                        <button
                          key={node.id}
                          type="button"
                          onClick={() => {
                            setSelectedId(node.id);
                            if (node.portal || node.source === "neighborhood") {
                              void expandNeighborhood(node);
                            }
                          }}
                          className="flex w-full items-center justify-between gap-3 rounded-[14px] border border-white/8 bg-slate-950/40 px-3 py-2 text-left transition hover:border-white/16 hover:bg-slate-950/70"
                        >
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium text-white">
                              {nodeLabel(node)}
                            </p>
                            <p className="mt-0.5 text-[11px] text-slate-500">
                              {node.kind || node.type}
                            </p>
                          </div>
                          <Badge size="xs" variant="default">
                            {node.source}
                          </Badge>
                        </button>
                      ))
                    ) : (
                      <div className="rounded-[14px] border border-dashed border-white/10 px-3 py-6 text-center text-sm text-slate-400">
                        No neighbors visible for this node yet.
                      </div>
                    )}
                  </div>
                </div>

                <div className="rounded-[18px] border border-white/8 bg-white/[0.03] p-4">
                  <div className="flex items-center gap-2">
                    <Layers3 size={13} className="text-violet-300" />
                    <p className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
                      Canvas state
                    </p>
                  </div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <div className="rounded-[14px] border border-white/8 bg-slate-950/45 px-3 py-2.5">
                      <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500">
                        Live seq
                      </p>
                      <p className="mt-1 text-sm font-semibold text-white">
                        {lastLiveSeq ?? 0}
                      </p>
                    </div>
                    <div className="rounded-[14px] border border-white/8 bg-slate-950/45 px-3 py-2.5">
                      <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500">
                        State
                      </p>
                      <p className="mt-1 text-sm font-semibold text-white">{liveState}</p>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
});

export default DomainKnowledgeGraph;
