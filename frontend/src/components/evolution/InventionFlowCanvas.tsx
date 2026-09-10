"use client";

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  FileText,
  GitCompare,
  Layers,
  Loader2,
  RotateCcw,
  Search,
  Sparkles,
  Zap,
  ZoomIn,
  ZoomOut,
  X,
} from "lucide-react";
import { Badge, Button } from "@/components/ui";

export interface FlowChildDetail {
  id: string;
  label: string;
  type: string;
  similarity: number;
}

export interface MergeDecision {
  selector: string;
  score_winner: number;
  score_loser: number;
  tie_break?: string | null;
  components_winner?: Record<string, number>;
}

export interface FlowNodeData {
  id: string;
  stage: "atom" | "macro" | "merge";
  title: string;
  subtitle: string;
  cognitiveType: "fact" | "procedure" | "event" | "contradiction" | "work";
  pressureLambda?: number;
  childCount?: number;
  status?: "active" | "synthesized" | "pruned" | "winner";
  childrenDetails?: FlowChildDetail[];
  decision?: MergeDecision;
  recent?: boolean;
}

export interface InventionFlowStages {
  atoms: FlowNodeData[];
  macros: FlowNodeData[];
  merges: FlowNodeData[];
}

export interface InventionFlowData {
  graph_id: string;
  node_count: number;
  macro_count: number;
  merge_count: number;
  stages: InventionFlowStages;
  computed_at: string;
}

interface InventionFlowCanvasProps {
  graphId: string;
  data?: InventionFlowData | null;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

type StageFilter = "all" | "macro" | "atom" | "merge";
type CognitiveType = FlowNodeData["cognitiveType"];

const COGNITIVE_TYPES: CognitiveType[] = [
  "fact",
  "procedure",
  "event",
  "contradiction",
  "work",
];

const DECISION_COMPONENT_LABELS: Record<string, string> = {
  evidence: "Evidence",
  usage: "Usage",
  recency: "Recency",
  source: "Source",
  residual: "Residual",
};

const MAX_VISIBLE_ATOMS = 12;
const MAX_VISIBLE_MACROS = 6;
const MAX_VISIBLE_MERGES = 6;

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export const InventionFlowCanvas: React.FC<InventionFlowCanvasProps> = ({
  graphId,
  data,
  loading = false,
  error = null,
  onRetry,
}) => {
  const [activeStageFilter, setActiveStageFilter] =
    useState<StageFilter>("all");
  const [selectedNode, setSelectedNode] = useState<FlowNodeData | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [cognitiveType, setCognitiveType] = useState<CognitiveType | "all">(
    "all",
  );
  const [diffMode, setDiffMode] = useState(false);

  // Infinite Canvas Pan & Zoom Transform State
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const transformRef = useRef(transform);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const viewportRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    transformRef.current = transform;
  }, [transform]);

  // Handle Mouse Pan (Drag Canvas)
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if ((e.target as HTMLElement).closest(".flow-node-card")) return;
      setIsDragging(true);
      setDragStart({ x: e.clientX - transformRef.current.x, y: e.clientY - transformRef.current.y });
    },
    [],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging) return;
      setTransform((prev) => ({
        ...prev,
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      }));
    },
    [isDragging, dragStart],
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Native wheel listener with { passive: false } so preventDefault works
  // and zoom is anchored to the cursor position (production-safe).
  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = viewport.getBoundingClientRect();
      const t = transformRef.current;
      const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
      const nextScale = clamp(t.scale * zoomFactor, 0.5, 2.5);
      const k = nextScale / t.scale;
      const cursorX = e.clientX - rect.left;
      const cursorY = e.clientY - rect.top;
      setTransform({
        x: cursorX - (cursorX - t.x) * k,
        y: cursorY - (cursorY - t.y) * k,
        scale: nextScale,
      });
    };

    viewport.addEventListener("wheel", handleWheel, { passive: false });
    return () => viewport.removeEventListener("wheel", handleWheel);
  }, []);

  // Zoom Controls
  const zoomIn = useCallback(() => {
    setTransform((prev) => ({
      ...prev,
      scale: clamp(prev.scale * 1.15, 0.5, 2.5),
    }));
  }, []);

  const zoomOut = useCallback(() => {
    setTransform((prev) => ({
      ...prev,
      scale: clamp(prev.scale * 0.85, 0.5, 2.5),
    }));
  }, []);

  const resetView = useCallback(() => {
    setTransform({ x: 0, y: 0, scale: 1 });
  }, []);

  const stages = useMemo(
    () => data?.stages ?? { atoms: [], macros: [], merges: [] },
    [data?.stages],
  );

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
          !`${node.title} ${node.subtitle} ${node.id}`
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

  const atoms = useMemo(
    () => applyFilters(stages.atoms).slice(0, MAX_VISIBLE_ATOMS),
    [stages, applyFilters],
  );
  const macros = useMemo(
    () => applyFilters(stages.macros).slice(0, MAX_VISIBLE_MACROS),
    [stages, applyFilters],
  );
  const merges = useMemo(
    () => applyFilters(stages.merges).slice(0, MAX_VISIBLE_MERGES),
    [stages, applyFilters],
  );
  const recentCount = useMemo(
    () => [...stages.atoms, ...stages.macros, ...stages.merges].filter((n) => n.recent).length,
    [stages],
  );

  const isEmpty =
    !loading &&
    !error &&
    data != null &&
    stages.atoms.length === 0 &&
    stages.macros.length === 0 &&
    stages.merges.length === 0;

  const hasData = !loading && !error && data != null && !isEmpty;

  const hasFilteredData =
    hasData && (atoms.length > 0 || macros.length > 0 || merges.length > 0);

  const hasActiveFilters =
    searchQuery.trim() !== "" ||
    cognitiveType !== "all" ||
    diffMode;

  return (
    <div className="relative w-full overflow-hidden rounded-2xl border border-white/10 bg-[#050810] shadow-2xl">
      {/* Top Header Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 border-b border-white/6 bg-black/40 backdrop-blur-xl z-20 relative">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-purple-400 animate-pulse" />
          <span className="font-mono text-xs font-bold uppercase tracking-wider text-slate-200">
            Real Invention Pipeline — {graphId}
          </span>
          <Badge variant="secondary" size="xs">
            Pan & Zoom Active
          </Badge>
        </div>

        {/* Stage Filter Switches */}
        <div className="flex items-center gap-1 rounded-xl border border-white/8 bg-white/[0.03] p-1">
          {[
            ["all", "All Stages"],
            ["atom", `Atoms ${stages.atoms.length}`],
            ["macro", `Macros ${stages.macros.length}`],
            ["merge", `Merges ${stages.merges.length}`],
          ].map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setActiveStageFilter(key as StageFilter)}
              className={`rounded-lg px-2.5 py-1 text-xs font-mono transition-all ${
                activeStageFilter === key
                  ? "bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Search, Cognitive Type + Cycle Diff Toolbar */}
      {hasData && (
        <div className="flex flex-wrap items-center gap-2 px-4 py-2.5 border-b border-white/6 bg-black/20 backdrop-blur-xl z-20 relative">
          <div className="relative min-w-[180px] flex-1 max-w-xs">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search nodes…"
              className="w-full rounded-lg border border-white/8 bg-white/[0.03] py-1.5 pl-8 pr-8 text-xs font-mono text-slate-200 placeholder:text-slate-500 outline-none focus:border-purple-500/50"
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

          <div className="flex items-center gap-1 flex-wrap">
            <button
              type="button"
              onClick={() => setCognitiveType("all")}
              className={`rounded-lg px-2 py-1 text-[11px] font-mono transition-all ${
                cognitiveType === "all"
                  ? "bg-slate-500/20 text-slate-200 border border-slate-500/40"
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
                className={`rounded-lg px-2 py-1 text-[11px] font-mono transition-all ${
                  cognitiveType === type
                    ? "bg-purple-500/20 text-purple-300 border border-purple-500/40"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {type}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => setDiffMode((v) => !v)}
            className={`ml-auto flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-[11px] font-mono transition-all ${
              diffMode
                ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                : "text-slate-400 border border-white/8 hover:text-amber-200"
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
      )}

      {/* Floating Infinite Canvas Zoom Control Deck */}
      <div className="absolute bottom-4 left-4 z-20 flex items-center gap-1.5 rounded-xl border border-white/10 bg-black/70 p-1.5 backdrop-blur-xl shadow-2xl text-xs">
        <button
          type="button"
          onClick={zoomIn}
          className="rounded-lg p-1.5 text-slate-300 hover:bg-white/10 hover:text-white transition-all"
          title="Zoom In (+)"
        >
          <ZoomIn size={14} />
        </button>
        <button
          type="button"
          onClick={zoomOut}
          className="rounded-lg p-1.5 text-slate-300 hover:bg-white/10 hover:text-white transition-all"
          title="Zoom Out (-)"
        >
          <ZoomOut size={14} />
        </button>
        <button
          type="button"
          onClick={resetView}
          className="rounded-lg p-1.5 text-slate-300 hover:bg-white/10 hover:text-white transition-all"
          title="Center View"
        >
          <RotateCcw size={14} />
        </button>
        <span className="border-l border-white/10 pl-2 font-mono text-[11px] text-purple-300">
          {(transform.scale * 100).toFixed(0)}%
        </span>
      </div>

      {/* 2.5D Infinite Mind-Map Viewport Container */}
      <div
        ref={viewportRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className="relative h-[calc(100vh-285px)] min-h-[400px] max-h-[620px] w-full cursor-grab overflow-hidden active:cursor-grabbing bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px]"
      >
        {loading && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-[#050810]/80 backdrop-blur-sm">
            <Loader2 size={28} className="animate-spin text-purple-400" />
            <p className="font-mono text-xs uppercase tracking-widest text-slate-400">
              Loading live invention topology…
            </p>
          </div>
        )}

        {!loading && error && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-[#050810]/80 px-6 text-center">
            <AlertTriangle size={28} className="text-rose-400" />
            <p className="font-mono text-xs uppercase tracking-widest text-rose-300">
              Invention flow unavailable
            </p>
            <p className="max-w-md text-xs text-slate-400">{error}</p>
            {onRetry && (
              <Button size="sm" variant="secondary" onClick={onRetry}>
                Retry
              </Button>
            )}
          </div>
        )}

        {!loading && !error && isEmpty && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-[#050810]/80 px-6 text-center">
            <Layers size={28} className="text-slate-600" />
            <p className="font-mono text-xs uppercase tracking-widest text-slate-400">
              No invention pipeline yet
            </p>
            <p className="max-w-md text-xs text-slate-500">
              Ingest documents into this graph and run an evolution cycle —
              atoms, synthesized macros and opposition merges will appear here
              in real time.
            </p>
          </div>
        )}

        {!loading && !error && hasData && !hasFilteredData && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-[#050810]/80 px-6 text-center">
            <Search size={28} className="text-slate-600" />
            <p className="font-mono text-xs uppercase tracking-widest text-slate-400">
              No nodes match current filters
            </p>
            <button
              type="button"
              onClick={() => {
                setSearchQuery("");
                setCognitiveType("all");
                setDiffMode(false);
              }}
              className="rounded-lg border border-white/10 px-3 py-1.5 text-xs font-mono text-slate-300 hover:bg-white/5"
            >
              Clear filters
            </button>
          </div>
        )}

        {/* Transform Scale & Translation Wrapper */}
        {hasData && (
          <div
            style={{
              transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`,
              transformOrigin: "center center",
              transition: isDragging ? "none" : "transform 0.1s ease-out",
            }}
            className="relative min-h-[460px] w-full p-6 select-none"
          >
            {/* Responsive Flex Layout with Inline SVG Bridges */}
            <div className="flex flex-col lg:flex-row items-stretch justify-between gap-4 w-full relative z-10">
              {/* --- STAGE 1: RAW ATOM CHUNKS (LEFT) --- */}
              {(activeStageFilter === "all" || activeStageFilter === "atom") && (
                <div className="flex-1 space-y-4">
                  <div className="flex items-center justify-between pb-2 border-b border-white/6">
                    <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                      <FileText size={13} className="text-cyan-400" />
                      Stage 1: Document Atoms
                    </span>
                    <Badge variant="outline" size="xs">
                      {stages.atoms.length} chunks
                    </Badge>
                  </div>

                  {atoms.length === 0 && (
                    <p className="text-xs text-slate-500 italic">
                      No atom nodes in this graph yet.
                    </p>
                  )}

                  {atoms.map((node) => (
                    <motion.div
                      key={node.id}
                      whileHover={{ scale: 1.03, x: 4 }}
                      onClick={() => setSelectedNode(node)}
                      className={`flow-node-card cursor-pointer relative -skew-x-12 rounded-xl border border-white/10 bg-slate-900/90 p-3.5 shadow-lg transition-all hover:border-cyan-400/60 hover:bg-slate-800/90 hover:shadow-[0_0_20px_rgba(56,189,248,0.3)] ${
                        node.recent
                          ? "ring-2 ring-amber-400/70 shadow-[0_0_18px_rgba(251,191,36,0.2)]"
                          : ""
                      }`}
                    >
                      {node.recent && (
                        <span className="skew-x-12 absolute -top-1.5 right-2 rounded-full border border-amber-400/50 bg-amber-500/20 px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider text-amber-300">
                          changed
                        </span>
                      )}
                      <div className="skew-x-12 flex items-center justify-between gap-2">
                        <div className="min-w-0">
                          <p className="font-bold text-xs text-slate-100 truncate">
                            {node.title}
                          </p>
                          <p className="font-mono text-[10px] text-slate-400 truncate mt-0.5">
                            {node.subtitle}
                          </p>
                        </div>
                        <Badge variant="info" size="xs">
                          {node.cognitiveType}
                        </Badge>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}

              {/* Stage 1 ➔ Stage 2 SVG Connecting Arrow Bridge */}
              {activeStageFilter === "all" && (
                <div className="hidden lg:flex flex-col justify-center items-center w-12 self-center">
                  <svg width="48" height="260" viewBox="0 0 48 260" fill="none">
                    <defs>
                      <linearGradient id="purpleGlow" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#c084fc" stopOpacity="0.9" />
                        <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.9" />
                      </linearGradient>
                      <marker
                        id="arrowPurple"
                        markerWidth="8"
                        markerHeight="8"
                        refX="6"
                        refY="4"
                        orient="auto"
                      >
                        <path d="M0,1 L7,4 L0,7 Z" fill="#c084fc" />
                      </marker>
                    </defs>
                    {[
                      "M 0 35 C 24 35, 24 85, 48 85",
                      "M 0 100 C 24 100, 24 85, 48 85",
                      "M 0 165 C 24 165, 24 85, 48 85",
                      "M 0 230 C 24 230, 24 200, 48 200",
                    ].map((d) => (
                      <path
                        key={d}
                        d={d}
                        stroke="url(#purpleGlow)"
                        strokeWidth="2"
                        markerEnd="url(#arrowPurple)"
                      />
                    ))}
                  </svg>
                </div>
              )}

              {/* --- STAGE 2: INVENTED MACRO CONCEPTS (CENTER) --- */}
              {(activeStageFilter === "all" || activeStageFilter === "macro") && (
                <div className="flex-1 space-y-6">
                  <div className="flex items-center justify-between pb-2 border-b border-white/6">
                    <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-purple-300 flex items-center gap-1.5">
                      <Zap size={13} className="text-purple-400 animate-pulse" />
                      Stage 2: Self-Inventions
                    </span>
                    <Badge variant="secondary" size="xs">
                      {stages.macros.length} macros
                    </Badge>
                  </div>

                  {macros.length === 0 && (
                    <p className="text-xs text-slate-500 italic">
                      No synthesized macros yet — they appear when co-activation
                      patterns repeat under pressure.
                    </p>
                  )}

                  {macros.map((node) => (
                    <motion.div
                      key={node.id}
                      whileHover={{ scale: 1.04, y: -2 }}
                      onClick={() => setSelectedNode(node)}
                      className={`flow-node-card cursor-pointer relative -skew-x-12 rounded-2xl border-2 border-purple-500/60 bg-[linear-gradient(135deg,rgba(147,51,234,0.25),rgba(15,23,42,0.95))] p-4 shadow-[0_0_25px_rgba(168,85,247,0.25)] transition-all hover:border-purple-400 hover:shadow-[0_0_35px_rgba(168,85,247,0.5)] ${
                        node.recent
                          ? "ring-2 ring-amber-400/70"
                          : ""
                      }`}
                    >
                      {node.recent && (
                        <span className="skew-x-12 absolute -top-1.5 right-2 rounded-full border border-amber-400/50 bg-amber-500/20 px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider text-amber-300">
                          changed
                        </span>
                      )}
                      <div className="skew-x-12">
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-1.5">
                            <span className="h-2 w-2 rounded-full bg-purple-400 animate-ping" />
                            <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-purple-300">
                              Synthesis Macro
                            </span>
                          </div>
                          {node.pressureLambda != null && (
                            <Badge variant="secondary" size="xs">
                              λ = {node.pressureLambda.toFixed(2)}
                            </Badge>
                          )}
                        </div>

                        <p className="mt-2 font-bold text-sm text-slate-100">
                          {node.title}
                        </p>
                        <p className="mt-0.5 font-mono text-[11px] text-slate-400">
                          {node.subtitle}
                        </p>

                        <div className="mt-3 flex items-center justify-between border-t border-purple-500/20 pt-2 font-mono text-[10px]">
                          <span className="text-purple-200">
                            Constituents: {node.childCount ?? 0}
                          </span>
                          <span className="flex items-center gap-1 text-cyan-300 font-bold">
                            Inspect Concept <ChevronRight size={12} />
                          </span>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}

              {/* Stage 2 ➔ Stage 3 SVG Connecting Arrow Bridge */}
              {activeStageFilter === "all" && (
                <div className="hidden lg:flex flex-col justify-center items-center w-12 self-center">
                  <svg width="48" height="260" viewBox="0 0 48 260" fill="none">
                    <defs>
                      <marker
                        id="arrowSky"
                        markerWidth="8"
                        markerHeight="8"
                        refX="6"
                        refY="4"
                        orient="auto"
                      >
                        <path d="M0,1 L7,4 L0,7 Z" fill="#38bdf8" />
                      </marker>
                      <marker
                        id="arrowRose"
                        markerWidth="8"
                        markerHeight="8"
                        refX="6"
                        refY="4"
                        orient="auto"
                      >
                        <path d="M0,1 L7,4 L0,7 Z" fill="#f43f5e" />
                      </marker>
                    </defs>
                    <path
                      d="M 0 85 C 24 85, 24 60, 48 60"
                      stroke="#38bdf8"
                      strokeWidth="2"
                      markerEnd="url(#arrowSky)"
                    />
                    <path
                      d="M 0 85 C 24 85, 24 180, 48 180"
                      stroke="#f43f5e"
                      strokeWidth="2"
                      strokeDasharray="4 4"
                      markerEnd="url(#arrowRose)"
                    />
                  </svg>
                </div>
              )}

              {/* --- STAGE 3: MERGES & PRUNING (RIGHT) --- */}
              {(activeStageFilter === "all" || activeStageFilter === "merge") && (
                <div className="flex-1 space-y-6">
                  <div className="flex items-center justify-between pb-2 border-b border-white/6">
                    <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                      <CheckCircle2 size={13} className="text-emerald-400" />
                      Stage 3: Merges & Prunes
                    </span>
                    <Badge variant="outline" size="xs">
                      {stages.merges.length} actions
                    </Badge>
                  </div>

                  {merges.length === 0 && (
                    <p className="text-xs text-slate-500 italic">
                      No opposition merges recorded yet.
                    </p>
                  )}

                  {merges.map((node) => (
                    <motion.div
                      key={node.id}
                      whileHover={{ scale: 1.03, x: -4 }}
                      onClick={() => setSelectedNode(node)}
                      className={`flow-node-card cursor-pointer relative -skew-x-12 rounded-xl border p-3.5 shadow-lg transition-all ${
                        node.status === "winner"
                          ? "border-sky-500/50 bg-sky-950/70 hover:border-sky-400 hover:shadow-[0_0_20px_rgba(56,189,248,0.3)]"
                          : "border-rose-500/50 bg-rose-950/70 hover:border-rose-400 hover:shadow-[0_0_20px_rgba(244,63,94,0.3)]"
                      } ${
                        node.recent
                          ? "ring-2 ring-amber-400/70 shadow-[0_0_18px_rgba(251,191,36,0.2)]"
                          : ""
                      }`}
                    >
                      {node.recent && (
                        <span className="skew-x-12 absolute -top-1.5 right-2 rounded-full border border-amber-400/50 bg-amber-500/20 px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider text-amber-300">
                          changed
                        </span>
                      )}
                      <div className="skew-x-12 flex items-center justify-between gap-2">
                        <div>
                          <p className="font-bold text-xs text-slate-100">
                            {node.title}
                          </p>
                          <p className="font-mono text-[10px] text-slate-400 mt-0.5">
                            {node.subtitle}
                          </p>
                        </div>
                        <Badge
                          variant={node.status === "winner" ? "info" : "error"}
                          size="xs"
                        >
                          {node.status === "winner" ? "Consensus" : "Pruned"}
                        </Badge>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Slide-Over Node Detail Inspector Modal */}
      <AnimatePresence>
        {selectedNode && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="absolute top-4 right-4 z-30 w-80 rounded-2xl border border-purple-500/40 bg-[#0b1220]/98 p-4 shadow-2xl backdrop-blur-2xl text-xs text-slate-100"
          >
            <div className="flex items-center justify-between border-b border-white/10 pb-2.5">
              <div className="flex items-center gap-2">
                <Zap size={14} className="text-purple-400 animate-pulse" />
                <span className="font-bold text-purple-200 uppercase tracking-wider text-[11px]">
                  Invention Flow Inspector
                </span>
              </div>
              <button
                type="button"
                onClick={() => setSelectedNode(null)}
                className="rounded-lg p-1 text-slate-400 hover:bg-white/10 hover:text-white"
              >
                <X size={14} />
              </button>
            </div>

            <div className="mt-3 space-y-2">
              <p className="font-bold text-sm text-slate-100">
                {selectedNode.title}
              </p>
              <p className="font-mono text-[11px] text-slate-400">
                Stage:{" "}
                <span className="text-purple-300 uppercase">
                  {selectedNode.stage}
                </span>
                {selectedNode.status && (
                  <>
                    {" "}
                    ·{" "}
                    <span
                      className={
                        selectedNode.status === "pruned"
                          ? "text-rose-300"
                          : selectedNode.status === "winner"
                            ? "text-sky-300"
                            : "text-emerald-300"
                      }
                    >
                      {selectedNode.status}
                    </span>
                  </>
                )}
              </p>

              {selectedNode.pressureLambda != null && (
                <div className="grid grid-cols-2 gap-2 pt-1 text-[11px]">
                  <div className="rounded-xl border border-white/8 bg-white/[0.03] p-2">
                    <span className="text-slate-400">Pressure λ</span>
                    <p className="font-bold text-cyan-300 mt-0.5">
                      {selectedNode.pressureLambda.toFixed(4)}
                    </p>
                  </div>
                  <div className="rounded-xl border border-white/8 bg-white/[0.03] p-2">
                    <span className="text-slate-400">Children</span>
                    <p className="font-bold text-purple-300 mt-0.5">
                      {selectedNode.childCount ?? 0} Chunks
                    </p>
                  </div>
                </div>
              )}

              {selectedNode.decision && (
                <div className="mt-3 pt-2 border-t border-white/10">
                  <p className="font-mono text-[10px] font-bold uppercase tracking-wider text-cyan-300 mb-2">
                    Why this node won
                  </p>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-400">Selector</span>
                      <span
                        className={`font-mono ${
                          selectedNode.decision.selector === "semantic"
                            ? "text-emerald-300"
                            : "text-slate-300"
                        }`}
                      >
                        {selectedNode.decision.selector}
                        {selectedNode.decision.tie_break === "legacy_hash" &&
                          selectedNode.decision.selector === "semantic" && (
                            <span className="text-slate-500">
                              {" "}
                              · tie: hash
                            </span>
                          )}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-2">
                        <span className="text-slate-400">Winner</span>
                        <p className="font-bold text-emerald-300 mt-0.5">
                          {selectedNode.decision.score_winner.toFixed(4)}
                        </p>
                      </div>
                      <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-2">
                        <span className="text-slate-400">Loser</span>
                        <p className="font-bold text-rose-300 mt-0.5">
                          {selectedNode.decision.score_loser.toFixed(4)}
                        </p>
                      </div>
                    </div>
                    {Object.keys(selectedNode.decision.components_winner ?? {})
                      .length > 0 && (
                      <div className="space-y-1.5 pt-1">
                        {Object.entries(
                          selectedNode.decision.components_winner ?? {},
                        ).map(([key, value]) => (
                          <div key={key} className="flex items-center gap-2">
                            <span className="w-16 shrink-0 font-mono text-[10px] text-slate-400">
                              {DECISION_COMPONENT_LABELS[key] ?? key}
                            </span>
                            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/8">
                              <div
                                className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-purple-400"
                                style={{
                                  width: `${Math.min(100, Math.max(0, value * 100))}%`,
                                }}
                              />
                            </div>
                            <span className="w-12 shrink-0 text-right font-mono text-[10px] text-slate-300">
                              {value.toFixed(3)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {selectedNode.childrenDetails &&
                selectedNode.childrenDetails.length > 0 && (
                  <div className="mt-3 pt-2 border-t border-white/10">
                    <p className="font-mono text-[10px] font-bold uppercase tracking-wider text-purple-300 mb-2">
                      Constituent Child Vector Chunks
                    </p>
                    <div className="max-h-44 overflow-y-auto custom-scrollbar space-y-1.5 pr-1">
                      {selectedNode.childrenDetails.map((child) => (
                        <div
                          key={child.id}
                          className="rounded-lg border border-white/8 bg-white/[0.02] p-2 flex items-center justify-between gap-2"
                        >
                          <div className="min-w-0">
                            <p className="truncate text-slate-200 text-[11px] font-medium">
                              {child.label}
                            </p>
                            <span className="text-[10px] text-slate-400 font-mono">
                              {child.type}
                            </span>
                          </div>
                          <Badge variant="info" size="xs">
                            {(child.similarity * 100).toFixed(0)}%
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              <p className="pt-2 border-t border-white/10 font-mono text-[10px] text-slate-500">
                node {selectedNode.id}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
