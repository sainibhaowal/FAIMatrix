"use client";

/**
 * FIG View — Relation Explorer Panel
 *
 * Standalone "Explain Relation" drawer. Allows selecting two nodes and
 * calling the /paths/explain endpoint to visualise the connection path.
 *
 * Design decisions:
 *   - fromNode / toNode are independently selectable via a searchable drop-down
 *   - Results render inline — path hops with node titles, edge kinds, summary
 *   - scorecard fields (D, H, λ) are NOT shown — backend sets scorecard: null
 *   - Deep links follow contract §7 only
 *   - No tenant_id in URLs
 */

import { useState, useMemo } from "react";

import { Badge, Spinner } from "@/components/ui";
import {
  buildSearchIndex,
  filterNodesBySearch,
} from "@/lib/figViewGraphTransform";
import { nodeColorByState } from "@/lib/figViewLayout";
import { nodeStateClass, safeNodeTitle } from "@/lib/figViewSafety";
import type {
  FigInteractionPulse,
  FigExplainResponse,
  FigNode,
  FigNodeDisplayState,
  FigQueryExplain,
} from "@/types/figView";
import FigPulseTrace from "./FigPulseTrace";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FigRelationPanelProps = {
  graphId: string;
  nodes: FigNode[];
  nodeIndex: Map<string, FigNode>;
  initialFromId?: string | null;
  initialToId?: string | null;
  onNavigateToNode: (nodeId: string) => void;
  onRequestExplain: (fromNodeId: string, toNodeId: string) => void;
  explainResult: FigExplainResponse | null;
  explainLoading: boolean;
  queryExplain?: FigQueryExplain | null;
  livePulse?: FigInteractionPulse | null;
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Compact node picker with fuzzy search */
function NodePicker({
  label,
  nodes,
  selectedId,
  onSelect,
  accentColor,
}: {
  label: string;
  nodes: FigNode[];
  selectedId: string | null;
  onSelect: (nodeId: string | null) => void;
  accentColor: "violet" | "cyan";
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  const searchIndex = useMemo(() => buildSearchIndex(nodes), [nodes]);
  const results = useMemo(() => {
    if (!query.trim()) return searchIndex.slice(0, 8);
    return filterNodesBySearch(searchIndex, query).slice(0, 8);
  }, [searchIndex, query]);

  const selectedNode = selectedId
    ? nodes.find((n) => n.node_id === selectedId)
    : null;
  const displayTitle = selectedNode
    ? safeNodeTitle(selectedNode)
    : "Select node…";

  const accent = accentColor === "violet" ? "violet" : "cyan";
  const borderActive =
    accent === "violet" ? "border-violet-400/50" : "border-cyan-400/50";
  const bgActive = accent === "violet" ? "bg-violet-500/10" : "bg-cyan-500/10";
  const textActive = accent === "violet" ? "text-violet-300" : "text-cyan-300";
  const dotColor = selectedNode
    ? nodeColorByState(
        nodeStateClass(selectedNode) as FigNodeDisplayState,
        false,
      )
    : "#475569";

  return (
    <div className="relative">
      <p className="mb-1 text-[9px] uppercase tracking-widest text-slate-500">
        {label}
      </p>
      <button
        onClick={() => setOpen((v) => !v)}
        className={`flex w-full items-center gap-2 rounded-lg border px-2.5 py-1.5 text-left text-xs transition-all ${
          selectedId
            ? `${borderActive} ${bgActive} ${textActive}`
            : "border-slate-700/60 bg-slate-900/40 text-slate-400 hover:border-slate-600"
        }`}
      >
        {selectedId && (
          <span
            className="h-2 w-2 rounded-full shrink-0"
            style={{ backgroundColor: dotColor }}
          />
        )}
        <span className="truncate flex-1">{displayTitle}</span>
        {selectedId && (
          <span
            role="button"
            onClick={(e) => {
              e.stopPropagation();
              onSelect(null);
              setQuery("");
            }}
            className="shrink-0 text-[10px] text-slate-500 hover:text-red-400 transition-colors"
          >
            ✕
          </span>
        )}
      </button>

      {open && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1 rounded-lg border border-slate-700/70 bg-slate-950/98 shadow-xl backdrop-blur-md">
          <div className="p-1.5">
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by title, kind, or ID…"
              className="w-full rounded-md bg-slate-900/80 border border-slate-700/60 px-2.5 py-1 text-[11px] text-slate-200 placeholder-slate-600 outline-none focus:border-slate-500"
            />
          </div>
          <div className="max-h-44 overflow-auto">
            {results.length === 0 ? (
              <p className="px-3 py-2 text-[10px] text-slate-600 text-center">
                No matches
              </p>
            ) : (
              results.map((entry) => {
                const n = nodes.find((node) => node.node_id === entry.node_id);
                const color = n
                  ? nodeColorByState(
                      nodeStateClass(n) as FigNodeDisplayState,
                      false,
                    )
                  : "#475569";
                return (
                  <button
                    key={entry.node_id}
                    onClick={() => {
                      onSelect(entry.node_id);
                      setOpen(false);
                      setQuery("");
                    }}
                    className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left text-[11px] hover:bg-slate-800/60 transition-colors"
                  >
                    <span
                      className="h-1.5 w-1.5 rounded-full shrink-0"
                      style={{ backgroundColor: color }}
                    />
                    <span className="truncate text-slate-200">
                      {entry.title}
                    </span>
                    <Badge size="sm" variant="outline">
                      {entry.kind}
                    </Badge>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Path display
// ---------------------------------------------------------------------------

function PathDisplay({
  result,
  nodeIndex,
  onNavigate,
  queryExplain,
  livePulse,
  focusNodeId,
}: {
  result: FigExplainResponse;
  nodeIndex: Map<string, FigNode>;
  onNavigate: (id: string) => void;
  queryExplain?: FigQueryExplain | null;
  livePulse?: FigInteractionPulse | null;
  focusNodeId?: string | null;
}) {
  if (!result.path_found) {
    return (
      <div className="rounded-lg border border-red-900/30 bg-red-950/20 px-3 py-2.5">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-red-400 shrink-0" />
          <span className="text-xs font-medium text-red-300">
            No path found
          </span>
        </div>
        <p className="mt-1 text-[10px] text-slate-500">
          {result.explanation.summary}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Summary */}
      <div className="rounded-lg border border-slate-800/60 bg-slate-900/40 px-3 py-2">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="h-2 w-2 rounded-full bg-emerald-400 shrink-0" />
          <span className="text-xs font-semibold text-slate-200">
            Path found
          </span>
        </div>
        <p className="text-[10px] text-slate-400 mb-1.5">
          {result.explanation.summary}
        </p>
        <div className="flex flex-wrap gap-1">
          <Badge size="sm" variant="outline">
            {result.explanation.hops} hop
            {result.explanation.hops !== 1 ? "s" : ""}
          </Badge>
          {result.explanation.edge_kinds_used.map((k) => (
            <Badge key={k} size="sm" variant="secondary">
              {k}
            </Badge>
          ))}
          {result.explanation.relation_distance != null && (
            <Badge size="sm" variant="outline">
              dist: {result.explanation.relation_distance}
            </Badge>
          )}
        </div>
      </div>

      <FigPulseTrace
        pulseTrace={result.pulse_trace}
        nodeIndex={nodeIndex}
        queryExplain={queryExplain}
        livePulse={livePulse}
        focusNodeId={focusNodeId}
        emptyText="This relation is grounded, but no pulse trace payload is attached."
      />

      {/* Path traces */}
      {result.paths.map((path, i) => (
        <div
          key={i}
          className="rounded-lg border border-slate-800/50 bg-slate-900/30 p-2"
        >
          <p className="mb-1.5 text-[9px] uppercase tracking-widest text-slate-600">
            Path {i + 1}
          </p>
          <div className="flex flex-wrap items-center gap-1">
            {path.node_ids.map((id, j) => {
              const n = nodeIndex.get(id);
              const label = n ? safeNodeTitle(n).slice(0, 14) : id.slice(0, 8);
              const color = n
                ? nodeColorByState(
                    nodeStateClass(n) as FigNodeDisplayState,
                    false,
                  )
                : "#475569";
              return (
                <span key={id} className="flex items-center gap-1">
                  <button
                    onClick={() => onNavigate(id)}
                    className="rounded-md border border-slate-700/60 bg-slate-900/60 px-1.5 py-0.5 text-[9px] font-mono text-slate-300 hover:text-cyan-300 hover:border-cyan-400/30 transition-all"
                    style={{ borderLeftColor: color, borderLeftWidth: 2 }}
                    title={n ? safeNodeTitle(n) : id}
                  >
                    {label}
                  </button>
                  {j < path.node_ids.length - 1 && (
                    <span className="text-[9px] text-slate-600">→</span>
                  )}
                </span>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function FigRelationPanel({
  nodes,
  nodeIndex,
  initialFromId,
  initialToId,
  onNavigateToNode,
  onRequestExplain,
  explainResult,
  explainLoading,
  queryExplain = null,
  livePulse = null,
}: FigRelationPanelProps) {
  const [fromId, setFromId] = useState<string | null>(initialFromId ?? null);
  const [toId, setToId] = useState<string | null>(initialToId ?? null);

  const canExplain = !!fromId && !!toId && fromId !== toId;

  return (
    <div className="flex flex-col gap-3 text-xs">
      {/* Header description */}
      <p className="text-[10px] text-slate-500 leading-relaxed">
        Select two nodes to find and explain the shortest path between them.
      </p>

      {/* Node pickers */}
      <div className="space-y-2.5">
        <NodePicker
          label="From node"
          nodes={nodes}
          selectedId={fromId}
          onSelect={setFromId}
          accentColor="violet"
        />
        {/* Visual connector */}
        <div className="flex items-center gap-2 pl-2">
          <div className="h-4 w-px bg-slate-700/60" />
          <span className="text-[9px] text-slate-600">path goes to</span>
        </div>
        <NodePicker
          label="To node"
          nodes={nodes}
          selectedId={toId}
          onSelect={setToId}
          accentColor="cyan"
        />
      </div>

      {/* Guard: same node selected */}
      {fromId && toId && fromId === toId && (
        <p className="text-[10px] text-amber-400 italic">
          From and To must be different nodes.
        </p>
      )}

      {/* Find path button */}
      <button
        onClick={() => canExplain && onRequestExplain(fromId!, toId!)}
        disabled={!canExplain || explainLoading}
        className="flex w-full items-center justify-center gap-2 rounded-lg border border-cyan-500/30 bg-cyan-950/30 px-3 py-2 text-[11px] font-medium text-cyan-300 hover:bg-cyan-950/50 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
      >
        {explainLoading ? (
          <>
            <Spinner size="sm" />
            <span>Explaining path…</span>
          </>
        ) : (
          "Find Connection"
        )}
      </button>

      {/* Results */}
      {explainResult && !explainLoading && (
      <PathDisplay
        result={explainResult}
        nodeIndex={nodeIndex}
        onNavigate={onNavigateToNode}
        queryExplain={queryExplain}
        livePulse={livePulse}
        focusNodeId={toId}
      />
      )}

      {/* Empty state hint */}
      {!explainResult && !explainLoading && canExplain && (
        <p className="text-center text-[10px] text-slate-600 italic">
          Click "Find Connection" to trace the path.
        </p>
      )}
    </div>
  );
}
