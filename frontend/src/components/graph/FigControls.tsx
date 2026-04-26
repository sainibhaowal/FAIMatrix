"use client";

import { useMemo } from "react";
import {
  Clock3,
  Crosshair,
  Eye,
  GitFork,
  Lock,
  Maximize2,
  Minus,
  Network,
  Plus,
  RotateCcw,
  RefreshCw,
  Unlock,
} from "lucide-react";

import { Badge } from "@/components/ui";
import type { LayoutMode, OverlayMode } from "@/lib/figViewLayout";
import type { FigNode, FigTopology } from "@/types/figView";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FigControlsProps = {
  layoutMode: LayoutMode;
  onLayoutChange: (mode: LayoutMode) => void;
  locked: boolean;
  onLockToggle: () => void;
  selectedNodeId: string | null;
  onFit: () => void;
  onCenter: () => void;
  onResetCamera: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  timelineVisible: boolean;
  onTimelineToggle: () => void;
  liveSyncEnabled: boolean;
  onLiveSyncToggle: () => void;
  liveSyncStatus:
    | "idle"
    | "live"
    | "catching_up"
    | "stale"
    | "disconnected"
    | "error";
  similarityMode: string;
  overlayMode: OverlayMode;
  onOverlayChange: (mode: OverlayMode) => void;
  topology?: FigTopology | null;
  nodes?: FigNode[];
};

// ---------------------------------------------------------------------------
// Layout mode config
// ---------------------------------------------------------------------------

const MODES: Array<{ key: LayoutMode; label: string; icon: React.ReactNode }> =
  [
    { key: "explore", label: "Explore", icon: <Eye className="h-3.5 w-3.5" /> },
    {
      key: "analyze",
      label: "Analyze",
      icon: <Network className="h-3.5 w-3.5" />,
    },
    {
      key: "lineage",
      label: "Lineage",
      icon: <GitFork className="h-3.5 w-3.5" />,
    },
  ];

const OVERLAYS: Array<{ key: OverlayMode; label: string; title: string }> = [
  {
    key: "none",
    label: "None",
    title: "No overlay — use layout mode coloring",
  },
  {
    key: "retrieval",
    label: "Retrieval",
    title: "Highlight nodes by retrieval relevance (residual × touch count)",
  },
  {
    key: "evolution",
    label: "Evolution",
    title: "Encode lifecycle state × temporal freshness",
  },
  {
    key: "temporal",
    label: "Temporal",
    title: "Warm-cool gradient by last access recency",
  },
  {
    key: "causality",
    label: "Causality",
    title: "Hot zones by combined recency × access frequency",
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

// Color helpers for quality indicators
function dHealthColor(d: number) {
  return d >= 0.15 ? "#22d3ee" : d >= 0.05 ? "#fbbf24" : "#64748b";
}
function hHealthColor(h: number) {
  return h >= 0.8 ? "#a78bfa" : h >= 0.3 ? "#fbbf24" : "#64748b";
}
function lHealthColor(l: number) {
  return l >= 2.0 ? "#34d399" : l >= 0.5 ? "#fbbf24" : "#64748b";
}
function stateColor(s: string): string {
  const MAP: Record<string, string> = {
    active: "#34d399",
    cold: "#64748b",
    historical: "#fbbf24",
    compressed: "#60a5fa",
    deduplicated: "#a78bfa",
    pruned: "#f87171",
    deactivated: "#475569",
    unknown: "#94a3b8",
  };
  return MAP[s] ?? "#94a3b8";
}

export default function FigControls({
  layoutMode,
  onLayoutChange,
  locked,
  onLockToggle,
  selectedNodeId,
  onFit,
  onCenter,
  onResetCamera,
  onZoomIn,
  onZoomOut,
  timelineVisible,
  onTimelineToggle,
  liveSyncEnabled,
  onLiveSyncToggle,
  liveSyncStatus,
  similarityMode,
  overlayMode,
  onOverlayChange,
  topology,
  nodes = [],
}: FigControlsProps) {
  const quality = useMemo(() => {
    if (!nodes.length) return null;
    const counts: Record<string, number> = {};
    let macroCount = 0;
    for (const n of nodes) {
      const s = n.display?.state ?? "unknown";
      counts[s] = (counts[s] ?? 0) + 1;
      if (n.level > 0) macroCount++;
    }
    const total = nodes.length;
    const compressedCount =
      (counts.compressed ?? 0) + (counts.deduplicated ?? 0);
    const edgeTotal = topology?.edge_count ?? 0;
    const oppCount =
      topology?.edge_counts_by_kind?.opposition ??
      topology?.edge_counts_by_kind?.OPPOSITION ??
      0;
    return {
      counts,
      total,
      macroRatio: total > 0 ? macroCount / total : 0,
      compressionRate: total > 0 ? compressedCount / total : 0,
      activeRatio: total > 0 ? (counts.active ?? 0) / total : 0,
      oppositionDensity: edgeTotal > 0 ? oppCount / edgeTotal : 0,
    };
  }, [nodes, topology]);

  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-xl bg-slate-900/70 border border-slate-800 px-3 py-2">
      {/* Layout mode toggle */}
      <div className="flex items-center rounded-lg bg-slate-800/60 p-0.5">
        {MODES.map((m) => (
          <button
            key={m.key}
            onClick={() => onLayoutChange(m.key)}
            className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              layoutMode === m.key
                ? "bg-cyan-900/60 text-cyan-300"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"
            }`}
            title={`${m.label} layout`}
          >
            {m.icon}
            <span className="hidden sm:inline">{m.label}</span>
          </button>
        ))}
      </div>

      <Separator />

      {/* Camera controls */}
      <ControlButton
        onClick={onFit}
        title="Fit graph to view"
        icon={<Maximize2 />}
      />
      <ControlButton
        onClick={onCenter}
        title={selectedNodeId ? "Center on selection" : "No node selected"}
        icon={<Crosshair />}
        disabled={!selectedNodeId}
      />
      <ControlButton
        onClick={onResetCamera}
        title="Reset camera"
        icon={<RotateCcw />}
      />

      <Separator />

      {/* Zoom */}
      <ControlButton onClick={onZoomIn} title="Zoom in" icon={<Plus />} />
      <ControlButton onClick={onZoomOut} title="Zoom out" icon={<Minus />} />

      <Separator />

      {/* Lock / Unlock */}
      <button
        onClick={onLockToggle}
        className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-colors ${
          locked
            ? "bg-amber-900/40 text-amber-300"
            : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"
        }`}
        title={locked ? "Unlock simulation" : "Lock simulation"}
      >
        {locked ? (
          <Lock className="h-3.5 w-3.5" />
        ) : (
          <Unlock className="h-3.5 w-3.5" />
        )}
        <span className="hidden sm:inline">{locked ? "Locked" : "Unlock"}</span>
      </button>

      <Separator />

      {/* Timeline toggle */}
      <button
        onClick={onTimelineToggle}
        className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-colors ${
          timelineVisible
            ? "bg-cyan-900/40 text-cyan-300"
            : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"
        }`}
        title={timelineVisible ? "Hide timeline" : "Show timeline"}
      >
        <Clock3 className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">Timeline</span>
      </button>

      <button
        onClick={onLiveSyncToggle}
        className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-colors ${
          liveSyncEnabled
            ? "bg-emerald-900/35 text-emerald-300"
            : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"
        }`}
        title={
          liveSyncEnabled
            ? "Pause live timeline sync"
            : "Resume live timeline sync"
        }
      >
        <RefreshCw
          className={`h-3.5 w-3.5 ${liveSyncEnabled && liveSyncStatus === "live" ? "animate-spin" : ""}`}
        />
        <span className="hidden sm:inline">Live</span>
      </button>

      <Separator />

      {/* Overlay mode */}
      <div className="flex flex-col gap-1 w-full">
        <span className="text-[9px] uppercase tracking-widest text-slate-500 px-1">
          Overlay
        </span>
        <div className="flex items-center rounded-lg bg-slate-800/60 p-0.5">
          {OVERLAYS.map((o) => (
            <button
              key={o.key}
              onClick={() => onOverlayChange(o.key)}
              title={o.title}
              className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                overlayMode === o.key
                  ? "bg-violet-900/60 text-violet-300"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {/* Similarity control (v1 placeholder) */}
      <div className="ml-auto flex items-center gap-1 mt-1">
        <Badge
          size="sm"
          variant={
            liveSyncStatus === "disconnected" || liveSyncStatus === "error"
              ? "error"
              : liveSyncStatus === "catching_up"
                ? "warning"
                : "outline"
          }
        >
          {liveSyncStatus}
        </Badge>
        <Badge size="sm" variant="outline">
          similarity: {similarityMode}
        </Badge>
      </div>

      {/* ================================================================
          TOPOLOGY QUALITY PANEL
          Shows D/H/λ health, node lifecycle breakdown, and self-org signals.
          All values computed client-side from backend-authoritative data.
      ================================================================ */}
      {(topology || quality) && (
        <div className="w-full mt-1 space-y-2 border-t border-slate-700/40 pt-2">
          <span className="text-[9px] uppercase tracking-widest text-slate-500 px-1">
            Graph Quality
          </span>

          {/* Scorecard health — color-coded D / H / λ */}
          {topology?.scorecard && (
            <div className="grid grid-cols-3 gap-1">
              {[
                {
                  key: "D",
                  val: topology.scorecard.density,
                  color: dHealthColor(topology.scorecard.density),
                  hint: "density",
                },
                {
                  key: "H",
                  val: topology.scorecard.entropy,
                  color: hHealthColor(topology.scorecard.entropy),
                  hint: "entropy",
                },
                {
                  key: "λ",
                  val: topology.scorecard.spectral_radius,
                  color: lHealthColor(topology.scorecard.spectral_radius),
                  hint: "spectral",
                },
              ].map(({ key, val, color, hint }) => (
                <div
                  key={key}
                  className="flex flex-col items-center rounded-md bg-slate-900/40 border border-slate-800/60 py-1.5"
                >
                  <span
                    className="font-mono text-xs font-bold"
                    style={{ color }}
                  >
                    {val.toFixed(2)}
                  </span>
                  <span className="text-[8px] text-slate-500">{key}</span>
                  <span className="text-[7px] text-slate-700">{hint}</span>
                </div>
              ))}
            </div>
          )}

          {/* Self-org signals */}
          {quality && (
            <div className="grid grid-cols-2 gap-1">
              {[
                {
                  label: "Active",
                  value: `${(quality.activeRatio * 100).toFixed(0)}%`,
                  color:
                    quality.activeRatio >= 0.6
                      ? "#34d399"
                      : quality.activeRatio >= 0.3
                        ? "#fbbf24"
                        : "#94a3b8",
                },
                {
                  label: "Compressed",
                  value: `${(quality.compressionRate * 100).toFixed(0)}%`,
                  color: quality.compressionRate > 0 ? "#60a5fa" : "#64748b",
                },
                {
                  label: "Macro nodes",
                  value: `${(quality.macroRatio * 100).toFixed(0)}%`,
                  color: quality.macroRatio > 0 ? "#a78bfa" : "#64748b",
                },
                {
                  label: "Opp. density",
                  value: `${(quality.oppositionDensity * 100).toFixed(0)}%`,
                  color:
                    quality.oppositionDensity > 0.2
                      ? "#f87171"
                      : quality.oppositionDensity > 0.05
                        ? "#fbbf24"
                        : "#64748b",
                },
              ].map(({ label, value, color }) => (
                <div
                  key={label}
                  className="flex items-center justify-between rounded bg-slate-900/30 px-2 py-1"
                >
                  <span className="text-[9px] text-slate-500">{label}</span>
                  <span
                    className="font-mono text-[10px] font-semibold"
                    style={{ color }}
                  >
                    {value}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Node lifecycle breakdown */}
          {quality && Object.entries(quality.counts).length > 0 && (
            <div className="space-y-0.5">
              <span className="text-[8px] uppercase tracking-widest text-slate-600 px-1">
                Lifecycle
              </span>
              {Object.entries(quality.counts)
                .sort(([, a], [, b]) => b - a)
                .map(([state, count]) => (
                  <div key={state} className="flex items-center gap-1.5 px-1">
                    <span
                      className="h-1.5 w-1.5 rounded-full shrink-0"
                      style={{ backgroundColor: stateColor(state) }}
                    />
                    <span className="flex-1 text-[9px] text-slate-500 capitalize">
                      {state}
                    </span>
                    <span className="font-mono text-[9px] text-slate-400">
                      {count}
                    </span>
                    <div
                      className="h-1 rounded-full bg-slate-700"
                      style={{ width: 40, position: "relative" }}
                    >
                      <div
                        className="h-1 rounded-full absolute left-0 top-0"
                        style={{
                          width: `${(count / quality.total) * 100}%`,
                          backgroundColor: stateColor(state),
                        }}
                      />
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ControlButton({
  onClick,
  title,
  icon,
  disabled = false,
}: {
  onClick: () => void;
  title: string;
  icon: React.ReactNode;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="flex items-center justify-center h-7 w-7 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors [&>svg]:h-3.5 [&>svg]:w-3.5"
      title={title}
    >
      {icon}
    </button>
  );
}

function Separator() {
  return <div className="h-5 w-px bg-slate-700/60 mx-0.5" />;
}
