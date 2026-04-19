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
// Hash-based Rainbow Coloring (Analyze mode)
//
// Deterministic: same node_id always produces the same color.
// Covers the full hue wheel so a homogeneous graph still shows rich variety.
// ---------------------------------------------------------------------------

function hashString(s: string): number {
  let h = 2166136261; // FNV-1a offset basis
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function hslToHex(h: number, s: number, l: number): string {
  // h in [0,360), s/l in [0,1]
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const hp = h / 60;
  const x = c * (1 - Math.abs((hp % 2) - 1));
  let r = 0, g = 0, b = 0;
  if (hp < 1)       { r = c; g = x; b = 0; }
  else if (hp < 2)  { r = x; g = c; b = 0; }
  else if (hp < 3)  { r = 0; g = c; b = x; }
  else if (hp < 4)  { r = 0; g = x; b = c; }
  else if (hp < 5)  { r = x; g = 0; b = c; }
  else              { r = c; g = 0; b = x; }
  const m = l - c / 2;
  const toHex = (v: number) => {
    const n = Math.round((v + m) * 255);
    return n.toString(16).padStart(2, "0");
  };
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

/**
 * Deterministic rainbow color from a node_id (or any string).
 * Returns an HSL-derived hex color with fixed saturation/lightness for
 * consistent visibility on dark backgrounds.
 */
export function nodeColorByIdentity(nodeId: string, selected: boolean): string {
  if (selected) return SELECTED_COLOR;
  const hue = hashString(nodeId) % 360;
  return hslToHex(hue, 0.70, 0.60); // vivid but not washed out
}

// ---------------------------------------------------------------------------
// Lineage Depth Coloring
//
// Gradient from warm (near selected) → cool (far from selected).
// Accepts the BFS distance from the focal node; 0 = the selected node itself.
// ---------------------------------------------------------------------------

const LINEAGE_DEPTH_COLORS = [
  "#f97316", // depth 0 — orange-500 (focal)
  "#fbbf24", // depth 1 — amber-400
  "#a3e635", // depth 2 — lime-400
  "#34d399", // depth 3 — emerald-400
  "#22d3ee", // depth 4 — cyan-400
  "#60a5fa", // depth 5 — blue-400
  "#a78bfa", // depth 6+ — violet-400
];

export function nodeColorByLineageDepth(depth: number, selected: boolean): string {
  if (selected) return SELECTED_COLOR;
  const clamped = Math.min(Math.max(depth, 0), LINEAGE_DEPTH_COLORS.length - 1);
  return LINEAGE_DEPTH_COLORS[clamped]!;
}

// ---------------------------------------------------------------------------
// Edge Colors by Kind
// ---------------------------------------------------------------------------

const EDGE_COLORS: Record<string, string> = {
  inheritance: "#22d3ee", // cyan-400
  opposition:  "#f87171", // rose-400
  similarity:  "#a78bfa", // violet-400
  semantic:    "#60a5fa", // blue-400
  co_occur:    "#94a3b8", // slate-400
};

const EDGE_DEFAULT_COLOR = "#94a3b8"; // slate-400 — visible on dark canvas

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

// ---------------------------------------------------------------------------
// Overlay Modes — FAIM-specific semantic emphasis
//
// Overlays sit on top of the topMode coloring and encode FAIM-specific
// signals from backend-authoritative node.metrics and display.state fields.
//
//   none       — use existing topMode-based coloring
//   retrieval  — highlight nodes by retrieval relevance (residual + touch_count)
//   evolution  — encode lifecycle state × freshness (last_access)
//   temporal   — warm-cool gradient by last_access recency (causal flow hints)
// ---------------------------------------------------------------------------

export type OverlayMode = "none" | "retrieval" | "evolution" | "temporal" | "causality";

/**
 * Retrieval relevance overlay.
 *
 * score = normalizedResidual × 0.6 + normalizedTouchCount × 0.4
 * High score → cyan (FAIM is actively retrieving from this node).
 * Low score  → near-black (rarely or never retrieved).
 */
export function nodeColorByRetrieval(score: number, isSelected: boolean): string {
  if (isSelected) return SELECTED_COLOR;
  if (score >= 0.8) return "#22d3ee"; // cyan-400  — highly relevant
  if (score >= 0.6) return "#0891b2"; // cyan-600
  if (score >= 0.4) return "#155e75"; // cyan-800
  if (score >= 0.2) return "#164e63"; // cyan-900
  return "#1e293b";                   // slate-800 — not retrieved
}

/**
 * Evolution freshness overlay.
 *
 * Encodes lifecycle state × temporal freshness derived from last_access.
 * freshnessScore = 0 (oldest in graph) … 1 (most recently accessed).
 * Nodes with no last_access get freshnessScore = 0.
 *
 * active      fresh/stale : emerald bright / emerald dark
 * historical  fresh/stale : amber bright / amber dark   (recently deprecated)
 * compressed  fresh/stale : blue bright / blue dark
 * deduplicated            : violet (merge is permanent — no freshness dimming)
 * pruned                  : red    (terminal — no freshness dimming)
 * cold / deactivated      : always dim slate
 */
export function nodeColorByEvolution(
  state: FigNodeDisplayState,
  freshnessScore: number,
  isSelected: boolean,
): string {
  if (isSelected) return SELECTED_COLOR;
  const fresh = freshnessScore >= 0.5;
  switch (state) {
    case "active":       return fresh ? "#34d399" : "#065f46"; // emerald-400 / emerald-900
    case "historical":   return fresh ? "#fbbf24" : "#92400e"; // amber-400   / amber-800
    case "compressed":   return fresh ? "#60a5fa" : "#1e3a5f"; // blue-400    / custom dark blue
    case "deduplicated": return "#a78bfa";                      // violet-400 (permanent)
    case "pruned":       return "#f87171";                      // red-400    (terminal)
    case "cold":         return "#334155";                      // slate-700
    case "deactivated":  return "#1e293b";                      // slate-800
    default:             return "#475569";                      // slate-600
  }
}

/**
 * Temporal recency overlay.
 *
 * Maps last_access freshness to a warm-cool gradient:
 * hot (orange) = just accessed  →  cool (blue) = long ago  →  dark = never.
 * Encodes causal flow: follow the heat to see where FAIM has been recently.
 */
export function nodeColorByTemporal(score: number, isSelected: boolean): string {
  if (isSelected) return SELECTED_COLOR;
  if (score >= 0.85) return "#f97316"; // orange-500 — very recent
  if (score >= 0.65) return "#fbbf24"; // amber-400
  if (score >= 0.45) return "#34d399"; // emerald-400
  if (score >= 0.25) return "#60a5fa"; // blue-400
  if (score > 0)     return "#475569"; // slate-600  — old
  return "#1e293b";                    // slate-800  — never accessed
}

/**
 * Retrieval size boost.
 *
 * Scales node size by normalizedTouchCount so frequently-retrieved nodes
 * are visually prominent in retrieval overlay mode.
 * baseSize × (1 + normT) caps at 2× the base size.
 */
export function nodeSizeByRetrievalBoost(baseSize: number, normalizedTouchCount: number): number {
  return baseSize * (1 + Math.min(normalizedTouchCount, 1));
}

/**
 * Causality overlay — hot zones by combined recency × access frequency.
 * Score = 0.5 × normalizedTouchCount + 0.5 × recencyScore [0-1]
 */
export function nodeColorByCausality(score: number, isSelected: boolean): string {
  if (isSelected) return SELECTED_COLOR;
  if (score >= 0.8) return "#ef4444"; // red-500   — very hot (recent + frequent)
  if (score >= 0.6) return "#f97316"; // orange-500
  if (score >= 0.4) return "#fbbf24"; // amber-400
  if (score >= 0.2) return "#60a5fa"; // blue-400  — cool
  return "#1e293b";                   // slate-800 — cold / never accessed
}
