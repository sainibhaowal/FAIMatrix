/**
 * FIG View layout modes and force-simulation tuning.
 *
 * Three layout modes: Explore (free organic), Analyze (spread for inspection),
 * Lineage (top-down DAG for parent→child).
 */

import type { FigNodeDisplayState } from "@/types/figView";

// ---------------------------------------------------------------------------
// Layout Modes
// ---------------------------------------------------------------------------

export type LayoutMode = "explore" | "analyze" | "lineage";

export type DagMode = "td" | "bu" | "lr" | "rl" | "zout" | "zin" | "radialout" | "radialin";

export type LayoutConfig = {
  dagMode: DagMode | null;
  chargeStrength: number;
  linkDistance: number;
  d3AlphaDecay: number;
  d3VelocityDecay: number;
  centerStrength: number;
};

const LAYOUT_CONFIGS: Record<LayoutMode, LayoutConfig> = {
  explore: {
    dagMode: null,
    chargeStrength: -120,
    linkDistance: 50,
    d3AlphaDecay: 0.0228,
    d3VelocityDecay: 0.4,
    centerStrength: 0.05,
  },
  analyze: {
    dagMode: null,
    chargeStrength: -200,
    linkDistance: 80,
    d3AlphaDecay: 0.01,
    d3VelocityDecay: 0.3,
    centerStrength: 0.03,
  },
  lineage: {
    dagMode: "td",
    chargeStrength: -80,
    linkDistance: 60,
    d3AlphaDecay: 0.02,
    d3VelocityDecay: 0.4,
    centerStrength: 0.05,
  },
};

export function getLayoutConfig(mode: LayoutMode): LayoutConfig {
  return LAYOUT_CONFIGS[mode];
}

/**
 * Apply layout forces to a ForceGraph3D ref.
 * Caller must call `d3ReheatSimulation()` after this.
 */
export function applyLayout(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  fgRef: { current: any },
  config: LayoutConfig,
): void {
  const fg = fgRef.current;
  if (!fg) return;

  const charge = fg.d3Force("charge");
  if (charge && typeof charge.strength === "function") {
    charge.strength(config.chargeStrength);
  }

  const link = fg.d3Force("link");
  if (link && typeof link.distance === "function") {
    link.distance(config.linkDistance);
  }

  const center = fg.d3Force("center");
  if (center && typeof center.strength === "function") {
    center.strength(config.centerStrength);
  }

  fg.d3ReheatSimulation();
}

// ---------------------------------------------------------------------------
// Node Colors by Display State
// ---------------------------------------------------------------------------

const STATE_COLORS: Record<FigNodeDisplayState, string> = {
  active: "#34d399",       // emerald-400
  cold: "#64748b",         // slate-500
  historical: "#fbbf24",   // amber-400
  compressed: "#60a5fa",   // blue-400
  deduplicated: "#a78bfa", // violet-400
  pruned: "#f87171",       // red-400
  deactivated: "#475569",  // slate-600
  unknown: "#94a3b8",      // slate-400
};

const SELECTED_COLOR = "#22d3ee"; // cyan-400

export function nodeColorByState(state: FigNodeDisplayState, selected: boolean): string {
  if (selected) return SELECTED_COLOR;
  return STATE_COLORS[state] ?? STATE_COLORS.unknown;
}

// ---------------------------------------------------------------------------
// Edge Colors by Kind
// ---------------------------------------------------------------------------

const EDGE_COLORS: Record<string, string> = {
  inheritance: "#22d3ee80", // cyan-400 with alpha
  opposition: "#f8717180",  // red-400 with alpha
};

const EDGE_DEFAULT_COLOR = "#47556980"; // slate-600 with alpha

export function edgeColorByKind(kind: string): string {
  return EDGE_COLORS[kind] ?? EDGE_DEFAULT_COLOR;
}

// ---------------------------------------------------------------------------
// Node Size by Level
// ---------------------------------------------------------------------------

export function nodeSizeByLevel(level: number): number {
  if (level >= 2) return 6;  // macro
  if (level === 1) return 4; // intermediate
  return 2.5;                // atom
}

// ---------------------------------------------------------------------------
// Default Camera Position
// ---------------------------------------------------------------------------

export const DEFAULT_CAMERA = { x: 0, y: 0, z: 300 } as const;
