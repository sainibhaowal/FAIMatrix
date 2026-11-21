"use client";

import React, {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Activity,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Cpu,
  GitCompare,
  GitMerge,
  Layers,
  Play,
  Radio,
  RotateCcw,
  Scissors,
  Search,
  Sparkles,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { Badge } from "@/components/ui";

export interface ChildDetail {
  id: string;
  label: string;
  type: string;
  similarity: number;
}

export interface MergeDecision {
  winner: string;
  action: string;
  similarity: number;
  reason: string;
}

export interface FlowNodeData {
  id: string;
  stage: "atom" | "macro" | "merge";
  title: string;
  subtitle: string;
  cognitiveType: string;
  pressureLambda?: number | null;
  childCount?: number | null;
  status?: string | null;
  childrenDetails?: ChildDetail[] | null;
  decision?: MergeDecision | null;
  recent: boolean;
  summary?: string | null;
  synthesisOrigin?: string | null;
  residual?: number | null;
  level?: number | null;
  weights?: Record<string, number>;
  pairId?: string | null;
}

export interface InventionFlowEdgeItem {
  edge_id: string;
  src_id: string;
  dst_id: string;
  kind: "atom_to_macro" | "atom_to_theory" | "atom_to_merge" | "macro_to_merge";
  weight: number;
  label: string;
}

export interface InventionFlowTheoryItem {
  theory_id: string;
  theory_type: string;
  title: string;
  description: string;
  confidence: number;
  graph_version: number;
  evidence_node_ids: string[];
}

export interface InventionFlowEvalMetrics {
  d_hat: number;
  h_hat: number;
  lambda_hat: number;
  redundancy_r: number;
  novelty_n: number;
  energy_e: number;
  compression_ratio_cr: number;
  macro_absorption_rate: number;
  merge_consensus_score: number;
  theory_confidence_mean: number;
  total_nodes: number;
  total_macros: number;
  total_merges: number;
  total_theories: number;
  graph_version?: number;
}

export interface InventionFlowData {
  graphId: string;
  tenantId: string;
  nodeCount: number;
  macroCount: number;
  mergeCount: number;
  theoryCount?: number;
  computedAt?: string;
  stages: {
    atoms: FlowNodeData[];
    macros: FlowNodeData[];
    merges: FlowNodeData[];
  };
  edges?: InventionFlowEdgeItem[];
  theories?: InventionFlowTheoryItem[];
  evalMetrics?: InventionFlowEvalMetrics | null;
}

interface InventionFlowCanvasProps {
  graphId: string;
  data?: InventionFlowData | null;
  loading?: boolean;
  error?: string | null;
  sseConnected?: boolean;
  isSynthesizing?: boolean;
  onRetry?: () => void;
  onTriggerSynthesize?: () => void;
}

type StageFilter = "all" | "atom" | "macro" | "theory" | "merge";
type CognitiveFilter =
  | "all"
  | "fact"
  | "procedure"
  | "event"
  | "contradiction"
  | "work";

type InspectorTarget =
  | { kind: "node"; node: FlowNodeData }
  | { kind: "theory"; theory: InventionFlowTheoryItem }
  | null;

interface MeasuredPath {
  edge: InventionFlowEdgeItem;
  d: string;
  mx: number;
  my: number;
}

const COGNITIVE_TYPES: Array<Exclude<CognitiveFilter, "all">> = [
  "fact",
  "procedure",
  "event",
  "contradiction",
  "work",
];

function cogBadgeStyle(cogType: string): string {
  switch ((cogType || "").toLowerCase()) {
    case "fact":
      return "border-sky-500/35 bg-sky-500/15 text-sky-300";
    case "procedure":
      return "border-cyan-500/35 bg-cyan-500/15 text-cyan-300";
    case "event":
      return "border-amber-500/35 bg-amber-500/15 text-amber-300";
    case "contradiction":
      return "border-rose-500/40 bg-rose-500/15 text-rose-300";
    case "work":
      return "border-emerald-500/35 bg-emerald-500/15 text-emerald-300";
    case "macro":
      return "border-purple-500/40 bg-purple-500/20 text-purple-200";
    default:
      return "border-slate-500/35 bg-slate-500/15 text-slate-300";
  }
}

function edgeStroke(kind: InventionFlowEdgeItem["kind"]): string {
  switch (kind) {
    case "atom_to_macro":
      return "#c084fc";
    case "atom_to_theory":
      return "#34d399";
    case "macro_to_merge":
      return "#38bdf8";
    case "atom_to_merge":
      return "#f472b6";
  }
}

export const InventionFlowCanvas: React.FC<InventionFlowCanvasProps> = ({
  graphId,
  data,
  loading = false,
  error = null,
  sseConnected = false,
  isSynthesizing = false,
  onRetry,
  onTriggerSynthesize,
}) => {
  const [activeStageFilter, setActiveStageFilter] =
    useState<StageFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [cognitiveType, setCognitiveType] = useState<CognitiveFilter>("all");
  const [diffMode, setDiffMode] = useState(false);
  const [showAllAtoms, setShowAllAtoms] = useState(false);

  const [hoveredKey, setHoveredKey] = useState<string | null>(null);
  const [inspector, setInspector] = useState<InspectorTarget>(null);

  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0, tx: 0, ty: 0 });

  const viewportRef = useRef<HTMLDivElement | null>(null);
  const worldRef = useRef<HTMLDivElement | null>(null);
  const cardRefs = useRef<Map<string, HTMLElement>>(new Map());
  const [svgSize, setSvgSize] = useState({ w: 1200, h: 640 });
  const [paths, setPaths] = useState<MeasuredPath[]>([]);

  const registerCardRef = useCallback(
    (domKey: string) => (el: HTMLElement | null) => {
      if (el) {
        cardRefs.current.set(domKey, el);
      } else {
        cardRefs.current.delete(domKey);
      }
    },
    [],
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if ((e.target as HTMLElement).closest("button, a, input, [data-card]")) {
        return;
      }
      isDraggingRef.current = true;
      dragStartRef.current = {
        x: e.clientX,
        y: e.clientY,
        tx: transform.x,
        ty: transform.y,
      };
    },
    [transform.x, transform.y],
  );

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDraggingRef.current) return;
    const dx = e.clientX - dragStartRef.current.x;
    const dy = e.clientY - dragStartRef.current.y;
    setTransform((prev) => ({
      ...prev,
      x: dragStartRef.current.tx + dx,
      y: dragStartRef.current.ty + dy,
    }));
  }, []);

  const handleMouseUp = useCallback(() => {
    isDraggingRef.current = false;
  }, []);

  const zoomIn = useCallback(() => {
    setTransform((prev) => ({
      ...prev,
      scale: Math.min(1.6, Number((prev.scale + 0.1).toFixed(2))),
    }));
  }, []);

  const zoomOut = useCallback(() => {
    setTransform((prev) => ({
      ...prev,
      scale: Math.max(0.55, Number((prev.scale - 0.1).toFixed(2))),
    }));
  }, []);

  const resetView = useCallback(() => {
    setTransform({ x: 0, y: 0, scale: 1 });
  }, []);

  const stages = useMemo(
    () => data?.stages ?? { atoms: [], macros: [], merges: [] },
    [data?.stages],
  );
  const theories = useMemo(() => data?.theories ?? [], [data?.theories]);
  const rawEdges = useMemo(() => data?.edges ?? [], [data?.edges]);
  const evalMetrics = data?.evalMetrics ?? null;

  // Compute incoming/outgoing edges per node DOM id for prioritization & lineage highlight
  const edgeIndex = useMemo(() => {
    const connectedIds = new Set<string>();
    const adjacency = new Map<string, Set<string>>();

    const link = (a: string, b: string) => {
      connectedIds.add(a);
      connectedIds.add(b);
      if (!adjacency.has(a)) adjacency.set(a, new Set());
      if (!adjacency.has(b)) adjacency.set(b, new Set());
      adjacency.get(a)!.add(b);
      adjacency.get(b)!.add(a);
    };

    for (const edge of rawEdges) {
      link(edge.src_id, edge.dst_id);
    }
    return { connectedIds, adjacency };
  }, [rawEdges]);

  const applyFilters = useCallback(
    (nodes: FlowNodeData[]): FlowNodeData[] => {
      const query = searchQuery.trim().toLowerCase();
      return nodes.filter((node) => {
        if (diffMode && !node.recent) return false;
        if (cognitiveType !== "all" && node.cognitiveType !== cognitiveType) {
          return false;
        }
        if (
          query &&
          !`${node.title} ${node.subtitle} ${node.summary || ""} ${node.id}`
            .toLowerCase()
            .includes(query)
        ) {
          return false;
        }
        return true;
      });
    },
    [searchQuery, cognitiveType, diffMode],
  );

  // Put connected atoms first so bezier topology links visibly across stages!
  const filteredAtomsAll = useMemo(() => {
    const list = applyFilters(stages.atoms);
    return [...list].sort((a, b) => {
      const aConn = edgeIndex.connectedIds.has(a.id) ? 1 : 0;
      const bConn = edgeIndex.connectedIds.has(b.id) ? 1 : 0;
      if (aConn !== bConn) return bConn - aConn;
      return (b.pressureLambda ?? 0) - (a.pressureLambda ?? 0);
    });
  }, [stages.atoms, applyFilters, edgeIndex.connectedIds]);

  const visibleAtoms = useMemo(
    () =>
      showAllAtoms
        ? filteredAtomsAll.slice(0, 48)
        : filteredAtomsAll.slice(0, 12),
    [filteredAtomsAll, showAllAtoms],
  );

  const visibleMacros = useMemo(
    () => applyFilters(stages.macros).slice(0, 18),
    [stages.macros, applyFilters],
  );

  const visibleTheories = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return theories
      .filter((t) => {
        if (!query) return true;
        return `${t.title} ${t.description} ${t.theory_type}`
          .toLowerCase()
          .includes(query);
      })
      .slice(0, 8);
  }, [theories, searchQuery]);

  const visibleMerges = useMemo(
    () => applyFilters(stages.merges).slice(0, 16),
    [stages.merges, applyFilters],
  );

  const recentCount = useMemo(
    () =>
      [...stages.atoms, ...stages.macros, ...stages.merges].filter(
        (n) => n.recent,
      ).length,
    [stages],
  );

  const isEmpty =
    !loading &&
    !error &&
    data != null &&
    stages.atoms.length === 0 &&
    stages.macros.length === 0 &&
    stages.merges.length === 0 &&
    theories.length === 0;

  const hasData = !loading && !error && data != null && !isEmpty;

  const hasFilteredData =
    hasData &&
    (visibleAtoms.length > 0 ||
      visibleMacros.length > 0 ||
      visibleTheories.length > 0 ||
      visibleMerges.length > 0);

  const activeFocusKey = useMemo(() => {
    if (hoveredKey) return hoveredKey;
    if (!inspector) return null;
    if (inspector.kind === "theory")
      return `theory:${inspector.theory.theory_id}`;
    return inspector.node.stage === "merge"
      ? `merge:${inspector.node.id}`
      : inspector.node.id;
  }, [hoveredKey, inspector]);

  const highlightedKeys = useMemo(() => {
    if (!activeFocusKey) return null;
    const set = new Set<string>([activeFocusKey]);
    const neighbors = edgeIndex.adjacency.get(activeFocusKey);
    if (neighbors) {
      neighbors.forEach((n) => set.add(n));
    }
    return set;
  }, [activeFocusKey, edgeIndex.adjacency]);

  // Measure DOM card anchors in unscaled world coordinates to draw true Bezier edges
  const recomputePaths = useCallback(() => {
    const world = worldRef.current;
    if (!world) return;
    const worldRect = world.getBoundingClientRect();
    const scale = transform.scale || 1;
    setSvgSize({
      w: Math.max(world.offsetWidth, Math.round(worldRect.width / scale)),
      h: Math.max(world.offsetHeight, Math.round(worldRect.height / scale)),
    });

    const nextPaths: MeasuredPath[] = [];
    for (const edge of rawEdges) {
      const srcEl = cardRefs.current.get(edge.src_id);
      const dstEl = cardRefs.current.get(edge.dst_id);
      if (!srcEl || !dstEl) continue;

      const sRect = srcEl.getBoundingClientRect();
      const dRect = dstEl.getBoundingClientRect();

      const x1 = (sRect.right - worldRect.left) / scale;
      const y1 = (sRect.top + sRect.height / 2 - worldRect.top) / scale;
      const x2 = (dRect.left - worldRect.left) / scale;
      const y2 = (dRect.top + dRect.height / 2 - worldRect.top) / scale;

      const dx = Math.max(40, Math.abs(x2 - x1) * 0.48);
      const d = `M ${x1.toFixed(1)} ${y1.toFixed(1)} C ${(x1 + dx).toFixed(
        1,
      )} ${y1.toFixed(1)}, ${(x2 - dx).toFixed(1)} ${y2.toFixed(1)}, ${x2.toFixed(
        1,
      )} ${y2.toFixed(1)}`;
      nextPaths.push({
        edge,
        d,
        mx: (x1 + x2) / 2,
        my: (y1 + y2) / 2,
      });
    }
    setPaths(nextPaths);
  }, [rawEdges, transform.scale]);

  useLayoutEffect(() => {
    const raf = requestAnimationFrame(recomputePaths);
    return () => cancelAnimationFrame(raf);
  }, [
    recomputePaths,
    visibleAtoms,
    visibleMacros,
    visibleTheories,
    visibleMerges,
    activeStageFilter,
    hasData,
  ]);

  useEffect(() => {
    const world = worldRef.current;
    if (!world || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => {
      requestAnimationFrame(recomputePaths);
    });
    ro.observe(world);
    return () => ro.disconnect();
  }, [recomputePaths]);

  const showAtomsCol =
    activeStageFilter === "all" || activeStageFilter === "atom";
  const showSynthesisCol =
    activeStageFilter === "all" ||
    activeStageFilter === "macro" ||
    activeStageFilter === "theory";
  const showMergesCol =
    activeStageFilter === "all" || activeStageFilter === "merge";

  const enabledColCount =
    (showAtomsCol ? 1 : 0) +
    (showSynthesisCol ? 1 : 0) +
    (showMergesCol ? 1 : 0);

  return (
    <div className="relative w-full overflow-hidden rounded-2xl border border-white/10 bg-[#040711] shadow-[0_0_50px_rgba(15,23,42,0.7)]">
      {/* Live Evaluation Telemetry Ribbon */}
      {hasData && evalMetrics && (
        <div className="relative z-20 flex flex-wrap items-center justify-between gap-2 border-b border-white/10 bg-gradient-to-r from-purple-950/35 via-[#070c18] to-cyan-950/30 px-4 py-2 font-mono text-[11px]">
          <div className="flex flex-wrap items-center gap-3">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] ${
                sseConnected
                  ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
                  : "border-amber-500/40 bg-amber-500/15 text-amber-300"
              }`}
            >
              <Radio
                size={10}
                className={sseConnected ? "animate-pulse text-emerald-400" : ""}
              />
              {sseConnected ? "SSE LIVE" : "SYNC"}
            </span>
            <span className="text-sky-300">
              D̂ <b>{evalMetrics.d_hat.toFixed(3)}</b>
            </span>
            <span className="text-cyan-300">
              Ĥ <b>{evalMetrics.h_hat.toFixed(3)}</b>
            </span>
            <span className="text-amber-300">
              λ̂ <b>{evalMetrics.lambda_hat.toFixed(3)}</b>
            </span>
            <span className="text-rose-300">
              R <b>{evalMetrics.redundancy_r.toFixed(3)}</b>
            </span>
            <span className="text-emerald-300">
              N <b>{evalMetrics.novelty_n.toFixed(3)}</b>
            </span>
            <span className="text-fuchsia-300">
              CR <b>{evalMetrics.compression_ratio_cr.toFixed(3)}</b>
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-[10px] text-slate-300">
            <span>
              Macro Absorption:{" "}
              <b className="text-purple-300">
                {(evalMetrics.macro_absorption_rate * 100).toFixed(1)}%
              </b>
            </span>
            <span>
              Merge Consensus:{" "}
              <b className="text-cyan-300">
                {(evalMetrics.merge_consensus_score * 100).toFixed(1)}%
              </b>
            </span>
            <span>
              Theory Conf:{" "}
              <b className="text-emerald-300">
                {(evalMetrics.theory_confidence_mean * 100).toFixed(1)}%
              </b>
            </span>
            {evalMetrics.graph_version != null && (
              <span className="text-slate-400">
                v{evalMetrics.graph_version}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Top Header Controls */}
      <div className="relative z-20 flex flex-wrap items-center justify-between gap-3 border-b border-white/8 bg-black/50 p-3.5 backdrop-blur-xl">
        <div className="flex flex-wrap items-center gap-2">
          <Sparkles size={16} className="text-purple-400 animate-pulse" />
          <span className="font-mono text-xs font-bold uppercase tracking-wider text-slate-100">
            Self-Invention Topology — {graphId}
          </span>
          <Badge variant="secondary" size="xs">
            CFP DAG · {paths.length} Links
          </Badge>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Stage Filter Switches */}
          <div className="flex flex-wrap items-center gap-1 rounded-xl border border-white/10 bg-white/[0.03] p-1">
            {(
              [
                ["all", "All Stages"],
                ["atom", `Atoms ${data?.nodeCount ?? stages.atoms.length}`],
                ["macro", `Macros ${data?.macroCount ?? stages.macros.length}`],
                ["theory", `Theories ${data?.theoryCount ?? theories.length}`],
                ["merge", `Merges ${data?.mergeCount ?? stages.merges.length}`],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setActiveStageFilter(key)}
                className={`rounded-lg px-2.5 py-1 font-mono text-[11px] transition-all ${
                  activeStageFilter === key
                    ? "border border-purple-500/45 bg-purple-500/20 text-purple-200 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {onTriggerSynthesize && (
            <button
              type="button"
              disabled={isSynthesizing}
              onClick={onTriggerSynthesize}
              className="inline-flex items-center gap-1.5 rounded-xl border border-purple-400/45 bg-gradient-to-r from-purple-600/30 to-cyan-600/25 px-3 py-1.5 font-mono text-[11px] font-semibold text-purple-100 hover:from-purple-600/45 hover:to-cyan-600/40 disabled:opacity-50 transition-all shadow-[0_0_16px_rgba(168,85,247,0.2)]"
            >
              <Play
                size={12}
                className={isSynthesizing ? "animate-spin" : ""}
              />
              {isSynthesizing ? "Synthesizing..." : "Synthesize & Evolve"}
            </button>
          )}
        </div>
      </div>

      {/* Search, Cognitive Type + Cycle Diff Toolbar */}
      {hasData && (
        <div className="relative z-20 flex flex-wrap items-center gap-2 border-b border-white/8 bg-black/30 px-4 py-2.5 backdrop-blur-xl">
          <div className="relative min-w-[180px] flex-1 max-w-xs">
            <Search
              size={13}
              className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search atoms, macros, theories…"
              className="w-full rounded-lg border border-white/10 bg-white/[0.03] py-1.5 pl-8 pr-8 font-mono text-xs text-slate-200 placeholder:text-slate-500 outline-none focus:border-purple-500/50"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
              >
                <X size={12} />
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-1">
            <button
              type="button"
              onClick={() => setCognitiveType("all")}
              className={`rounded-lg px-2 py-1 font-mono text-[11px] transition-all ${
                cognitiveType === "all"
                  ? "border border-slate-500/40 bg-slate-500/20 text-slate-200"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              all types
            </button>
            {COGNITIVE_TYPES.map((type) => (
              <button
                key={type}
                type="button"
                onClick={() =>
                  setCognitiveType(cognitiveType === type ? "all" : type)
                }
                className={`rounded-lg px-2 py-1 font-mono text-[11px] transition-all ${
                  cognitiveType === type
                    ? "border border-purple-500/40 bg-purple-500/20 text-purple-300"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {type}
              </button>
            ))}
          </div>

          <div className="ml-auto flex items-center gap-2">
            {filteredAtomsAll.length > 12 && (
              <button
                type="button"
                onClick={() => setShowAllAtoms((v) => !v)}
                className="rounded-lg border border-white/10 px-2.5 py-1 font-mono text-[11px] text-slate-300 hover:border-cyan-500/40 hover:text-cyan-200 transition-all"
              >
                {showAllAtoms
                  ? "Compact Atoms (12)"
                  : `Expand Atoms (${Math.min(48, filteredAtomsAll.length)})`}
              </button>
            )}

            <button
              type="button"
              onClick={() => setDiffMode((v) => !v)}
              className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 font-mono text-[11px] transition-all ${
                diffMode
                  ? "border border-amber-500/40 bg-amber-500/20 text-amber-300"
                  : "border border-white/10 text-slate-400 hover:text-amber-200"
              }`}
              title="Only nodes touched by the latest completed evolution cycle"
            >
              <GitCompare size={13} />
              Cycle diff
              {diffMode && recentCount > 0 && (
                <span className="rounded bg-amber-500/30 px-1.5 text-[10px]">
                  {recentCount}
                </span>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Floating Zoom & Center Controls */}
      <div className="absolute bottom-4 left-4 z-20 flex items-center gap-1.5 rounded-xl border border-white/10 bg-black/80 p-1.5 font-mono text-xs backdrop-blur-xl shadow-2xl">
        <button
          type="button"
          onClick={zoomIn}
          className="rounded-lg p-1.5 text-slate-300 hover:bg-white/10 hover:text-white transition-all"
          title="Zoom In"
        >
          <ZoomIn size={14} />
        </button>
        <button
          type="button"
          onClick={zoomOut}
          className="rounded-lg p-1.5 text-slate-300 hover:bg-white/10 hover:text-white transition-all"
          title="Zoom Out"
        >
          <ZoomOut size={14} />
        </button>
        <button
          type="button"
          onClick={resetView}
          className="rounded-lg p-1.5 text-slate-300 hover:bg-white/10 hover:text-white transition-all"
          title="Reset Pan & Zoom"
        >
          <RotateCcw size={14} />
        </button>
        <span className="border-l border-white/10 pl-2 text-[11px] text-purple-300">
          {(transform.scale * 100).toFixed(0)}%
        </span>
      </div>

      {/* Main 2.5D Sci-Fi Topology Viewport */}
      <div
        ref={viewportRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className="relative min-h-[540px] max-h-[760px] w-full overflow-auto cursor-grab active:cursor-grabbing bg-[#03060f] bg-[radial-gradient(rgba(148,163,184,0.14)_1px,transparent_1px)] [background-size:24px_24px]"
      >
        {loading && (
          <div className="flex h-[480px] flex-col items-center justify-center gap-3 font-mono text-xs text-slate-400">
            <Cpu size={28} className="text-purple-400 animate-pulse" />
            <span>Mapping topological manifold & CFP macro synthesis…</span>
          </div>
        )}

        {!loading && error && (
          <div className="flex h-[480px] flex-col items-center justify-center gap-3 px-6 text-center font-mono text-xs text-rose-300">
            <span>{error}</span>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="rounded-lg border border-rose-500/40 bg-rose-500/15 px-3 py-1.5 text-rose-200 hover:bg-rose-500/25"
              >
                Retry Topology Load
              </button>
            )}
          </div>
        )}

        {isEmpty && (
          <div className="flex h-[480px] flex-col items-center justify-center gap-3 px-6 text-center font-mono text-xs text-slate-400">
            <Layers size={28} className="text-cyan-400" />
            <span>
              No nodes, macros, theories, or merges found for {graphId}.
            </span>
            {onTriggerSynthesize && (
              <button
                type="button"
                onClick={onTriggerSynthesize}
                className="rounded-lg border border-purple-500/40 bg-purple-500/15 px-3 py-1.5 text-purple-200 hover:bg-purple-500/25"
              >
                Run Synthesis Cycle
              </button>
            )}
          </div>
        )}

        {hasData && !hasFilteredData && (
          <div className="flex h-[440px] flex-col items-center justify-center gap-2 font-mono text-xs text-slate-400">
            <span>
              No topology items match current search / filter criteria.
            </span>
            <button
              type="button"
              onClick={() => {
                setSearchQuery("");
                setCognitiveType("all");
                setDiffMode(false);
              }}
              className="rounded-lg border border-white/15 px-3 py-1 text-slate-200 hover:bg-white/10"
            >
              Clear Filters
            </button>
          </div>
        )}

        {hasFilteredData && (
          <div
            ref={worldRef}
            style={{
              transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`,
              transformOrigin: "top left",
            }}
            className="relative min-w-[1060px] p-6 transition-transform duration-75"
          >
            {/* True Measured SVG Bezier Connections Layer */}
            <svg
              width={svgSize.w}
              height={svgSize.h}
              viewBox={`0 0 ${svgSize.w} ${svgSize.h}`}
              className="pointer-events-none absolute inset-0 z-10 overflow-visible"
            >
              <defs>
                <filter
                  id="neonGlow"
                  x="-20%"
                  y="-20%"
                  width="140%"
                  height="140%"
                >
                  <feGaussianBlur stdDeviation="2.5" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {paths.map(({ edge, d, mx, my }) => {
                const isActive =
                  highlightedKeys !== null
                    ? highlightedKeys.has(edge.src_id) &&
                      highlightedKeys.has(edge.dst_id)
                    : false;
                const dimmed = highlightedKeys !== null && !isActive;
                const color = edgeStroke(edge.kind);
                return (
                  <g key={edge.edge_id}>
                    <path
                      d={d}
                      fill="none"
                      stroke={color}
                      strokeWidth={isActive ? 2.4 : 1.35}
                      strokeOpacity={dimmed ? 0.08 : isActive ? 0.95 : 0.48}
                      strokeDasharray={
                        edge.kind === "atom_to_theory" ? "5 4" : undefined
                      }
                      filter={isActive ? "url(#neonGlow)" : undefined}
                    />
                    {isActive && edge.label && (
                      <g transform={`translate(${mx}, ${my})`}>
                        <rect
                          x={-22}
                          y={-9}
                          width={44}
                          height={18}
                          rx={5}
                          fill="#050914"
                          stroke={color}
                          strokeOpacity={0.65}
                          strokeWidth={1}
                        />
                        <text
                          x={0}
                          y={3}
                          textAnchor="middle"
                          fill="#e2e8f0"
                          fontSize={9}
                          fontFamily="monospace"
                        >
                          {edge.label}
                        </text>
                      </g>
                    )}
                  </g>
                );
              })}
            </svg>

            {/* 3-Stage Coordinated DAG Columns */}
            <div
              className={`relative z-20 grid gap-14 ${
                enabledColCount === 1
                  ? "grid-cols-1 max-w-2xl"
                  : enabledColCount === 2
                    ? "grid-cols-2"
                    : "grid-cols-3"
              }`}
            >
              {/* STAGE 1: DOCUMENT ATOMS */}
              {showAtomsCol && (
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between rounded-xl border border-sky-500/25 bg-sky-950/20 px-3 py-2 font-mono text-xs">
                    <span className="inline-flex items-center gap-2 font-semibold text-sky-200">
                      <span className="h-2 w-2 rounded-full bg-sky-400 shadow-[0_0_8px_#38bdf8]" />
                      STAGE 1 · ATOMS
                    </span>
                    <span className="text-[10px] text-sky-300/80">
                      {visibleAtoms.length}/{filteredAtomsAll.length} shown
                    </span>
                  </div>

                  {visibleAtoms.map((atom) => {
                    const isDimmed =
                      highlightedKeys !== null && !highlightedKeys.has(atom.id);
                    const isSelected =
                      inspector?.kind === "node" &&
                      inspector.node.id === atom.id;
                    const connected = edgeIndex.connectedIds.has(atom.id);
                    return (
                      <div
                        key={atom.id}
                        ref={registerCardRef(atom.id)}
                        data-card
                        onMouseEnter={() => setHoveredKey(atom.id)}
                        onMouseLeave={() => setHoveredKey(null)}
                        onClick={() =>
                          setInspector({ kind: "node", node: atom })
                        }
                        className={`group relative cursor-pointer rounded-xl border p-3 backdrop-blur-md transition-all ${
                          isSelected
                            ? "border-sky-400 bg-sky-950/40 shadow-[0_0_20px_rgba(56,189,248,0.22)]"
                            : connected
                              ? "border-white/15 bg-[#090f1d]/90 hover:border-sky-400/50"
                              : "border-white/8 bg-[#070b15]/80 hover:border-white/25"
                        } ${isDimmed ? "opacity-30" : "opacity-100"}`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="line-clamp-2 text-xs font-medium text-slate-100">
                            {atom.title}
                          </div>
                          <span
                            className={`shrink-0 rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase ${cogBadgeStyle(
                              atom.cognitiveType,
                            )}`}
                          >
                            {atom.cognitiveType}
                          </span>
                        </div>
                        <div className="mt-2 flex items-center justify-between gap-2 font-mono text-[10px] text-slate-400">
                          <span className="truncate">{atom.subtitle}</span>
                          {atom.pressureLambda != null && (
                            <span className="shrink-0 text-amber-300">
                              λ {atom.pressureLambda.toFixed(3)}
                            </span>
                          )}
                        </div>
                        {connected && (
                          <span className="absolute -right-1.5 top-1/2 h-3 w-3 -translate-y-1/2 rounded-full border border-[#03060f] bg-purple-400 shadow-[0_0_8px_#c084fc]" />
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* STAGE 2: SYNTHESIZED MACROS + GRAPH THEORIES */}
              {showSynthesisCol && (
                <div className="flex flex-col gap-4">
                  {(activeStageFilter === "all" ||
                    activeStageFilter === "macro") && (
                    <div className="flex flex-col gap-3">
                      <div className="flex items-center justify-between rounded-xl border border-purple-500/35 bg-purple-950/25 px-3 py-2 font-mono text-xs">
                        <span className="inline-flex items-center gap-2 font-semibold text-purple-200">
                          <span className="h-2 w-2 rounded-full bg-purple-400 shadow-[0_0_8px_#c084fc]" />
                          STAGE 2A · SELF-INVENTED MACROS
                        </span>
                        <span className="text-[10px] text-purple-300">
                          {visibleMacros.length} macros
                        </span>
                      </div>

                      {visibleMacros.length === 0 ? (
                        <div className="rounded-xl border border-dashed border-purple-500/30 bg-purple-950/10 p-4 font-mono text-[11px] text-slate-400">
                          <div className="font-semibold text-purple-300">
                            No L1+ Macros Synthesized Yet
                          </div>
                          <p className="mt-1 text-[10px] leading-relaxed text-slate-400">
                            Macros crystallize when co-activation patterns or
                            grounded theories compress constituent atoms via CFP
                            weights.
                          </p>
                          {onTriggerSynthesize && (
                            <button
                              type="button"
                              onClick={onTriggerSynthesize}
                              disabled={isSynthesizing}
                              className="mt-2.5 inline-flex items-center gap-1 rounded-lg border border-purple-500/40 bg-purple-500/20 px-2.5 py-1 text-[10px] text-purple-200 hover:bg-purple-500/30"
                            >
                              <Sparkles size={11} />
                              Synthesize Macros Now
                            </button>
                          )}
                        </div>
                      ) : (
                        visibleMacros.map((macro) => {
                          const isDimmed =
                            highlightedKeys !== null &&
                            !highlightedKeys.has(macro.id);
                          const isSelected =
                            inspector?.kind === "node" &&
                            inspector.node.id === macro.id;
                          const weightEntries = Object.entries(
                            macro.weights || {},
                          ).slice(0, 3);
                          return (
                            <div
                              key={macro.id}
                              ref={registerCardRef(macro.id)}
                              data-card
                              onMouseEnter={() => setHoveredKey(macro.id)}
                              onMouseLeave={() => setHoveredKey(null)}
                              onClick={() =>
                                setInspector({ kind: "node", node: macro })
                              }
                              className={`relative cursor-pointer rounded-xl border p-3.5 backdrop-blur-md transition-all ${
                                isSelected
                                  ? "border-purple-400 bg-purple-950/45 shadow-[0_0_24px_rgba(192,132,252,0.28)]"
                                  : "border-purple-500/35 bg-[#100a22]/90 hover:border-purple-400/70"
                              } ${isDimmed ? "opacity-30" : "opacity-100"}`}
                            >
                              <span className="absolute -left-1.5 top-1/2 h-3 w-3 -translate-y-1/2 rounded-full border border-[#03060f] bg-purple-400 shadow-[0_0_8px_#c084fc]" />
                              <span className="absolute -right-1.5 top-1/2 h-3 w-3 -translate-y-1/2 rounded-full border border-[#03060f] bg-cyan-400 shadow-[0_0_8px_#38bdf8]" />

                              <div className="flex items-start justify-between gap-2">
                                <div className="line-clamp-2 text-xs font-semibold text-purple-100">
                                  {macro.title}
                                </div>
                                <span className="shrink-0 rounded border border-purple-400/40 bg-purple-500/20 px-1.5 py-0.5 font-mono text-[9px] text-purple-200">
                                  L{macro.level ?? 1} · {macro.childCount ?? 0}{" "}
                                  atoms
                                </span>
                              </div>

                              {macro.summary && (
                                <p className="mt-1.5 line-clamp-2 text-[11px] leading-snug text-slate-300">
                                  {macro.summary}
                                </p>
                              )}

                              {weightEntries.length > 0 && (
                                <div className="mt-2 flex flex-wrap gap-1 font-mono text-[9px]">
                                  {weightEntries.map(([label, w]) => (
                                    <span
                                      key={label}
                                      className="rounded border border-purple-400/25 bg-purple-500/10 px-1.5 py-0.5 text-purple-200"
                                    >
                                      {Number(w).toFixed(2)}·
                                      {label.slice(0, 14)}
                                    </span>
                                  ))}
                                </div>
                              )}

                              <div className="mt-2 flex items-center justify-between font-mono text-[10px] text-slate-400">
                                <span className="truncate">
                                  {macro.synthesisOrigin || "macro_synthesis"}
                                </span>
                                <span className="text-amber-300">
                                  λ {(macro.pressureLambda ?? 0).toFixed(3)} · ρ{" "}
                                  {(macro.residual ?? 0).toFixed(2)}
                                </span>
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  )}

                  {/* Subsection B: Symbolic Graph Theories */}
                  {(activeStageFilter === "all" ||
                    activeStageFilter === "theory") && (
                    <div className="flex flex-col gap-3">
                      <div className="flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-950/20 px-3 py-2 font-mono text-xs">
                        <span className="inline-flex items-center gap-2 font-semibold text-emerald-200">
                          <BookOpen size={13} className="text-emerald-400" />
                          STAGE 2B · SYMBOLIC THEORIES
                        </span>
                        <span className="text-[10px] text-emerald-300">
                          {visibleTheories.length} active
                        </span>
                      </div>

                      {visibleTheories.map((t) => {
                        const domKey = `theory:${t.theory_id}`;
                        const isDimmed =
                          highlightedKeys !== null &&
                          !highlightedKeys.has(domKey);
                        const isSelected =
                          inspector?.kind === "theory" &&
                          inspector.theory.theory_id === t.theory_id;
                        return (
                          <div
                            key={t.theory_id}
                            ref={registerCardRef(domKey)}
                            data-card
                            onMouseEnter={() => setHoveredKey(domKey)}
                            onMouseLeave={() => setHoveredKey(null)}
                            onClick={() =>
                              setInspector({ kind: "theory", theory: t })
                            }
                            className={`relative cursor-pointer rounded-xl border p-3 backdrop-blur-md transition-all ${
                              isSelected
                                ? "border-emerald-400 bg-emerald-950/40 shadow-[0_0_20px_rgba(52,211,153,0.22)]"
                                : "border-emerald-500/30 bg-[#061813]/85 hover:border-emerald-400/65"
                            } ${isDimmed ? "opacity-30" : "opacity-100"}`}
                          >
                            <span className="absolute -left-1.5 top-1/2 h-3 w-3 -translate-y-1/2 rounded-full border border-[#03060f] bg-emerald-400 shadow-[0_0_8px_#34d399]" />
                            <div className="flex items-start justify-between gap-2">
                              <div className="line-clamp-2 text-xs font-semibold text-emerald-100">
                                {t.title}
                              </div>
                              <span className="shrink-0 rounded border border-emerald-400/40 bg-emerald-500/20 px-1.5 py-0.5 font-mono text-[9px] uppercase text-emerald-200">
                                {t.theory_type} ·{" "}
                                {(t.confidence * 100).toFixed(0)}%
                              </span>
                            </div>
                            <p className="mt-1 line-clamp-2 text-[11px] text-slate-300">
                              {t.description}
                            </p>
                            <div className="mt-2 flex items-center justify-between font-mono text-[10px] text-emerald-300/80">
                              <span>
                                {t.evidence_node_ids.length} evidence atoms
                              </span>
                              <span>v{t.graph_version}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* STAGE 3: ANTISYMMETRIC MERGES & CONSENSUS */}
              {showMergesCol && (
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between rounded-xl border border-cyan-500/30 bg-cyan-950/20 px-3 py-2 font-mono text-xs">
                    <span className="inline-flex items-center gap-2 font-semibold text-cyan-200">
                      <GitMerge size={13} className="text-cyan-400" />
                      STAGE 3 · ANTISYMMETRIC MERGES
                    </span>
                    <span className="text-[10px] text-cyan-300">
                      {visibleMerges.length} /{" "}
                      {data?.mergeCount ?? visibleMerges.length}
                    </span>
                  </div>

                  {visibleMerges.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-cyan-500/25 bg-cyan-950/10 p-4 font-mono text-[11px] text-slate-400">
                      No antisymmetric merges recorded yet.
                    </div>
                  ) : (
                    visibleMerges.map((merge) => {
                      const domKey = `merge:${merge.id}`;
                      const isDimmed =
                        highlightedKeys !== null &&
                        !highlightedKeys.has(domKey);
                      const isSelected =
                        inspector?.kind === "node" &&
                        inspector.node.id === merge.id;
                      const simPct = Math.round(
                        (merge.decision?.similarity ?? 0) * 100,
                      );
                      const isPruned = merge.status === "pruned";
                      return (
                        <div
                          key={merge.id}
                          ref={registerCardRef(domKey)}
                          data-card
                          onMouseEnter={() => setHoveredKey(domKey)}
                          onMouseLeave={() => setHoveredKey(null)}
                          onClick={() =>
                            setInspector({ kind: "node", node: merge })
                          }
                          className={`relative cursor-pointer rounded-xl border p-3 backdrop-blur-md transition-all ${
                            isSelected
                              ? "border-cyan-400 bg-cyan-950/40 shadow-[0_0_20px_rgba(56,189,248,0.22)]"
                              : isPruned
                                ? "border-rose-500/30 bg-[#140a14]/85 hover:border-rose-400/60"
                                : "border-cyan-500/25 bg-[#07111d]/85 hover:border-cyan-400/60"
                          } ${isDimmed ? "opacity-30" : "opacity-100"}`}
                        >
                          <span className="absolute -left-1.5 top-1/2 h-3 w-3 -translate-y-1/2 rounded-full border border-[#03060f] bg-cyan-400 shadow-[0_0_8px_#38bdf8]" />
                          <div className="flex items-start justify-between gap-2">
                            <div className="line-clamp-2 text-xs font-medium text-slate-100">
                              {merge.title}
                            </div>
                            <span
                              className={`inline-flex shrink-0 items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase ${
                                isPruned
                                  ? "border-rose-500/40 bg-rose-500/15 text-rose-300"
                                  : "border-cyan-500/40 bg-cyan-500/15 text-cyan-200"
                              }`}
                            >
                              {isPruned ? (
                                <Scissors size={9} />
                              ) : (
                                <CheckCircle2 size={9} />
                              )}
                              {merge.status || "winner"}
                            </span>
                          </div>

                          <div className="mt-2 font-mono text-[10px] text-slate-400">
                            {merge.subtitle}
                          </div>

                          {merge.decision && (
                            <div className="mt-2">
                              <div className="flex items-center justify-between font-mono text-[10px]">
                                <span className="truncate text-cyan-300">
                                  {merge.decision.reason}
                                </span>
                                <span className="shrink-0 text-slate-200">
                                  {simPct}%
                                </span>
                              </div>
                              <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-white/10">
                                <div
                                  className={`h-full rounded-full ${
                                    isPruned ? "bg-rose-400" : "bg-cyan-400"
                                  }`}
                                  style={{
                                    width: `${Math.min(100, Math.max(4, simPct))}%`,
                                  }}
                                />
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Interactive Inspector Drawer */}
      {inspector && (
        <div className="border-t border-white/10 bg-[#050915]/95 p-4 backdrop-blur-xl">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              {inspector.kind === "node" ? (
                <>
                  <div className="flex flex-wrap items-center gap-2 font-mono text-[10px] uppercase">
                    <span className="rounded border border-purple-400/40 bg-purple-500/20 px-2 py-0.5 text-purple-200">
                      {inspector.node.stage}
                    </span>
                    <span
                      className={`rounded border px-2 py-0.5 ${cogBadgeStyle(
                        inspector.node.cognitiveType,
                      )}`}
                    >
                      {inspector.node.cognitiveType}
                    </span>
                    <span className="text-slate-400">{inspector.node.id}</span>
                    {inspector.node.pressureLambda != null && (
                      <span className="text-amber-300">
                        λ={inspector.node.pressureLambda.toFixed(4)}
                      </span>
                    )}
                    {inspector.node.residual != null && (
                      <span className="text-cyan-300">
                        residual={inspector.node.residual.toFixed(4)}
                      </span>
                    )}
                  </div>
                  <h4 className="mt-1.5 text-sm font-semibold text-white">
                    {inspector.node.title}
                  </h4>
                  <p className="mt-1 text-xs text-slate-300">
                    {inspector.node.summary || inspector.node.subtitle}
                  </p>

                  {inspector.node.childrenDetails &&
                    inspector.node.childrenDetails.length > 0 && (
                      <div className="mt-3">
                        <div className="mb-1.5 font-mono text-[10px] uppercase tracking-wider text-purple-300">
                          CFP Constituent Lineage (
                          {inspector.node.childrenDetails.length})
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                          {inspector.node.childrenDetails.map((child) => (
                            <div
                              key={child.id}
                              className="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-xs"
                            >
                              <div className="min-w-0">
                                <div className="truncate text-slate-200">
                                  {child.label}
                                </div>
                                <div className="font-mono text-[9px] text-slate-500">
                                  {child.type} · {child.id.slice(0, 10)}
                                </div>
                              </div>
                              <span className="shrink-0 font-mono text-[10px] text-purple-300">
                                {(child.similarity * 100).toFixed(1)}%
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                  {inspector.node.decision && (
                    <div className="mt-3 flex flex-wrap items-center gap-3 rounded-lg border border-cyan-500/25 bg-cyan-950/20 px-3 py-2 font-mono text-[11px] text-cyan-200">
                      <Activity size={13} className="text-cyan-400" />
                      <span>Winner: {inspector.node.decision.winner}</span>
                      <ArrowRight size={12} className="text-slate-500" />
                      <span>Action: {inspector.node.decision.action}</span>
                      <span>
                        Similarity:{" "}
                        {(inspector.node.decision.similarity * 100).toFixed(1)}%
                      </span>
                      <span className="text-slate-300">
                        ({inspector.node.decision.reason})
                      </span>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="flex flex-wrap items-center gap-2 font-mono text-[10px] uppercase">
                    <span className="rounded border border-emerald-400/40 bg-emerald-500/20 px-2 py-0.5 text-emerald-200">
                      theory · {inspector.theory.theory_type}
                    </span>
                    <span className="text-emerald-300">
                      confidence{" "}
                      {(inspector.theory.confidence * 100).toFixed(1)}%
                    </span>
                    <span className="text-slate-400">
                      graph v{inspector.theory.graph_version}
                    </span>
                  </div>
                  <h4 className="mt-1.5 text-sm font-semibold text-white">
                    {inspector.theory.title}
                  </h4>
                  <p className="mt-1 text-xs text-slate-300">
                    {inspector.theory.description}
                  </p>
                  {inspector.theory.evidence_node_ids.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5 font-mono text-[10px]">
                      {inspector.theory.evidence_node_ids.map((eid) => (
                        <span
                          key={eid}
                          className="rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-emerald-200"
                        >
                          evidence: {eid.slice(0, 12)}
                        </span>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>

            <button
              type="button"
              onClick={() => setInspector(null)}
              className="rounded-lg border border-white/10 p-1.5 text-slate-400 hover:bg-white/10 hover:text-white"
              title="Close Inspector"
            >
              <X size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
