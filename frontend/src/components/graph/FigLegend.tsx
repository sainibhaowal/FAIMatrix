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
import { Badge } from "@/components/ui";
import type {
  FigInteractionPulse,
  FigNodeDisplayState,
  FigPulseTrace,
  FigQueryExplain,
} from "@/types/figView";

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
  overlayMode?: string;
  pulseTrace?: FigPulseTrace | null;
  queryExplain?: FigQueryExplain | null;
  livePulse?: FigInteractionPulse | null;
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

// All known display states with canonical colors and descriptions
const NODE_STATES: {
  state: FigNodeDisplayState;
  label: string;
  desc: string;
}[] = [
  {
    state: "active",
    label: "Active (Hot)",
    desc: "Accessed within 7 days — highest retrieval priority",
  },
  {
    state: "warm",
    label: "Warm",
    desc: "Accessed within 30 days — still in working memory",
  },
  {
    state: "cold",
    label: "Cold",
    desc: "Not accessed in 90+ days or zero touches — candidate for pruning",
  },
  {
    state: "historical",
    label: "Historical",
    desc: "Older contradicting fact (temporal suppression)",
  },
  {
    state: "compressed",
    label: "Compressed",
    desc: "Merged into a macro node (summarized)",
  },
  {
    state: "deduplicated",
    label: "Deduplicated",
    desc: "Detected as near-duplicate and removed",
  },
  {
    state: "pruned",
    label: "Pruned",
    desc: "Removed by pruning policy (terminal)",
  },
  {
    state: "deactivated",
    label: "Deactivated",
    desc: "Explicitly deactivated by operator",
  },
  { state: "unknown", label: "Unknown", desc: "State not yet determined" },
];

const COGNITIVE_STATES = [
  {
    type: "fact",
    label: "Fact",
    color: "#3b82f6",
    desc: "Declarative knowledge (what is)",
  },
  {
    type: "event",
    label: "Event",
    color: "#22c55e",
    desc: "Episodic experiences (what happened)",
  },
  {
    type: "procedure",
    label: "Procedure",
    color: "#f97316",
    desc: "Skills and workflows (how to)",
  },
  {
    type: "prediction",
    label: "Prediction",
    color: "#eab308",
    desc: "Hypotheses and forecasts (what might be)",
  },
  {
    type: "contradiction",
    label: "Contradiction",
    color: "#ef4444",
    desc: "Conflicts and uncertainty (what conflicts)",
  },
  {
    type: "source",
    label: "Source",
    color: "#f8fafc",
    desc: "Raw document reference (where from)",
  },
  {
    type: "work",
    label: "Work",
    color: "#a855f7",
    desc: "Professional/project context",
  },
  {
    type: "unknown",
    label: "Unknown",
    color: "#64748b",
    desc: "Unclassified memory fragment",
  },
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function LegendSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
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
  overlayMode = "none",
  pulseTrace = null,
  queryExplain = null,
  livePulse = null,
}: FigLegendProps) {
  return (
    <div className="flex flex-col gap-4 text-xs">
      {/* ================================================================
          NODE STATES — visual reference only (not filterable by state)
      ================================================================ */}
      <LegendSection title="Node States">
        {overlayMode === "cognitive"
          ? COGNITIVE_STATES.map(({ type, label, color, desc }) => (
              <div
                key={type}
                className="flex items-start gap-2.5 px-2 py-0.5"
                title={desc}
              >
                <span
                  className="h-2.5 w-2.5 rounded-full shrink-0 mt-0.5"
                  style={{ backgroundColor: color }}
                />
                <div className="min-w-0">
                  <span className="text-[11px] text-slate-400">{label}</span>
                  <p className="text-[8px] text-slate-600 leading-tight mt-0.5">
                    {desc}
                  </p>
                </div>
              </div>
            ))
          : NODE_STATES.map(({ state, label, desc }) => (
              <div
                key={state}
                className="flex items-start gap-2.5 px-2 py-0.5"
                title={desc}
              >
                <span
                  className="h-2.5 w-2.5 rounded-full shrink-0 mt-0.5"
                  style={{ backgroundColor: nodeColorByState(state, false) }}
                />
                <div className="min-w-0">
                  <span className="text-[11px] text-slate-400">{label}</span>
                  <p className="text-[8px] text-slate-600 leading-tight mt-0.5">
                    {desc}
                  </p>
                </div>
              </div>
            ))}
      </LegendSection>

      {pulseTrace && (
        <>
          <div className="h-px bg-slate-800/60" />
          <LegendSection title="Pulse Protocol">
            <div className="rounded-lg border border-cyan-500/15 bg-cyan-500/5 px-2 py-2 text-[10px] text-slate-300">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-cyan-300">
                  {pulseTrace.protocol}
                </span>
                <span className="font-mono text-slate-500">
                  {pulseTrace.path_length} hops
                </span>
              </div>
              <p className="mt-1 text-slate-400">
                Trace is backed by graph path, semantic signature, node
                metrics, and provenance evidence.
              </p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {Object.entries(pulseTrace.layer_summary || {})
                  .slice(0, 8)
                  .map(([layer, count]) => (
                    <Badge key={layer} size="sm" variant="outline">
                      {layer}: {count}
                    </Badge>
                  ))}
              </div>
            </div>
          </LegendSection>
        </>
      )}

      {queryExplain && (
        <>
          <div className="h-px bg-slate-800/60" />
          <LegendSection title="Query Reason Stack">
            <div className="rounded-lg border border-violet-500/15 bg-violet-500/5 px-2 py-2 text-[10px] text-slate-300">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-violet-300">
                  Overlay evidence
                </span>
                <span className="font-mono text-slate-500">
                  {queryExplain.query_fusion_summary?.top_result?.active_layers?.length ??
                    queryExplain.fusion_summary?.active_layers?.length ??
                    0} layers
                </span>
              </div>
              <p className="mt-1 text-slate-400">
                The selected node is backed by weighted expansion, domain
                memory, graph score, reranking, and late interaction signals
                when present.
              </p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {(queryExplain.fusion_summary?.active_layers ?? []).slice(0, 6).map((layer) => (
                  <Badge key={layer} size="sm" variant="outline">
                    {layer}
                  </Badge>
                ))}
              </div>
            </div>
          </LegendSection>
        </>
      )}

      {livePulse && (
        <>
          <div className="h-px bg-slate-800/60" />
          <LegendSection title="Live Interaction Pulse">
            <div className="rounded-lg border border-fuchsia-500/15 bg-fuchsia-500/5 px-2 py-2 text-[10px] text-slate-300">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-fuchsia-300">
                  {livePulse.protocol}
                </span>
                <span className="font-mono text-slate-500">
                  {livePulse.event_count} events
                </span>
              </div>
              <p className="mt-1 text-slate-400">
                Current selection, hover state, overlay mode, and drawer state
                are summarized in the same pulse-v2 shape used by FIG proof
                surfaces.
              </p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {(livePulse.active_layers ?? []).slice(0, 8).map((layer) => (
                  <Badge key={layer} size="sm" variant="outline">
                    {layer}
                  </Badge>
                ))}
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {livePulse.ui_context?.selected_node_id && (
                  <Badge size="sm" variant="secondary">
                    selected: {livePulse.ui_context.selected_node_id.slice(0, 12)}
                  </Badge>
                )}
                {livePulse.ui_context?.hovered_node_id && (
                  <Badge size="sm" variant="outline">
                    hover: {livePulse.ui_context.hovered_node_id.slice(0, 12)}
                  </Badge>
                )}
                {livePulse.ui_context?.overlay_mode && (
                  <Badge size="sm" variant="outline">
                    overlay: {livePulse.ui_context.overlay_mode}
                  </Badge>
                )}
                {livePulse.ui_context?.top_mode && (
                  <Badge size="sm" variant="outline">
                    mode: {livePulse.ui_context.top_mode}
                  </Badge>
                )}
              </div>
            </div>
          </LegendSection>
        </>
      )}

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
          SCORECARD — computed from graph topology
      ================================================================ */}
      <div className="h-px bg-slate-800/60" />
      <div className="rounded-lg border border-slate-800/60 bg-slate-900/30 px-3 py-2 space-y-2">
        <p className="text-[9px] font-semibold uppercase tracking-widest text-slate-500">
          Graph Scorecard (Computed)
        </p>

        {/* D — Density */}
        <div className="rounded-md bg-slate-900/50 border border-slate-800/40 p-2">
          <p className="text-[10px] font-mono font-semibold text-cyan-300">
            D — Density
          </p>
          <p className="text-[8px] text-slate-500 mt-0.5">
            Edges ÷ (Nodes × (Nodes−1)). Range 0–1.
          </p>
          <p className="text-[8px] text-slate-600 mt-1">
            <strong>0</strong> = no connections · <strong>1</strong> = complete
            graph
          </p>
        </div>

        {/* H — Entropy */}
        <div className="rounded-md bg-slate-900/50 border border-slate-800/40 p-2">
          <p className="text-[10px] font-mono font-semibold text-violet-300">
            H — Entropy
          </p>
          <p className="text-[8px] text-slate-500 mt-0.5">
            Shannon entropy of edge kinds (bits). Higher = more diverse.
          </p>
          <p className="text-[8px] text-slate-600 mt-1">
            <strong>0</strong> = all edges same kind ·{" "}
            <strong>log₂(kinds)</strong> = max
          </p>
        </div>

        {/* λ — Spectral Radius */}
        <div className="rounded-md bg-slate-900/50 border border-slate-800/40 p-2">
          <p className="text-[10px] font-mono font-semibold text-emerald-300">
            λ — Spectral Radius
          </p>
          <p className="text-[8px] text-slate-500 mt-0.5">
            Largest eigenvalue of adjacency matrix (power iteration).
          </p>
          <p className="text-[8px] text-slate-600 mt-1">
            <strong>Higher</strong> = tighter clustering ·{" "}
            <strong>Lower</strong> = sparse/random
          </p>
        </div>
      </div>
    </div>
  );
}
