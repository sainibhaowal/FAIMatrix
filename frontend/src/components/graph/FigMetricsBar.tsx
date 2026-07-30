"use client";

/**
 * FIG View — Metrics Bar with Dual Scorecard
 *
 * Compact bar displaying graph-level metrics from topology.
 * Scorecard (D, H, λ) computed client-side from graph data:
 *   - D (Density): edges / (nodes × (nodes-1))
 *   - H (Entropy): Shannon entropy of edge kinds
 *   - λ (Spectral Radius): largest eigenvalue via power iteration
 *
 * DUAL MODE (toggle):
 *   - Full Graph: Shows metrics for entire unfiltered graph
 *   - Current View: Shows metrics for filtered view (based on hidden kinds)
 *
 * Displays:
 *   - Node count (updates per mode)
 *   - Edge count (updates per mode)
 *   - Opposition/Inheritance breakdown
 *   - [Toggle Box] "Full Graph" ↔ "Current View"
 *   - D, H, λ — REAL COMPUTED VALUES (updates per mode)
 *   - Snapshot version + consistency flag
 */

import { Activity, GitBranch, Layers, Network } from "lucide-react";
import { useMemo, useState } from "react";

import {
  computeScorecard,
  type FigScorecard,
} from "@/lib/figViewGraphTransform";
import type {
  FigBackendScorecard,
  FigEdge,
  FigNode,
  FigSnapshot,
  FigTopology,
} from "@/types/figView";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FigMetricsBarProps = {
  topology: FigTopology | null;
  snapshot: FigSnapshot | null;
  nodeCount: number;
  edgeCount: number;
  nodes?: FigNode[];
  edges?: FigEdge[];
  // Filtered view (based on hidden kinds)
  filteredNodeCount?: number;
  filteredEdgeCount?: number;
  filteredNodes?: FigNode[];
  filteredEdges?: FigEdge[];
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function MetricCell({
  icon,
  value,
  label,
  sub,
  dimmed,
}: {
  icon?: React.ReactNode;
  value: string | number;
  label: string;
  sub?: string;
  dimmed?: boolean;
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-0.5 px-4 py-2 min-w-[72px] ${
        dimmed ? "opacity-40" : ""
      }`}
    >
      {icon && <div className="mb-0.5">{icon}</div>}
      <span className="font-mono text-[14px] font-bold leading-none text-slate-100">
        {value}
      </span>
      <span className="text-[8px] uppercase tracking-widest text-slate-500 mt-0.5">
        {label}
      </span>
      {sub && (
        <span className="text-[8px] text-slate-600 font-mono">{sub}</span>
      )}
    </div>
  );
}

function Divider() {
  return <div className="w-px self-stretch bg-slate-700/40 my-1" />;
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function FigMetricsBar({
  topology,
  snapshot,
  nodeCount,
  edgeCount,
  nodes = [],
  edges = [],
  filteredNodeCount,
  filteredEdgeCount,
  filteredNodes,
  filteredEdges,
}: FigMetricsBarProps) {
  // Toggle between Full Graph and Current View
  const [metricsMode, setMetricsMode] = useState<"full" | "view">("full");

  const edgeKinds = topology?.edge_counts_by_kind ?? {};
  const oppCount = edgeKinds["opposition"] ?? edgeKinds["OPPOSITION"] ?? 0;
  const inhCount = edgeKinds["inheritance"] ?? edgeKinds["INHERITANCE"] ?? 0;

  const effectiveNodes = topology?.node_count ?? nodeCount;
  const effectiveEdges = topology?.edge_count ?? edgeCount;

  // Backend-provided scorecard (plan §11: authoritative source when available).
  // The backend embeds this only when cheaply available; otherwise null.
  const backendScorecard: FigBackendScorecard | null =
    topology?.scorecard ?? null;

  // Full-graph scorecard: prefer backend when provided, fall back to client-computed.
  // Client-computed is derived entirely from backend-authoritative node/edge data,
  // so it is correct — just not independently verified by the backend process.
  const fullScorecard = useMemo<FigScorecard | null>(() => {
    if (backendScorecard) return backendScorecard;
    if (nodes.length > 0) return computeScorecard(nodes, edges);
    return null;
  }, [backendScorecard, nodes, edges]);

  // Filtered-view scorecard: always client-computed (backend does not know about
  // client-side kind filters).
  const viewScorecard = useMemo<FigScorecard | null>(() => {
    if (filteredNodes && filteredNodes.length > 0 && filteredEdges) {
      return computeScorecard(filteredNodes, filteredEdges);
    }
    return null;
  }, [filteredNodes, filteredEdges]);

  // Select which scorecard to display based on mode
  const displayScorecard =
    metricsMode === "full" ? fullScorecard : viewScorecard;
  const displayNodeCount =
    metricsMode === "full"
      ? effectiveNodes
      : (filteredNodeCount ?? effectiveNodes);
  const displayEdgeCount =
    metricsMode === "full"
      ? effectiveEdges
      : (filteredEdgeCount ?? effectiveEdges);

  // Source label: "backend" when the backend provided the scorecard and we are
  // showing full-graph mode; "computed" otherwise (client-derived from backend data).
  const scorecardSource: "backend" | "computed" =
    metricsMode === "full" && backendScorecard !== null
      ? "backend"
      : "computed";

  return (
    <div className="flex items-stretch rounded-xl border border-slate-700/50 bg-slate-950/85 backdrop-blur-md shadow-[0_4px_20px_rgba(0,0,0,0.4)] overflow-hidden divide-x divide-slate-700/30">
      {/* Nodes — updates per mode */}
      <MetricCell
        icon={
          <Network
            size={11}
            className={
              metricsMode === "view" ? "text-cyan-400" : "text-slate-500"
            }
          />
        }
        value={displayNodeCount}
        label="Nodes"
      />

      <Divider />

      {/* Edges — updates per mode */}
      <MetricCell
        icon={
          <GitBranch
            size={11}
            className={
              metricsMode === "view" ? "text-cyan-400" : "text-slate-500"
            }
          />
        }
        value={displayEdgeCount}
        label="Edges"
      />

      <Divider />

      {/* Opposition edges */}
      <MetricCell
        icon={<Layers size={11} className="text-amber-400" />}
        value={oppCount}
        label="Opposition"
      />

      <Divider />

      {/* Inheritance edges */}
      <MetricCell
        icon={<Activity size={11} className="text-emerald-400" />}
        value={inhCount}
        label="Inheritance"
      />

      <Divider />

      {/* TOGGLE BOX — Full Graph ↔ Current View */}
      <button
        onClick={() => setMetricsMode(metricsMode === "full" ? "view" : "full")}
        className={`flex flex-col items-center justify-center gap-0.5 px-3 py-2 min-w-[80px] transition-all duration-150 ${
          metricsMode === "view"
            ? "bg-cyan-950/30 border-l border-r border-cyan-500/30"
            : "hover:bg-slate-800/40"
        }`}
        title="Toggle between Full Graph and Current View"
      >
        <span
          className={`text-[11px] font-semibold transition-colors ${
            metricsMode === "view" ? "text-cyan-300" : "text-slate-400"
          }`}
        >
          {metricsMode === "full" ? "Full Graph" : "Current View"}
        </span>
        <span
          className={`text-[9px] ${metricsMode === "view" ? "text-cyan-600" : "text-slate-600"}`}
        >
          ↕
        </span>
      </button>

      <Divider />

      {/* ================================================================
          SCORECARD — D, H, λ
          Source: backend scorecard when provided (plan §11 authoritative);
          client-computed fallback when backend returns null.
      ================================================================ */}
      <div
        className="flex items-stretch gap-0 divide-x divide-slate-700/30"
        title={
          scorecardSource === "backend"
            ? "D/H/λ sourced from backend scorecard (authoritative)"
            : "D/H/λ computed client-side from backend-authoritative node/edge data"
        }
      >
        {[
          {
            key: "D",
            value: displayScorecard?.density ?? 0,
            healthColor: (v: number) =>
              v >= 0.15 ? "#22d3ee" : v >= 0.05 ? "#fbbf24" : "#64748b",
            healthHint: (v: number) =>
              v >= 0.15 ? "dense" : v >= 0.05 ? "sparse" : "disconnected",
          },
          {
            key: "H",
            value: displayScorecard?.entropy ?? 0,
            healthColor: (v: number) =>
              v >= 0.8 ? "#a78bfa" : v >= 0.3 ? "#fbbf24" : "#64748b",
            healthHint: (v: number) =>
              v >= 0.8 ? "diverse" : v >= 0.3 ? "moderate" : "uniform",
          },
          {
            key: "λ",
            value: displayScorecard?.spectral_radius ?? 0,
            healthColor: (v: number) =>
              v >= 2.0 ? "#34d399" : v >= 0.5 ? "#fbbf24" : "#64748b",
            healthHint: (v: number) =>
              v >= 2.0 ? "clustered" : v >= 0.5 ? "moderate" : "sparse",
          },
        ].map(({ key, value, healthColor, healthHint }) => {
          const valColor =
            metricsMode === "view" ? "#22d3ee" : healthColor(value);
          return (
            <div
              key={key}
              className={`flex flex-col items-center justify-center gap-0.5 px-4 py-2 min-w-[72px] transition-colors ${
                metricsMode === "view" ? "bg-cyan-950/10" : ""
              }`}
            >
              <span
                className="font-mono text-[14px] font-bold leading-none transition-colors"
                style={{ color: valColor }}
              >
                {typeof value === "number" && value > 0
                  ? value.toFixed(2)
                  : value === 0
                    ? "0"
                    : "—"}
              </span>
              <span className="text-[8px] uppercase tracking-widest text-slate-500 mt-0.5">
                {key}
              </span>
              <span
                className="text-[7px] font-mono"
                style={{ color: valColor, opacity: 0.7 }}
              >
                {healthHint(value)}
              </span>
            </div>
          );
        })}
        {/* Source badge */}
        <div className="flex flex-col items-center justify-end px-2 py-2">
          <span
            className={`text-[7px] font-mono uppercase tracking-widest ${
              scorecardSource === "backend"
                ? "text-emerald-600"
                : "text-slate-700"
            }`}
          >
            {scorecardSource}
          </span>
        </div>
      </div>

      {/* ================================================================
          SNAPSHOT VERSION + consistency
      ================================================================ */}
      {snapshot && (
        <>
          <Divider />
          <div className="flex flex-col items-center justify-center px-3 py-2 gap-0.5 min-w-[60px]">
            <span className="font-mono text-[11px] text-slate-400">
              v{snapshot.graph_version}
            </span>
            <span
              className={`text-[8px] uppercase tracking-widest ${
                snapshot.consistent_read ? "text-emerald-600" : "text-amber-600"
              }`}
            >
              {snapshot.consistent_read ? "consistent" : "eventual"}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
