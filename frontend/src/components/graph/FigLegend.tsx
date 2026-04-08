"use client";

/**
 * FIG View — Legend + Filter Panel
 *
 * Visual legend for node states and edge kinds.
 * Provides client-side filter toggles for node kinds and edge kinds.
 *
 * IMPORTANT: Filters are client-side visibility controls only.
 * They never mutate backend truth or refetch from API.
 * Hidden kinds are passed back to FigCanvas to suppress rendering.
 *
 * scorecard fields (D, H, λ) are NOT shown — scorecard is always null in v1.
 */

import { edgeColorByKind, nodeColorByState } from "@/lib/figViewLayout";
import type { FigNodeDisplayState } from "@/types/figView";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FigLegendProps = {
  nodeKinds: string[];
  edgeKinds: string[];
  hiddenNodeKinds: Set<string>;
  hiddenEdgeKinds: Set<string>;
  onToggleNodeKind: (kind: string) => void;
  onToggleEdgeKind: (kind: string) => void;
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

// All known display states with their canonical colors
const NODE_STATES: { state: FigNodeDisplayState; label: string }[] = [
  { state: "active", label: "Active" },
  { state: "cold", label: "Cold" },
  { state: "historical", label: "Historical" },
  { state: "compressed", label: "Compressed" },
  { state: "deduplicated", label: "Deduplicated" },
  { state: "pruned", label: "Pruned" },
  { state: "deactivated", label: "Deactivated" },
  { state: "unknown", label: "Unknown" },
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function LegendSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-1.5 text-[9px] font-semibold uppercase tracking-widest text-slate-500">
        {title}
      </p>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function LegendRow({
  color,
  label,
  visible,
  onToggle,
  shape = "circle",
}: {
  color: string;
  label: string;
  visible: boolean;
  onToggle: () => void;
  shape?: "circle" | "line";
}) {
  return (
    <button
      onClick={onToggle}
      className={`flex w-full items-center gap-2.5 rounded-md px-2 py-1 text-left text-[11px] transition-all hover:bg-slate-800/50 ${
        visible ? "opacity-100" : "opacity-35"
      }`}
    >
      {/* Color indicator */}
      {shape === "circle" ? (
        <span
          className="h-2.5 w-2.5 rounded-full shrink-0 transition-opacity"
          style={{ backgroundColor: color }}
        />
      ) : (
        <span
          className="h-px w-5 shrink-0 transition-opacity"
          style={{ backgroundColor: color, height: 2, borderRadius: 1 }}
        />
      )}
      <span
        className={`flex-1 transition-colors ${
          visible ? "text-slate-200" : "text-slate-600 line-through"
        }`}
      >
        {label}
      </span>
      {/* Toggle indicator */}
      <span
        className={`h-3 w-3 rounded-full border transition-all shrink-0 ${
          visible
            ? "border-slate-500 bg-slate-500"
            : "border-slate-700 bg-transparent"
        }`}
      />
    </button>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function FigLegend({
  nodeKinds,
  edgeKinds,
  hiddenNodeKinds,
  hiddenEdgeKinds,
  onToggleNodeKind,
  onToggleEdgeKind,
}: FigLegendProps) {
  return (
    <div className="flex flex-col gap-4 text-xs">

      {/* ================================================================
          NODE STATES — visual reference only (not filterable by state)
      ================================================================ */}
      <LegendSection title="Node States">
        {NODE_STATES.map(({ state, label }) => (
          <div key={state} className="flex items-center gap-2.5 px-2 py-0.5">
            <span
              className="h-2.5 w-2.5 rounded-full shrink-0"
              style={{ backgroundColor: nodeColorByState(state, false) }}
            />
            <span className="text-[11px] text-slate-400">{label}</span>
          </div>
        ))}
      </LegendSection>

      <div className="h-px bg-slate-800/60" />

      {/* ================================================================
          NODE KIND FILTERS — client-side visibility toggles
      ================================================================ */}
      {nodeKinds.length > 0 && (
        <LegendSection title="Node Kinds (click to hide/show)">
          {nodeKinds.map((kind) => (
            <LegendRow
              key={kind}
              color="#64748b"
              label={kind}
              visible={!hiddenNodeKinds.has(kind)}
              onToggle={() => onToggleNodeKind(kind)}
              shape="circle"
            />
          ))}
        </LegendSection>
      )}

      {nodeKinds.length > 0 && edgeKinds.length > 0 && (
        <div className="h-px bg-slate-800/60" />
      )}

      {/* ================================================================
          EDGE KIND FILTERS — client-side visibility toggles
      ================================================================ */}
      {edgeKinds.length > 0 && (
        <LegendSection title="Edge Kinds (click to hide/show)">
          {edgeKinds.map((kind) => (
            <LegendRow
              key={kind}
              color={edgeColorByKind(kind)}
              label={kind}
              visible={!hiddenEdgeKinds.has(kind)}
              onToggle={() => onToggleEdgeKind(kind)}
              shape="line"
            />
          ))}
        </LegendSection>
      )}

      {/* ================================================================
          SCORECARD NOTE — scorecard is null in v1, show N/A clearly
      ================================================================ */}
      <div className="h-px bg-slate-800/60" />
      <div className="rounded-lg border border-slate-800/60 bg-slate-900/30 px-3 py-2">
        <p className="text-[9px] font-semibold uppercase tracking-widest text-slate-500 mb-1.5">
          Graph Scorecard
        </p>
        <div className="grid grid-cols-3 gap-2 text-center">
          {[
            { key: "D", label: "Density" },
            { key: "H", label: "Entropy" },
            { key: "λ", label: "Lambda" },
          ].map(({ key, label }) => (
            <div key={key} className="rounded bg-slate-900/40 border border-slate-800/50 px-1.5 py-1">
              <p className="font-mono text-[13px] font-bold text-slate-600">N/A</p>
              <p className="text-[8px] text-slate-700">{key} — {label}</p>
            </div>
          ))}
        </div>
        <p className="mt-1.5 text-[9px] text-slate-700 italic">
          Scorecard metrics not available in v1.
        </p>
      </div>

    </div>
  );
}
