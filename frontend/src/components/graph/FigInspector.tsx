"use client";

/**
 * FIG View — Node Inspector Panel
 *
 * Full-detail panel for a selected graph node. Answers:
 *   "What is this node and why is it here?"
 *
 * Sections:
 *   1. Header (title, kind, state, pin, nav)
 *   2. Identity (node_id, level, vector_hash, deep link)
 *   3. Provenance (raw_id, block_id, storage link)
 *   4. Metrics (touch_count, residual, last_access)
 *   5. Parents
 *   6. Children
 *   7. Opposition/Conflict
 *   8. Explain Relation (when pinned node differs from selected)
 *
 * Safety:
 *   - No v_native vectors, no auth tokens, no cross-tenant identifiers
 *   - Deep links use /dashboard/storage and /api/v1/node — safe per contract §7
 *   - All display values from backend only
 */

import { useEffect, useState } from "react";

import { Badge, Spinner } from "@/components/ui";
import {
  getBestEdgeToNeighbor,
  getChildIds,
  getOppositionEdges,
  getParentIds,
  getRelevantNeighborOrder,
  type AdjacencyMap,
} from "@/lib/figViewGraphTransform";
import { nodeColorByState } from "@/lib/figViewLayout";
import { nodeStateClass, safeNodeTitle } from "@/lib/figViewSafety";
import type {
  FigEdge,
  FigExplainResponse,
  FigNeighborhoodExpansion,
  FigNode,
  FigNodeDisplayState,
} from "@/types/figView";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FigInspectorProps = {
  node: FigNode;
  graphId: string;
  allEdges: FigEdge[];
  nodeIndex: Map<string, FigNode>;
  adj: AdjacencyMap;
  pinnedNodeId: string | null;
  onPinToggle: (nodeId: string) => void;
  onNavigateToNode: (nodeId: string) => void;
  onRequestExplain: (fromNodeId: string, toNodeId: string) => void;
  explainResult: FigExplainResponse | null;
  explainLoading: boolean;
  onExpandNeighborhood: (nodeId: string, depth: number) => void;
  neighborhoodLoading: boolean;
  neighborhoodExpansion: FigNeighborhoodExpansion | null;
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SectionHeader({
  title,
  open,
  onToggle,
}: {
  title: string;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      className="flex w-full items-center justify-between py-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-400 hover:text-slate-200 transition-colors"
    >
      <span>{title}</span>
      <span className="text-slate-600">{open ? "▲" : "▼"}</span>
    </button>
  );
}

function CopyableValue({ value, label }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <button
      onClick={handleCopy}
      title={`Copy ${label ?? "value"}`}
      className="flex items-center gap-1 font-mono text-[10px] text-slate-400 hover:text-cyan-300 transition-colors truncate max-w-full"
    >
      <span className="truncate">{value}</span>
      {copied && <span className="text-emerald-400 shrink-0">✓</span>}
    </button>
  );
}

function NodeRef({
  nodeId,
  nodeIndex,
  onNavigate,
}: {
  nodeId: string;
  nodeIndex: Map<string, FigNode>;
  onNavigate: (id: string) => void;
}) {
  const n = nodeIndex.get(nodeId);
  if (!n)
    return (
      <div className="flex items-center gap-2 rounded-md bg-slate-900/40 px-2 py-1.5 text-xs text-slate-500">
        <span className="font-mono">{nodeId.slice(0, 12)}…</span>
      </div>
    );
  const title = safeNodeTitle(n);
  const state = nodeStateClass(n) as FigNodeDisplayState;
  const color = nodeColorByState(state, false);
  return (
    <button
      onClick={() => onNavigate(nodeId)}
      className="flex w-full items-center justify-between gap-2 rounded-md bg-slate-900/40 border border-slate-800/60 px-2 py-1.5 text-xs hover:border-cyan-500/30 hover:bg-slate-900/70 transition-all"
    >
      <div className="flex items-center gap-2 min-w-0">
        <span
          className="h-2 w-2 rounded-full shrink-0"
          style={{ backgroundColor: color }}
        />
        <span className="truncate text-slate-200 font-medium">{title}</span>
        <Badge size="sm" variant="outline">
          {n.kind}
        </Badge>
      </div>
      <span className="text-[9px] text-slate-500 shrink-0">→</span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Lifecycle banner config — shown for terminal/notable states
// ---------------------------------------------------------------------------

const LIFECYCLE_BANNERS: Partial<
  Record<string, { title: string; desc: string; cls: string }>
> = {
  compressed: {
    title: "Compressed node",
    desc: "This node was merged into a macro node during summarization. Its content is represented by a higher-level ancestor.",
    cls: "border-blue-500/30 bg-blue-950/20 text-blue-300",
  },
  deduplicated: {
    title: "Deduplicated node",
    desc: "This node was detected as a near-duplicate and removed from active retrieval. Its canonical version is another node.",
    cls: "border-violet-500/30 bg-violet-950/20 text-violet-300",
  },
  pruned: {
    title: "Pruned node",
    desc: "This node was removed by the pruning policy. It is no longer returned in retrieval results.",
    cls: "border-red-500/30 bg-red-950/20 text-red-300",
  },
  deactivated: {
    title: "Deactivated node",
    desc: "This node was explicitly deactivated by an operator action.",
    cls: "border-slate-600/40 bg-slate-900/40 text-slate-400",
  },
};

// ---------------------------------------------------------------------------
// Memory signal helpers — pure, no React
// ---------------------------------------------------------------------------

function noveltyColor(r: number): string {
  return r >= 0.7 ? "#34d399" : r >= 0.3 ? "#fbbf24" : "#94a3b8";
}
function noveltyLabel(r: number): string {
  return r >= 0.7 ? "novel" : r >= 0.3 ? "moderate" : "low novelty";
}
function redundancyColor(tc: number): string {
  return tc <= 5 ? "#34d399" : tc <= 20 ? "#fbbf24" : "#f87171";
}
function redundancyLabel(tc: number): string {
  return tc <= 5 ? "low access" : tc <= 20 ? "medium access" : "high access";
}
function recencyDays(isoDate: string): number {
  return Math.floor((Date.now() - new Date(isoDate).getTime()) / 86_400_000);
}
function recencyColor(days: number): string {
  return days < 7 ? "#34d399" : days < 30 ? "#fbbf24" : "#94a3b8";
}
function recencyLabel(days: number): string {
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  return `${days}d ago`;
}

const COGNITIVE_COLORS: Record<string, string> = {
  fact: "#3b82f6",
  event: "#22c55e",
  procedure: "#f97316",
  prediction: "#eab308",
  contradiction: "#ef4444",
  source: "#f8fafc",
  work: "#a855f7",
  unknown: "#64748b",
};

// ---------------------------------------------------------------------------
// Long-term toggle sub-component
// ---------------------------------------------------------------------------

function LongTermToggle({ node, graphId }: { node: FigNode; graphId: string }) {
  const [longTerm, setLongTerm] = useState<boolean>(node.long_term ?? false);
  const [loading, setLoading] = useState(false);

  const toggle = async () => {
    setLoading(true);
    try {
      const next = !longTerm;
      const res = await fetch(
        `/api/v1/storage/graphs/${encodeURIComponent(graphId)}/nodes/${encodeURIComponent(node.node_id)}/long-term?long_term=${next}`,
        { method: "POST" },
      );
      if (res.ok) {
        setLongTerm(next);
      }
    } catch {
      // silent — user can retry
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="border-t border-slate-800/40 px-3 py-2 flex items-center justify-between gap-3">
      <div className="min-w-0">
        <p className="text-[9px] font-semibold uppercase tracking-widest text-slate-500">
          Long-term Memory
        </p>
        <p className="text-[9px] text-slate-600 mt-0.5 leading-tight">
          {longTerm
            ? "Protected from cold pruning"
            : "Eligible for cold pruning"}
        </p>
      </div>
      <button
        onClick={toggle}
        disabled={loading}
        className={`shrink-0 flex items-center gap-1.5 rounded-full px-3 py-1 text-[10px] font-semibold border transition-all ${
          longTerm
            ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
            : "border-slate-700 bg-slate-900/40 text-slate-500 hover:border-slate-600 hover:text-slate-400"
        }`}
      >
        {loading ? "…" : longTerm ? "♾ Protected" : "Set Long-term"}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function FigInspector({
  node,
  graphId,
  nodeIndex,
  adj,
  pinnedNodeId,
  onPinToggle,
  onNavigateToNode,
  onRequestExplain,
  explainResult,
  explainLoading,
  onExpandNeighborhood,
  neighborhoodLoading,
  neighborhoodExpansion,
}: FigInspectorProps) {
  const [sections, setSections] = useState<Record<string, boolean>>({
    identity: true,
    provenance: true,
    metrics: true,
    parents: true,
    children: false,
    opposition: true,
    neighborhood: false,
    explain: true,
  });
  const [neighborhoodDepth, setNeighborhoodDepth] = useState(1);
  const [showAllParents, setShowAllParents] = useState(false);
  const [showAllChildren, setShowAllChildren] = useState(false);
  // nav cursor — 0-based index into relevantOrder; resets on node change
  const [navIdx, setNavIdx] = useState(0);
  useEffect(() => {
    setNavIdx(0);
  }, [node.node_id]);

  const toggleSection = (key: string) =>
    setSections((prev) => ({ ...prev, [key]: !prev[key] }));

  const title = safeNodeTitle(node);
  const stateKey = nodeStateClass(node) as FigNodeDisplayState;
  const stateColor = nodeColorByState(stateKey, false);
  const isPinned = pinnedNodeId === node.node_id;

  const parentIds = getParentIds(node.node_id, adj);
  const childIds = getChildIds(node.node_id, adj);
  const oppositionEdges = getOppositionEdges(node.node_id, adj);
  const relevantOrder = getRelevantNeighborOrder(node.node_id, adj, nodeIndex);

  const shownParents = showAllParents ? parentIds : parentIds.slice(0, 5);
  const shownChildren = showAllChildren ? childIds : childIds.slice(0, 5);

  const pinnedNode = pinnedNodeId ? nodeIndex.get(pinnedNodeId) : null;
  const canExplain = pinnedNodeId && pinnedNodeId !== node.node_id;

  return (
    <div className="flex flex-col gap-0 text-xs">
      {/* ================================================================
          HEADER — title, state, pin, navigation
      ================================================================ */}
      <div className="mb-3 rounded-lg border border-slate-800/60 bg-slate-900/40 px-3 py-2.5">
        {/* Color strip */}
        <div
          className="mb-2 h-0.5 rounded-full"
          style={{ backgroundColor: stateColor }}
        />

        {/* Title + kind */}
        <div className="flex items-start justify-between gap-2">
          <p
            className="font-semibold text-slate-100 text-[13px] leading-tight truncate max-w-[200px]"
            title={title}
          >
            {title}
          </p>
          <button
            onClick={() => onPinToggle(node.node_id)}
            title={isPinned ? "Unpin node" : "Pin node for comparison"}
            className={`shrink-0 rounded-md px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-widest border transition-all ${
              isPinned
                ? "border-violet-400/50 bg-violet-500/20 text-violet-300"
                : "border-slate-700/60 text-slate-500 hover:border-cyan-400/30 hover:text-cyan-300"
            }`}
          >
            {isPinned ? "Pinned" : "Pin"}
          </button>
        </div>

        {/* Badges */}
        <div className="mt-1.5 flex flex-wrap gap-1">
          <Badge size="sm" variant="outline">
            {node.kind}
          </Badge>
          <span
            className="inline-flex items-center rounded-full px-2 py-0.5 text-[9px] font-semibold border"
            style={{ color: stateColor, borderColor: stateColor + "44" }}
          >
            {stateKey}
          </span>
          <Badge size="sm" variant="secondary">
            L{node.level}
          </Badge>
          {node.metrics?.temperature && (
            <span
              className="inline-flex items-center rounded-full px-2 py-0.5 text-[9px] font-semibold border"
              style={{
                color:
                  node.metrics.temperature === "hot"
                    ? "#f97316"
                    : node.metrics.temperature === "warm"
                      ? "#fbbf24"
                      : "#64748b",
                borderColor:
                  (node.metrics.temperature === "hot"
                    ? "#f97316"
                    : node.metrics.temperature === "warm"
                      ? "#fbbf24"
                      : "#64748b") + "44",
              }}
            >
              {node.metrics.temperature === "hot"
                ? "🔥 hot"
                : node.metrics.temperature === "warm"
                  ? "◆ warm"
                  : "❄ cold"}
            </span>
          )}
          {node.anchor?.block_type && (
            <Badge size="sm" variant="outline">
              {node.anchor.block_type}
            </Badge>
          )}
          {node.cluster_id != null && (
            <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[9px] font-semibold border border-violet-500/30 bg-violet-500/10 text-violet-400">
              cluster {node.cluster_id}
            </span>
          )}
          {node.long_term && (
            <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[9px] font-semibold border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
              ♾ long-term
            </span>
          )}
          {node.cognitive_type && (
            <span
              className="inline-flex items-center rounded-full px-2 py-0.5 text-[9px] font-semibold border"
              style={{
                color: COGNITIVE_COLORS[node.cognitive_type] || "#64748b",
                borderColor:
                  (COGNITIVE_COLORS[node.cognitive_type] || "#64748b") + "44",
                backgroundColor:
                  (COGNITIVE_COLORS[node.cognitive_type] || "#64748b") + "11",
              }}
            >
              🧠 {node.cognitive_type}
            </span>
          )}
        </div>

        {/* Relevant memory navigation — deterministic prev/next ordering */}
        {relevantOrder.length > 0 &&
          (() => {
            const clampedIdx = Math.min(navIdx, relevantOrder.length - 1);
            const targetId = relevantOrder[clampedIdx]!;
            const targetNode = nodeIndex.get(targetId);
            const edge = getBestEdgeToNeighbor(node.node_id, targetId, adj);
            const stateC = targetNode
              ? nodeColorByState(
                  nodeStateClass(targetNode) as FigNodeDisplayState,
                  false,
                )
              : "#64748b";
            return (
              <div className="mt-2 border-t border-slate-800/60 pt-2 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[9px] uppercase tracking-widest text-slate-500">
                    Relevant memories
                  </span>
                  <span className="text-[9px] text-slate-600">
                    {clampedIdx + 1} / {relevantOrder.length}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  {/* Prev */}
                  <button
                    onClick={() =>
                      setNavIdx(
                        clampedIdx <= 0
                          ? relevantOrder.length - 1
                          : clampedIdx - 1,
                      )
                    }
                    title="Previous relevant memory"
                    className="shrink-0 rounded px-1.5 py-1 text-[10px] border border-slate-700/60 text-slate-400 hover:text-cyan-300 hover:border-cyan-400/30 transition-all"
                  >
                    ←
                  </button>
                  {/* Node preview — clicking navigates */}
                  <button
                    onClick={() => targetNode && onNavigateToNode(targetId)}
                    disabled={!targetNode}
                    className="flex flex-1 min-w-0 items-center justify-between gap-1.5 rounded-md bg-slate-900/40 border border-slate-800/60 px-2 py-1 hover:border-cyan-500/30 hover:bg-slate-900/70 disabled:opacity-40 transition-all"
                  >
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span
                        className="h-1.5 w-1.5 rounded-full shrink-0"
                        style={{ backgroundColor: stateC }}
                      />
                      <span className="truncate text-[10px] font-medium text-slate-200">
                        {targetNode
                          ? safeNodeTitle(targetNode).slice(0, 22)
                          : targetId.slice(0, 12)}
                      </span>
                    </div>
                    {edge && (
                      <div className="flex items-center gap-1 shrink-0">
                        <span className="text-[8px] text-slate-600">
                          {edge.kind.slice(0, 3)}
                        </span>
                        <span className="font-mono text-[8px] text-slate-500">
                          {edge.weight.toFixed(2)}
                        </span>
                      </div>
                    )}
                  </button>
                  {/* Next */}
                  <button
                    onClick={() =>
                      setNavIdx(
                        clampedIdx >= relevantOrder.length - 1
                          ? 0
                          : clampedIdx + 1,
                      )
                    }
                    title="Next relevant memory"
                    className="shrink-0 rounded px-1.5 py-1 text-[10px] border border-slate-700/60 text-slate-400 hover:text-cyan-300 hover:border-cyan-400/30 transition-all"
                  >
                    →
                  </button>
                </div>
              </div>
            );
          })()}
      </div>

      {/* ================================================================
          LIFECYCLE BANNER — shown for compressed/deduplicated/pruned/deactivated
      ================================================================ */}
      {LIFECYCLE_BANNERS[stateKey] &&
        (() => {
          const b = LIFECYCLE_BANNERS[stateKey]!;
          return (
            <div className={`mb-3 rounded-lg border px-3 py-2 ${b.cls}`}>
              <p className="text-[10px] font-semibold">{b.title}</p>
              <p className="mt-0.5 text-[9px] opacity-75">{b.desc}</p>
            </div>
          );
        })()}

      {/* ================================================================
          IDENTITY
      ================================================================ */}
      <div className="border-t border-slate-800/40">
        <SectionHeader
          title="Identity"
          open={sections.identity}
          onToggle={() => toggleSection("identity")}
        />
        {sections.identity && (
          <div className="mb-3 space-y-1.5 pl-1">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">node_id</span>
              <CopyableValue value={node.node_id} label="node_id" />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">kind</span>
              <span className="font-mono text-slate-300">{node.kind}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">level</span>
              <span className="font-mono text-slate-300">{node.level}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">vector_hash</span>
              <span className="font-mono text-[9px] text-slate-500">
                {(node.vector_hash ?? "").slice(0, 12)}…
              </span>
            </div>
            {/* Safe deep link — node detail API per contract §7 */}
            <a
              href={`/api/v1/node/${node.node_id}?graph_id=${encodeURIComponent(graphId)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-[10px] text-cyan-600 hover:text-cyan-400 transition-colors"
            >
              <span>View node API</span>
              <span>↗</span>
            </a>
          </div>
        )}
      </div>

      {/* ================================================================
          PROVENANCE
      ================================================================ */}
      {(node.provenance?.raw_id || node.provenance?.block_id) && (
        <div className="border-t border-slate-800/40">
          <SectionHeader
            title="Provenance"
            open={sections.provenance}
            onToggle={() => toggleSection("provenance")}
          />
          {sections.provenance && (
            <div className="mb-3 space-y-1.5 pl-1">
              {node.provenance?.raw_id && (
                <div className="flex items-center justify-between gap-2">
                  <span className="text-slate-500 shrink-0">raw_id</span>
                  <CopyableValue
                    value={node.provenance.raw_id}
                    label="raw_id"
                  />
                </div>
              )}
              {node.provenance?.block_id && (
                <div className="flex items-center justify-between gap-2">
                  <span className="text-slate-500 shrink-0">block_id</span>
                  <CopyableValue
                    value={node.provenance.block_id}
                    label="block_id"
                  />
                </div>
              )}
              {/* Safe deep link to storage — per contract §7 */}
              {node.provenance?.raw_id && (
                <a
                  href={`/dashboard/storage`}
                  className="flex items-center gap-1 text-[10px] text-cyan-600 hover:text-cyan-400 transition-colors"
                  title="Open Storage page (filter manually by raw_id)"
                >
                  <span>Open Storage page</span>
                  <span>↗</span>
                </a>
              )}
            </div>
          )}
        </div>
      )}

      {/* ================================================================
          MEMORY SIGNALS — novelty, redundancy, recency
          Source: FigNode.metrics (always available when node has metrics)
          Energy / confidence / salience are not exposed per node — omitted.
      ================================================================ */}
      {node.metrics && (
        <div className="border-t border-slate-800/40">
          <SectionHeader
            title="Memory Signals"
            open={sections.metrics}
            onToggle={() => toggleSection("metrics")}
          />
          {sections.metrics && (
            <div className="mb-3 pl-1 space-y-1.5">
              {/* Novelty — from residual [0-1]: high = unique content, low = replicated */}
              {typeof node.metrics.residual === "number" &&
                (() => {
                  const r = node.metrics!.residual;
                  const c = noveltyColor(r);
                  return (
                    <div className="flex items-center justify-between rounded-lg bg-slate-900/40 border border-slate-800/60 px-2.5 py-2">
                      <div>
                        <p className="text-[9px] uppercase tracking-widest text-slate-500">
                          Novelty
                        </p>
                        <p className="mt-0.5 text-[9px] text-slate-600">
                          Uniqueness vs graph average
                        </p>
                      </div>
                      <div className="text-right">
                        <p
                          className="font-mono text-sm font-semibold"
                          style={{ color: c }}
                        >
                          {r.toFixed(2)}
                        </p>
                        <p className="text-[9px]" style={{ color: c }}>
                          {noveltyLabel(r)}
                        </p>
                      </div>
                    </div>
                  );
                })()}

              {/* Redundancy signal — from touch_count: high touches = frequently queried */}
              {(() => {
                const tc = node.metrics!.touch_count;
                const c = redundancyColor(tc);
                return (
                  <div className="flex items-center justify-between rounded-lg bg-slate-900/40 border border-slate-800/60 px-2.5 py-2">
                    <div>
                      <p className="text-[9px] uppercase tracking-widest text-slate-500">
                        Redundancy
                      </p>
                      <p className="mt-0.5 text-[9px] text-slate-600">
                        Query access frequency
                      </p>
                    </div>
                    <div className="text-right">
                      <p
                        className="font-mono text-sm font-semibold"
                        style={{ color: c }}
                      >
                        {tc}
                      </p>
                      <p className="text-[9px]" style={{ color: c }}>
                        {redundancyLabel(tc)}
                      </p>
                    </div>
                  </div>
                );
              })()}

              {/* Recency — from last_access datetime */}
              {(() => {
                const la = node.metrics!.last_access;
                if (!la)
                  return (
                    <div className="flex items-center justify-between rounded-lg bg-slate-900/40 border border-slate-800/60 px-2.5 py-2">
                      <div>
                        <p className="text-[9px] uppercase tracking-widest text-slate-500">
                          Recency
                        </p>
                        <p className="mt-0.5 text-[9px] text-slate-600">
                          Last query access
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-mono text-sm font-semibold text-slate-500">
                          —
                        </p>
                        <p className="text-[9px] text-slate-600">
                          never accessed
                        </p>
                      </div>
                    </div>
                  );
                const days = recencyDays(la);
                const c = recencyColor(days);
                return (
                  <div className="flex items-center justify-between rounded-lg bg-slate-900/40 border border-slate-800/60 px-2.5 py-2">
                    <div>
                      <p className="text-[9px] uppercase tracking-widest text-slate-500">
                        Recency
                      </p>
                      <p className="mt-0.5 text-[9px] text-slate-600">
                        Last query access
                      </p>
                    </div>
                    <div className="text-right">
                      <p
                        className="font-mono text-sm font-semibold"
                        style={{ color: c }}
                      >
                        {recencyLabel(days)}
                      </p>
                      <p className="text-[9px] text-slate-500">
                        {new Date(la).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}
        </div>
      )}

      {/* ================================================================
          STRUCTURE — anchor metadata: doc_type, block_type, page, section, etc.
      ================================================================ */}
      {node.anchor && Object.values(node.anchor).some((v) => v != null) && (
        <div className="border-t border-slate-800/40">
          <SectionHeader
            title="Structure"
            open={sections.structure ?? true}
            onToggle={() => toggleSection("structure")}
          />
          {(sections.structure ?? true) && (
            <div className="mb-3 pl-1 space-y-1">
              {[
                { label: "Doc Type", value: node.anchor.doc_type },
                { label: "Block Type", value: node.anchor.block_type },
                {
                  label: "Page",
                  value:
                    node.anchor.page != null ? `p.${node.anchor.page}` : null,
                },
                {
                  label: "Slide",
                  value:
                    node.anchor.slide != null
                      ? `slide ${node.anchor.slide}`
                      : null,
                },
                { label: "Sheet", value: node.anchor.sheet },
                { label: "Section", value: node.anchor.section },
                {
                  label: "Rows",
                  value:
                    node.anchor.row_start != null
                      ? `${node.anchor.row_start}–${node.anchor.row_end ?? node.anchor.row_start}`
                      : null,
                },
                {
                  label: "Chars",
                  value:
                    node.anchor.char_start != null
                      ? `${node.anchor.char_start}–${node.anchor.char_end ?? "?"}`
                      : null,
                },
              ]
                .filter((r) => r.value != null && r.value !== "")
                .map((r) => (
                  <div
                    key={r.label}
                    className="flex items-center justify-between py-1 border-b border-slate-800/40 last:border-0"
                  >
                    <span className="text-[9px] uppercase tracking-widest text-slate-500">
                      {r.label}
                    </span>
                    <span className="font-mono text-[10px] text-slate-300">
                      {String(r.value)}
                    </span>
                  </div>
                ))}
              {node.cluster_id != null && (
                <div className="flex items-center justify-between py-1 border-b border-slate-800/40">
                  <span className="text-[9px] uppercase tracking-widest text-slate-500">
                    Cluster
                  </span>
                  <span className="font-mono text-[10px] text-violet-400">
                    #{node.cluster_id}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ================================================================
          MEMORY CONTROLS — long-term flag toggle
      ================================================================ */}
      <LongTermToggle node={node} graphId={graphId} />

      {/* ================================================================
          PARENTS
      ================================================================ */}
      {parentIds.length > 0 && (
        <div className="border-t border-slate-800/40">
          <SectionHeader
            title={`Parents (${parentIds.length})`}
            open={sections.parents}
            onToggle={() => toggleSection("parents")}
          />
          {sections.parents && (
            <div className="mb-3 flex flex-col gap-1 pl-1">
              {shownParents.map((id) => (
                <NodeRef
                  key={id}
                  nodeId={id}
                  nodeIndex={nodeIndex}
                  onNavigate={onNavigateToNode}
                />
              ))}
              {parentIds.length > 5 && (
                <button
                  onClick={() => setShowAllParents((v) => !v)}
                  className="text-[10px] text-slate-500 hover:text-cyan-400 transition-colors"
                >
                  {showAllParents
                    ? "Show less"
                    : `+${parentIds.length - 5} more`}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* ================================================================
          CHILDREN
      ================================================================ */}
      {childIds.length > 0 && (
        <div className="border-t border-slate-800/40">
          <SectionHeader
            title={`Children (${childIds.length})`}
            open={sections.children}
            onToggle={() => toggleSection("children")}
          />
          {sections.children && (
            <div className="mb-3 flex flex-col gap-1 pl-1">
              {shownChildren.map((id) => (
                <NodeRef
                  key={id}
                  nodeId={id}
                  nodeIndex={nodeIndex}
                  onNavigate={onNavigateToNode}
                />
              ))}
              {childIds.length > 5 && (
                <button
                  onClick={() => setShowAllChildren((v) => !v)}
                  className="text-[10px] text-slate-500 hover:text-cyan-400 transition-colors"
                >
                  {showAllChildren
                    ? "Show less"
                    : `+${childIds.length - 5} more`}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* ================================================================
          OPPOSITION / CONFLICT
      ================================================================ */}
      {oppositionEdges.length > 0 && (
        <div className="border-t border-slate-800/40">
          <SectionHeader
            title={`Conflicts/Opposition (${oppositionEdges.length})`}
            open={sections.opposition}
            onToggle={() => toggleSection("opposition")}
          />
          {sections.opposition && (
            <div className="mb-3 flex flex-col gap-1 pl-1">
              {oppositionEdges.map((edge) => {
                const otherId =
                  edge.src_node_id === node.node_id
                    ? edge.dst_node_id
                    : edge.src_node_id;
                return (
                  <div
                    key={edge.edge_id}
                    className="flex items-center justify-between gap-2 rounded-md bg-red-950/30 border border-red-900/30 px-2 py-1.5"
                  >
                    <button
                      onClick={() => onNavigateToNode(otherId)}
                      className="truncate text-red-300 hover:text-red-200 transition-colors text-left min-w-0"
                    >
                      {safeNodeTitle(
                        nodeIndex.get(otherId) ?? {
                          node_id: otherId,
                          kind: "?",
                          level: 0,
                          vector_hash: "",
                          display: {
                            title: otherId.slice(0, 8),
                            title_source: "node_id",
                            state: "unknown",
                          },
                        },
                      )}
                    </button>
                    <span className="shrink-0 text-[9px] font-mono text-red-500">
                      w:{edge.weight.toFixed(2)}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ================================================================
          NEIGHBORHOOD EXPANSION
      ================================================================ */}
      <div className="border-t border-slate-800/40">
        <SectionHeader
          title="Neighborhood"
          open={sections.neighborhood}
          onToggle={() => toggleSection("neighborhood")}
        />
        {sections.neighborhood && (
          <div className="mb-3 pl-1 space-y-2">
            <p className="text-[10px] text-slate-500">
              Expand the graph to include nodes reachable from here.
            </p>
            <div className="flex items-center gap-1.5">
              <span className="text-[9px] uppercase tracking-widest text-slate-500 shrink-0">
                Depth
              </span>
              {([1, 2, 3] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => setNeighborhoodDepth(d)}
                  className={`rounded px-2 py-0.5 text-[10px] font-mono border transition-colors ${
                    neighborhoodDepth === d
                      ? "border-cyan-500/40 bg-cyan-900/50 text-cyan-300"
                      : "border-slate-700/60 text-slate-400 hover:text-slate-200 hover:border-slate-600"
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
            <button
              onClick={() =>
                onExpandNeighborhood(node.node_id, neighborhoodDepth)
              }
              disabled={neighborhoodLoading}
              className="flex w-full items-center justify-center gap-2 rounded-md border border-emerald-500/30 bg-emerald-950/30 px-3 py-1.5 text-[11px] text-emerald-300 hover:bg-emerald-950/50 disabled:opacity-50 transition-all"
            >
              {neighborhoodLoading ? (
                <>
                  <Spinner size="sm" />
                  <span>Expanding…</span>
                </>
              ) : (
                "Expand Neighborhood"
              )}
            </button>
            {neighborhoodExpansion?.seedNodeId === node.node_id && (
              <div className="rounded-lg border border-emerald-800/40 bg-emerald-950/20 px-2.5 py-2 text-[10px] text-emerald-300 space-y-0.5">
                <div>
                  +{neighborhoodExpansion.addedNodeCount} node
                  {neighborhoodExpansion.addedNodeCount !== 1 ? "s" : ""} added
                </div>
                <div>
                  +{neighborhoodExpansion.addedEdgeCount} edge
                  {neighborhoodExpansion.addedEdgeCount !== 1 ? "s" : ""} added
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ================================================================
          EXPLAIN RELATION
      ================================================================ */}
      <div className="border-t border-slate-800/40">
        <SectionHeader
          title="Explain Relation"
          open={sections.explain}
          onToggle={() => toggleSection("explain")}
        />
        {sections.explain && (
          <div className="mb-3 pl-1">
            {!pinnedNodeId && (
              <p className="text-[10px] text-slate-500 italic">
                Pin a node first to explain the relation between it and this
                node.
              </p>
            )}
            {pinnedNodeId && pinnedNodeId === node.node_id && (
              <p className="text-[10px] text-slate-500 italic">
                Select a different node to explain the path from the pinned
                node.
              </p>
            )}
            {canExplain && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-[10px] text-slate-400">
                  <span className="text-violet-300 font-medium truncate max-w-[100px]">
                    {pinnedNode
                      ? safeNodeTitle(pinnedNode)
                      : pinnedNodeId!.slice(0, 8)}
                  </span>
                  <span>→</span>
                  <span className="text-cyan-300 font-medium truncate max-w-[100px]">
                    {title}
                  </span>
                </div>

                <button
                  onClick={() => onRequestExplain(pinnedNodeId!, node.node_id)}
                  disabled={explainLoading}
                  className="flex w-full items-center justify-center gap-2 rounded-md border border-cyan-500/30 bg-cyan-950/30 px-3 py-1.5 text-[11px] text-cyan-300 hover:bg-cyan-950/50 disabled:opacity-50 transition-all"
                >
                  {explainLoading ? (
                    <>
                      <Spinner size="sm" />
                      <span>Explaining…</span>
                    </>
                  ) : (
                    "Find Path"
                  )}
                </button>

                {explainResult && (
                  <div className="rounded-lg border border-slate-800/60 bg-slate-900/40 p-2.5 space-y-1.5">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`h-2 w-2 rounded-full ${explainResult.path_found ? "bg-emerald-400" : "bg-red-400"}`}
                      />
                      <span className="text-[10px] font-semibold text-slate-200">
                        {explainResult.path_found
                          ? "Path found"
                          : "No path found"}
                      </span>
                    </div>

                    {explainResult.path_found && (
                      <>
                        <p className="text-[10px] text-slate-400">
                          {explainResult.explanation.summary}
                        </p>
                        <div className="flex flex-wrap gap-1">
                          <Badge size="sm" variant="outline">
                            {explainResult.explanation.hops} hop
                            {explainResult.explanation.hops !== 1 ? "s" : ""}
                          </Badge>
                          {explainResult.explanation.edge_kinds_used.map(
                            (k) => (
                              <Badge key={k} size="sm" variant="secondary">
                                {k}
                              </Badge>
                            ),
                          )}
                          {explainResult.explanation.relation_distance !=
                            null && (
                            <Badge size="sm" variant="outline">
                              dist:{" "}
                              {explainResult.explanation.relation_distance}
                            </Badge>
                          )}
                        </div>
                        {explainResult.paths.map((path, i) => (
                          <div
                            key={i}
                            className="text-[9px] text-slate-500 font-mono"
                          >
                            {path.node_ids
                              .map((id) => {
                                const n = nodeIndex.get(id);
                                return n
                                  ? safeNodeTitle(n).slice(0, 10)
                                  : id.slice(0, 8);
                              })
                              .join(" → ")}
                          </div>
                        ))}
                      </>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
