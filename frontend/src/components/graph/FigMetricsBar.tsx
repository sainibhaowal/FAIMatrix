"use client";

/**
 * FIG View — Metrics Bar
 *
 * Compact bar displaying graph-level metrics from topology.
 * scorecard (D, H, λ) is ALWAYS shown as N/A — backend sets scorecard: null in v1.
 * This is correct and intentional — do not compute these client-side.
 *
 * Displays:
 *   - Node count + breakdown by state (active vs others)
 *   - Edge count + breakdown by kind
 *   - D, H, λ — all N/A
 *   - Snapshot version + consistency flag
 */

import { Activity, GitBranch, Layers, Network } from "lucide-react";

import type { FigSnapshot, FigTopology } from "@/types/figView";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FigMetricsBarProps = {
  topology: FigTopology | null;
  snapshot: FigSnapshot | null;
  nodeCount: number;
  edgeCount: number;
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
}: FigMetricsBarProps) {
  const edgeKinds = topology?.edge_counts_by_kind ?? {};
  const oppCount = edgeKinds["opposition"] ?? edgeKinds["OPPOSITION"] ?? 0;
  const inhCount = edgeKinds["inheritance"] ?? edgeKinds["INHERITANCE"] ?? 0;

  const effectiveNodes = topology?.node_count ?? nodeCount;
  const effectiveEdges = topology?.edge_count ?? edgeCount;

  return (
    <div className="flex items-stretch rounded-xl border border-slate-700/50 bg-slate-950/85 backdrop-blur-md shadow-[0_4px_20px_rgba(0,0,0,0.4)] overflow-hidden divide-x divide-slate-700/30">

      {/* Nodes */}
      <MetricCell
        icon={<Network size={11} className="text-cyan-400" />}
        value={effectiveNodes}
        label="Nodes"
      />

      <Divider />

      {/* Edges */}
      <MetricCell
        icon={<GitBranch size={11} className="text-violet-400" />}
        value={effectiveEdges}
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

      {/* ================================================================
          SCORECARD — all N/A per contract (scorecard: null in v1)
          NEVER compute these client-side.
      ================================================================ */}
      <div className="flex items-center gap-0 divide-x divide-slate-700/30">
        {[
          { key: "D", title: "Density" },
          { key: "H", title: "Entropy" },
          { key: "λ", title: "Lambda" },
        ].map(({ key, title }) => (
          <MetricCell
            key={key}
            value="N/A"
            label={key}
            sub={title}
            dimmed
          />
        ))}
      </div>

      {/* ================================================================
          SNAPSHOT VERSION + consistency
      ================================================================ */}
      {snapshot && (
        <>
          <Divider />
          <div className="flex flex-col items-center justify-center px-3 py-2 gap-0.5 min-w-[60px]">
            <span className="font-mono text-[11px] text-slate-400">v{snapshot.graph_version}</span>
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
