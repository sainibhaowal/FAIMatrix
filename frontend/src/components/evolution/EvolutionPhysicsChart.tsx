"use client";

import React, { useMemo, useState } from "react";
import {
  Activity,
  Cpu,
  Flame,
  Gauge,
  GitBranch,
  Layers,
  Radio,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface EvolutionPhysicsPoint {
  time: string;
  seq?: number;
  entropy: number; // H
  redundancy: number; // R
  novelty: number; // N
  pressure: number; // Lambda
  energy: number; // E
  d_hat?: number;
  cr?: number;
  action?: string;
  cycle_version?: number | null;
  merges_count?: number;
  macros_count?: number;
}

export interface PhysicsStreamPoint {
  seq: number;
  ts: string;
  label: string;
  cycle_version?: number | null;
  action: string;
  redundancy_R: number;
  novelty_N: number;
  novelty_raw: number;
  pressure_lambda: number;
  entropy_H: number;
  energy_E: number;
  d_hat: number;
  compression_ratio_cr: number;
  merges_count: number;
  macros_count: number;
  nodes_count: number;
  edges_count: number;
}

export interface PhysicsStreamResponse {
  graph_id: string;
  tenant_id: string;
  last_seq: number;
  computed_at: string;
  points: PhysicsStreamPoint[];
  current: {
    redundancy_R: number;
    novelty_N: number;
    novelty_raw: number;
    pressure_lambda: number;
    entropy_H: number;
    energy_E: number;
    d_hat: number;
    compression_ratio_cr: number;
  };
  deltas: Record<string, number>;
  thresholds: {
    tau_R: number;
    tau_N: number;
    tau_E: number;
    lambda_critical: number;
    d_hat_target: number;
  };
  evals: {
    regime: string;
    lyapunov_stable: boolean;
    manifold_health_score: number;
    compression_efficiency: number;
    invention_readiness: number;
    total_nodes: number;
    total_macros: number;
    total_merges: number;
    total_theories: number;
    sample_count: number;
  };
}

interface EvolutionPhysicsChartProps {
  data: EvolutionPhysicsPoint[];
  streamData?: PhysicsStreamResponse | null;
  sseConnected?: boolean;
  onRefresh?: () => void;
}

type SeriesKey =
  | "redundancy_R"
  | "novelty_N"
  | "pressure_lambda"
  | "entropy_H"
  | "energy_E"
  | "d_hat"
  | "compression_ratio_cr";

type ChartPreset = "equilibrium" | "geometry" | "all";

interface ChartDatum {
  idx: number;
  seq: number;
  label: string;
  ts: string;
  action: string;
  cycle_version?: number | null;
  redundancy_R: number;
  novelty_N: number;
  novelty_raw: number;
  pressure_lambda: number;
  entropy_H: number;
  energy_E: number;
  d_hat: number;
  compression_ratio_cr: number;
  merges_count: number;
  macros_count: number;
  nodes_count: number;
  edges_count: number;
}

const SERIES_CONFIG: Array<{
  key: SeriesKey;
  short: string;
  label: string;
  color: string;
  gradId: string;
  unit?: string;
}> = [
  {
    key: "redundancy_R",
    short: "R",
    label: "Redundancy (R)",
    color: "#f43f5e",
    gradId: "gradRedundancy",
  },
  {
    key: "novelty_N",
    short: "N",
    label: "Novelty (N)",
    color: "#10b981",
    gradId: "gradNovelty",
  },
  {
    key: "pressure_lambda",
    short: "λ̂",
    label: "Pressure (λ̂)",
    color: "#f59e0b",
    gradId: "gradPressure",
  },
  {
    key: "entropy_H",
    short: "Ĥ",
    label: "Entropy (Ĥ)",
    color: "#06b6d4",
    gradId: "gradEntropy",
  },
  {
    key: "energy_E",
    short: "E",
    label: "Energy (E)",
    color: "#a855f7",
    gradId: "gradEnergy",
  },
  {
    key: "d_hat",
    short: "D̂",
    label: "Fractal Dim (D̂)",
    color: "#38bdf8",
    gradId: "gradDhat",
  },
  {
    key: "compression_ratio_cr",
    short: "CR",
    label: "Compression (CR)",
    color: "#e879f9",
    gradId: "gradCr",
  },
];

const REGIME_STYLES: Record<
  string,
  { badge: string; label: string; hint: string }
> = {
  HIGH_PRESSURE_BIFURCATION: {
    badge: "bg-amber-500/20 text-amber-300 border-amber-400/50",
    label: "HIGH-PRESSURE BIFURCATION",
    hint: "Co-activation pressure λ̂ exceeded λ_crit — active structural bifurcation & invention",
  },
  HIGH_PRESSURE_INVENTION: {
    badge: "bg-amber-500/15 text-amber-300 border-amber-500/40",
    label: "HIGH-PRESSURE INVENTION",
    hint: "Co-activation pressure λ̂ exceeds critical threshold — active macro crystallization",
  },
  REDUNDANCY_COMPRESSION: {
    badge: "bg-rose-500/15 text-rose-300 border-rose-500/40",
    label: "REDUNDANCY COMPRESSION",
    hint: "Antisymmetric opposition pairs are pruning overlap and tightening manifold density",
  },
  CONVERGED_STABLE: {
    badge: "bg-emerald-500/20 text-emerald-300 border-emerald-400/50",
    label: "CONVERGED STABLE",
    hint: "Manifold settled inside Lyapunov basin with low drift and stabilized entropy",
  },
  LYAPUNOV_CONVERGED: {
    badge: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
    label: "LYAPUNOV CONVERGED",
    hint: "Total manifold energy E is below equilibrium threshold τ_E with dE/dt ≤ 0",
  },
  EQUILIBRIUM_DRIFT: {
    badge: "bg-sky-500/15 text-sky-300 border-sky-500/40",
    label: "EQUILIBRIUM DRIFT",
    hint: "Manifold tracking gradual novelty absorption and structural equilibrium adaptation",
  },
  ACTIVE_EQUILIBRIUM: {
    badge: "bg-cyan-500/15 text-cyan-300 border-cyan-500/40",
    label: "ACTIVE EQUILIBRIUM",
    hint: "Manifold evolving within nominal bounds across entropy, pressure, and geometry",
  },
  IDLE_MANIFOLD: {
    badge: "bg-slate-500/15 text-slate-300 border-slate-500/40",
    label: "IDLE MANIFOLD",
    hint: "Awaiting evolution telemetry or synthesis pressure updates",
  },
};

function fmt4(v: number | undefined | null): string {
  if (typeof v !== "number" || !Number.isFinite(v)) return "0.0000";
  return v.toFixed(4);
}

function fmtDelta(v: number | undefined | null): {
  text: string;
  tone: "up" | "down" | "flat";
} {
  if (typeof v !== "number" || !Number.isFinite(v) || Math.abs(v) < 0.00005) {
    return { text: "0.0000", tone: "flat" };
  }
  return {
    text: `${v > 0 ? "+" : ""}${v.toFixed(4)}`,
    tone: v > 0 ? "up" : "down",
  };
}

function actionBadgeStyle(action: string): string {
  const upper = (action || "").toUpperCase();
  if (upper.includes("INVENT") || upper.includes("MACRO")) {
    return "bg-purple-500/20 text-purple-300 border-purple-500/40";
  }
  if (upper.includes("MERGE")) {
    return "bg-cyan-500/20 text-cyan-300 border-cyan-500/40";
  }
  if (upper.includes("PRUNE")) {
    return "bg-rose-500/20 text-rose-300 border-rose-500/40";
  }
  if (upper.includes("CONVERG")) {
    return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
  }
  return "bg-slate-500/20 text-slate-300 border-slate-500/30";
}

function PhysicsTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: ChartDatum }>;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const pt = payload[0].payload;
  return (
    <div className="min-w-[250px] rounded-xl border border-cyan-400/30 bg-[#050914]/95 p-3 shadow-[0_0_24px_rgba(6,182,212,0.18)] backdrop-blur-xl font-mono text-[11px]">
      <div className="flex items-center justify-between gap-3 border-b border-white/10 pb-2 mb-2">
        <div>
          <div className="text-slate-200 font-semibold">
            {pt.label}{" "}
            {pt.cycle_version != null ? `· v${pt.cycle_version}` : ""}
          </div>
          <div className="text-[10px] text-slate-400">
            seq #{pt.seq}
            {pt.ts ? ` · ${pt.ts.slice(11, 19)}` : ""}
          </div>
        </div>
        <span
          className={`rounded border px-1.5 py-0.5 text-[9px] uppercase ${actionBadgeStyle(
            pt.action,
          )}`}
        >
          {pt.action}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
        <div className="flex justify-between text-rose-300">
          <span>R</span>
          <span>{fmt4(pt.redundancy_R)}</span>
        </div>
        <div className="flex justify-between text-emerald-300">
          <span>N</span>
          <span>{fmt4(pt.novelty_N)}</span>
        </div>
        <div className="flex justify-between text-amber-300">
          <span>λ̂</span>
          <span>{fmt4(pt.pressure_lambda)}</span>
        </div>
        <div className="flex justify-between text-cyan-300">
          <span>Ĥ</span>
          <span>{fmt4(pt.entropy_H)}</span>
        </div>
        <div className="flex justify-between text-purple-300">
          <span>E</span>
          <span>{fmt4(pt.energy_E)}</span>
        </div>
        <div className="flex justify-between text-sky-300">
          <span>D̂</span>
          <span>{fmt4(pt.d_hat)}</span>
        </div>
        <div className="flex justify-between text-fuchsia-300">
          <span>CR</span>
          <span>{fmt4(pt.compression_ratio_cr)}</span>
        </div>
        <div className="flex justify-between text-slate-300">
          <span>Δ M/I</span>
          <span>
            +{pt.merges_count}m / +{pt.macros_count}i
          </span>
        </div>
      </div>

      {(pt.nodes_count > 0 || pt.edges_count > 0) && (
        <div className="mt-2 border-t border-white/10 pt-1.5 flex justify-between text-[10px] text-slate-400">
          <span>nodes: {pt.nodes_count}</span>
          <span>edges: {pt.edges_count}</span>
          {pt.novelty_raw > 0 && <span>rawN: {fmt4(pt.novelty_raw)}</span>}
        </div>
      )}
    </div>
  );
}

export const EvolutionPhysicsChart: React.FC<EvolutionPhysicsChartProps> = ({
  data,
  streamData,
  sseConnected = false,
  onRefresh,
}) => {
  const [preset, setPreset] = useState<ChartPreset>("equilibrium");
  const [windowSize, setWindowSize] = useState<"15" | "40" | "all">("40");
  const [showThresholds, setShowThresholds] = useState(true);
  const [visibleSeries, setVisibleSeries] = useState<
    Record<SeriesKey, boolean>
  >({
    redundancy_R: true,
    novelty_N: true,
    pressure_lambda: true,
    entropy_H: true,
    energy_E: true,
    d_hat: false,
    compression_ratio_cr: false,
  });

  const handlePresetChange = (next: ChartPreset) => {
    setPreset(next);
    if (next === "equilibrium") {
      setVisibleSeries({
        redundancy_R: true,
        novelty_N: true,
        pressure_lambda: true,
        entropy_H: true,
        energy_E: false,
        d_hat: false,
        compression_ratio_cr: false,
      });
    } else if (next === "geometry") {
      setVisibleSeries({
        redundancy_R: false,
        novelty_N: false,
        pressure_lambda: false,
        entropy_H: false,
        energy_E: true,
        d_hat: true,
        compression_ratio_cr: true,
      });
    } else {
      setVisibleSeries({
        redundancy_R: true,
        novelty_N: true,
        pressure_lambda: true,
        entropy_H: true,
        energy_E: true,
        d_hat: true,
        compression_ratio_cr: true,
      });
    }
  };

  const toggleSeries = (key: SeriesKey) => {
    setVisibleSeries((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const allPoints: ChartDatum[] = useMemo(() => {
    if (
      streamData &&
      Array.isArray(streamData.points) &&
      streamData.points.length > 0
    ) {
      return streamData.points.map((pt, idx) => ({
        idx,
        seq: pt.seq,
        label: pt.label || `#${pt.seq}`,
        ts: pt.ts || "",
        action: pt.action || "SNAPSHOT",
        cycle_version: pt.cycle_version ?? null,
        redundancy_R: Number(pt.redundancy_R ?? 0),
        novelty_N: Number(pt.novelty_N ?? 0),
        novelty_raw: Number(pt.novelty_raw ?? pt.novelty_N ?? 0),
        pressure_lambda: Number(pt.pressure_lambda ?? 0),
        entropy_H: Number(pt.entropy_H ?? 0),
        energy_E: Number(pt.energy_E ?? 0),
        d_hat: Number(pt.d_hat ?? 0),
        compression_ratio_cr: Number(pt.compression_ratio_cr ?? 0),
        merges_count: Number(pt.merges_count ?? 0),
        macros_count: Number(pt.macros_count ?? 0),
        nodes_count: Number(pt.nodes_count ?? 0),
        edges_count: Number(pt.edges_count ?? 0),
      }));
    }

    return (data || []).map((pt, idx) => ({
      idx,
      seq: pt.seq ?? idx + 1,
      label: pt.time || `T-${(data?.length || 1) - idx}`,
      ts: "",
      action: pt.action || "DIAGNOSTICS",
      cycle_version: pt.cycle_version ?? null,
      redundancy_R: Number(pt.redundancy ?? 0),
      novelty_N: Number(pt.novelty ?? 0),
      novelty_raw: Number(pt.novelty ?? 0),
      pressure_lambda: Number(pt.pressure ?? 0),
      entropy_H: Number(pt.entropy ?? 0),
      energy_E: Number(pt.energy ?? 0),
      d_hat: Number(pt.d_hat ?? 0),
      compression_ratio_cr: Number(pt.cr ?? 0),
      merges_count: Number(pt.merges_count ?? 0),
      macros_count: Number(pt.macros_count ?? 0),
      nodes_count: 0,
      edges_count: 0,
    }));
  }, [streamData, data]);

  const chartPoints = useMemo(() => {
    if (windowSize === "all") return allPoints;
    const n = Number(windowSize);
    return allPoints.length > n ? allPoints.slice(-n) : allPoints;
  }, [allPoints, windowSize]);

  const latest = chartPoints[chartPoints.length - 1];
  const prev =
    chartPoints.length > 1 ? chartPoints[chartPoints.length - 2] : undefined;

  const current = streamData?.current ?? {
    redundancy_R: latest?.redundancy_R ?? 0,
    novelty_N: latest?.novelty_N ?? 0,
    novelty_raw: latest?.novelty_raw ?? 0,
    pressure_lambda: latest?.pressure_lambda ?? 0,
    entropy_H: latest?.entropy_H ?? 0,
    energy_E: latest?.energy_E ?? 0,
    d_hat: latest?.d_hat ?? 0,
    compression_ratio_cr: latest?.compression_ratio_cr ?? 0,
  };

  const deltas = streamData?.deltas ?? {
    redundancy_R: prev ? current.redundancy_R - prev.redundancy_R : 0,
    novelty_N: prev ? current.novelty_N - prev.novelty_N : 0,
    pressure_lambda: prev ? current.pressure_lambda - prev.pressure_lambda : 0,
    entropy_H: prev ? current.entropy_H - prev.entropy_H : 0,
    energy_E: prev ? current.energy_E - prev.energy_E : 0,
    d_hat: prev ? current.d_hat - prev.d_hat : 0,
    compression_ratio_cr: prev
      ? current.compression_ratio_cr - prev.compression_ratio_cr
      : 0,
  };

  const thresholds = streamData?.thresholds ?? {
    tau_R: 0.35,
    tau_N: 0.25,
    tau_E: 0.45,
    lambda_critical: 0.3,
    d_hat_target: 1.5,
  };

  const evals = streamData?.evals ?? {
    regime: allPoints.length > 0 ? "ACTIVE_EQUILIBRIUM" : "IDLE_MANIFOLD",
    lyapunov_stable: (deltas.energy_E ?? 0) <= 0.005,
    manifold_health_score: Math.max(
      0,
      Math.min(100, (1 - Math.min(1, current.energy_E)) * 100),
    ),
    compression_efficiency: current.compression_ratio_cr * 100,
    invention_readiness: Math.min(
      100,
      (current.pressure_lambda / Math.max(0.05, thresholds.lambda_critical)) *
        100,
    ),
    total_nodes: latest?.nodes_count ?? 0,
    total_macros: latest?.macros_count ?? 0,
    total_merges: latest?.merges_count ?? 0,
    total_theories: 0,
    sample_count: allPoints.length,
  };

  const regimeMeta =
    REGIME_STYLES[evals.regime] || REGIME_STYLES.ACTIVE_EQUILIBRIUM;

  const kpiCards: Array<{
    key: SeriesKey;
    title: string;
    symbol: string;
    value: number;
    delta: number;
    threshold?: { label: string; val: number };
    subtext?: string;
    color: string;
    accentBorder: string;
  }> = [
    {
      key: "redundancy_R",
      title: "Redundancy",
      symbol: "R",
      value: current.redundancy_R,
      delta: deltas.redundancy_R ?? 0,
      threshold: { label: "τ_R", val: thresholds.tau_R },
      color: "text-rose-300",
      accentBorder: "border-rose-500/25 hover:border-rose-400/50",
    },
    {
      key: "novelty_N",
      title: "Novelty",
      symbol: "N",
      value: current.novelty_N,
      delta: deltas.novelty_N ?? 0,
      threshold: { label: "τ_N", val: thresholds.tau_N },
      subtext:
        current.novelty_raw > current.novelty_N + 0.0005
          ? `raw ${current.novelty_raw.toFixed(3)}`
          : undefined,
      color: "text-emerald-300",
      accentBorder: "border-emerald-500/25 hover:border-emerald-400/50",
    },
    {
      key: "pressure_lambda",
      title: "Pressure",
      symbol: "λ̂",
      value: current.pressure_lambda,
      delta: deltas.pressure_lambda ?? 0,
      threshold: { label: "λ_crit", val: thresholds.lambda_critical },
      color: "text-amber-300",
      accentBorder: "border-amber-500/25 hover:border-amber-400/50",
    },
    {
      key: "entropy_H",
      title: "Entropy",
      symbol: "Ĥ",
      value: current.entropy_H,
      delta: deltas.entropy_H ?? 0,
      color: "text-cyan-300",
      accentBorder: "border-cyan-500/25 hover:border-cyan-400/50",
    },
    {
      key: "energy_E",
      title: "Energy",
      symbol: "E",
      value: current.energy_E,
      delta: deltas.energy_E ?? 0,
      threshold: { label: "τ_E", val: thresholds.tau_E },
      color: "text-purple-300",
      accentBorder: "border-purple-500/25 hover:border-purple-400/50",
    },
    {
      key: "d_hat",
      title: "Fractal Dim",
      symbol: "D̂",
      value: current.d_hat,
      delta: deltas.d_hat ?? 0,
      threshold: { label: "D*_target", val: thresholds.d_hat_target },
      color: "text-sky-300",
      accentBorder: "border-sky-500/25 hover:border-sky-400/50",
    },
    {
      key: "compression_ratio_cr",
      title: "Compression",
      symbol: "CR",
      value: current.compression_ratio_cr,
      delta: deltas.compression_ratio_cr ?? 0,
      subtext: `${evals.total_macros} macros · ${evals.total_merges} merges`,
      color: "text-fuchsia-300",
      accentBorder: "border-fuchsia-500/25 hover:border-fuchsia-400/50",
    },
  ];

  const recentFrames = useMemo(
    () => [...allPoints].reverse().slice(0, 6),
    [allPoints],
  );

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-[#040711] p-4 shadow-[0_0_50px_rgba(15,23,42,0.65)] relative overflow-hidden">
      {/* Subtle sci-fi grid backdrop */}
      <div className="pointer-events-none absolute inset-0 opacity-25 bg-[radial-gradient(circle_at_top_right,rgba(168,85,247,0.16),transparent_45%),radial-gradient(circle_at_bottom_left,rgba(6,182,212,0.14),transparent_45%)]" />

      {/* Section 1: Regime & Lyapunov Stability Banner */}
      <div className="relative z-10 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-black/45 px-4 py-3 backdrop-blur-xl">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider ${
                sseConnected
                  ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
                  : "border-amber-500/40 bg-amber-500/15 text-amber-300"
              }`}
            >
              <Radio
                size={11}
                className={sseConnected ? "animate-pulse text-emerald-400" : ""}
              />
              {sseConnected ? "SSE LIVE" : "POLL SYNC"}
            </span>
            <span
              className={`rounded-full border px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider ${regimeMeta.badge}`}
              title={regimeMeta.hint}
            >
              {regimeMeta.label}
            </span>
            <span
              className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-mono text-[10px] ${
                evals.lyapunov_stable
                  ? "border-cyan-500/35 bg-cyan-500/10 text-cyan-300"
                  : "border-amber-500/35 bg-amber-500/10 text-amber-300"
              }`}
            >
              <ShieldCheck size={11} />
              {evals.lyapunov_stable
                ? "Lyapunov dE/dt ≤ 0"
                : "Transient Energy"}
            </span>
          </div>
          <span className="hidden xl:inline font-mono text-[11px] text-slate-400">
            {regimeMeta.hint}
          </span>
        </div>

        {/* Manifold Health + Topology Counters + Refresh */}
        <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
          <div className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1 text-slate-200">
            <Gauge size={12} className="text-cyan-400" />
            <span className="text-slate-400">Health</span>
            <span className="font-semibold text-cyan-300">
              {evals.manifold_health_score.toFixed(1)}%
            </span>
          </div>
          <div className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1 text-slate-200">
            <Flame size={12} className="text-amber-400" />
            <span className="text-slate-400">Invent Ready</span>
            <span className="font-semibold text-amber-300">
              {evals.invention_readiness.toFixed(0)}%
            </span>
          </div>
          <div className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1 text-slate-300">
            <Layers size={12} className="text-purple-400" />
            <span>{evals.total_nodes} nodes</span>
            <span className="text-slate-500">·</span>
            <span className="text-purple-300">{evals.total_macros} macros</span>
            <span className="text-slate-500">·</span>
            <span className="text-emerald-300">
              {evals.total_theories} theories
            </span>
          </div>
          {streamData && (
            <span className="rounded-lg border border-white/10 bg-white/[0.03] px-2 py-1 text-[10px] text-slate-400">
              seq #{streamData.last_seq} · {evals.sample_count} pts
            </span>
          )}
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/[0.04] px-2.5 py-1 text-xs text-slate-200 hover:bg-white/10 transition-colors"
              title="Refresh physics telemetry stream"
            >
              <RefreshCw size={12} />
              Sync
            </button>
          )}
        </div>
      </div>

      {/* Section 2: 7 Live Invariant KPI Scorecards */}
      <div className="relative z-10 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
        {kpiCards.map((card) => {
          const d = fmtDelta(card.delta);
          const pctVsThreshold = card.threshold
            ? Math.min(
                100,
                Math.max(
                  4,
                  (card.value / Math.max(0.01, card.threshold.val)) * 100,
                ),
              )
            : null;
          const active = visibleSeries[card.key];
          return (
            <button
              key={card.key}
              type="button"
              onClick={() => toggleSeries(card.key)}
              className={`text-left rounded-xl border bg-black/50 p-3 backdrop-blur-md transition-all ${
                card.accentBorder
              } ${active ? "ring-1 ring-white/15" : "opacity-60"}`}
              title={`Click to ${active ? "hide" : "show"} ${card.title} on the trajectory chart`}
            >
              <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-wider text-slate-400">
                <span>{card.title}</span>
                <span className={`font-bold ${card.color}`}>{card.symbol}</span>
              </div>
              <div
                className={`mt-1 font-mono text-base font-bold tracking-tight ${card.color}`}
              >
                {fmt4(card.value)}
              </div>
              <div className="mt-1 flex items-center justify-between gap-1 font-mono text-[10px]">
                <span
                  className={`inline-flex items-center gap-0.5 ${
                    d.tone === "up"
                      ? "text-amber-300"
                      : d.tone === "down"
                        ? "text-emerald-300"
                        : "text-slate-500"
                  }`}
                >
                  {d.tone === "up" && <TrendingUp size={10} />}
                  {d.tone === "down" && <TrendingDown size={10} />}Δ {d.text}
                </span>
                {card.threshold && (
                  <span className="text-slate-500">
                    {card.threshold.label} {card.threshold.val.toFixed(2)}
                  </span>
                )}
              </div>
              {pctVsThreshold !== null ? (
                <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-white/10">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      card.value > (card.threshold?.val ?? 1)
                        ? "bg-amber-400"
                        : "bg-cyan-400/80"
                    }`}
                    style={{ width: `${pctVsThreshold}%` }}
                  />
                </div>
              ) : (
                <div className="mt-2 truncate font-mono text-[9px] text-slate-500">
                  {card.subtext || "live invariant"}
                </div>
              )}
              {pctVsThreshold !== null && card.subtext && (
                <div className="mt-1 truncate font-mono text-[9px] text-slate-500">
                  {card.subtext}
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Section 3: Chart Preset Controls + Multi-Series Telemetry Chart */}
      <div className="relative z-10 rounded-xl border border-white/10 bg-black/45 p-3.5">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            {(
              [
                ["equilibrium", "Equilibrium (R, N, λ̂, Ĥ)"],
                ["geometry", "Energy & Geometry (E, D̂, CR)"],
                ["all", "All 7 Invariants"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => handlePresetChange(id)}
                className={`rounded-lg border px-2.5 py-1 font-mono text-[11px] transition-all ${
                  preset === id
                    ? "border-purple-500/45 bg-purple-500/20 text-purple-200 shadow-sm"
                    : "border-white/8 bg-white/[0.02] text-slate-400 hover:text-slate-200"
                }`}
              >
                {label}
              </button>
            ))}

            <button
              type="button"
              onClick={() => setShowThresholds((v) => !v)}
              className={`rounded-lg border px-2.5 py-1 font-mono text-[11px] transition-all ${
                showThresholds
                  ? "border-cyan-500/40 bg-cyan-500/15 text-cyan-200"
                  : "border-white/8 bg-white/[0.02] text-slate-400 hover:text-slate-200"
              }`}
            >
              Thresholds {showThresholds ? "ON" : "OFF"}
            </button>
          </div>

          <div className="flex items-center gap-1.5 font-mono text-[11px]">
            <span className="text-slate-500 mr-1">Window:</span>
            {(["15", "40", "all"] as const).map((w) => (
              <button
                key={w}
                type="button"
                onClick={() => setWindowSize(w)}
                className={`rounded border px-2 py-0.5 transition-all ${
                  windowSize === w
                    ? "border-sky-500/45 bg-sky-500/20 text-sky-200"
                    : "border-white/8 text-slate-400 hover:text-slate-200"
                }`}
              >
                {w === "all" ? "All" : `Last ${w}`}
              </button>
            ))}
          </div>
        </div>

        {/* Toggleable Series Legend Strip */}
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {SERIES_CONFIG.map((s) => {
            const on = visibleSeries[s.key];
            return (
              <button
                key={s.key}
                type="button"
                onClick={() => toggleSeries(s.key)}
                className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 font-mono text-[11px] transition-all ${
                  on
                    ? "border-white/20 bg-white/[0.06] text-slate-100"
                    : "border-white/5 bg-transparent text-slate-500 line-through"
                }`}
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{
                    backgroundColor: s.color,
                    boxShadow: on ? `0 0 8px ${s.color}` : "none",
                  }}
                />
                {s.label}
              </button>
            );
          })}
        </div>

        {chartPoints.length === 0 ? (
          <div className="flex h-[280px] flex-col items-center justify-center gap-2 font-mono text-xs text-slate-400">
            <Activity size={24} className="text-purple-400 animate-pulse" />
            <span>Awaiting real evolution physics stream frames…</span>
            <span className="text-[11px] text-slate-500">
              Run an evolution cycle or trigger SSE diagnostics telemetry to
              plot live curves.
            </span>
          </div>
        ) : (
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={chartPoints}
                margin={{ top: 12, right: 18, left: -12, bottom: 4 }}
              >
                <defs>
                  {SERIES_CONFIG.map((s) => (
                    <linearGradient
                      key={s.gradId}
                      id={s.gradId}
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="5%"
                        stopColor={s.color}
                        stopOpacity={0.34}
                      />
                      <stop
                        offset="95%"
                        stopColor={s.color}
                        stopOpacity={0.0}
                      />
                    </linearGradient>
                  ))}
                </defs>

                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(148, 163, 184, 0.10)"
                  vertical={false}
                />
                <XAxis
                  dataKey="label"
                  stroke="#64748b"
                  fontSize={10}
                  tickLine={false}
                  axisLine={{ stroke: "rgba(148,163,184,0.16)" }}
                  fontFamily="monospace"
                  minTickGap={18}
                />
                <YAxis
                  stroke="#64748b"
                  fontSize={10}
                  tickLine={false}
                  axisLine={false}
                  fontFamily="monospace"
                  domain={["auto", "auto"]}
                  tickFormatter={(v: number) =>
                    Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(2)
                  }
                />
                <Tooltip content={<PhysicsTooltip />} />

                {showThresholds && visibleSeries.pressure_lambda && (
                  <ReferenceLine
                    y={thresholds.lambda_critical}
                    stroke="#f59e0b"
                    strokeDasharray="4 4"
                    strokeOpacity={0.65}
                    label={{
                      value: `λ_crit=${thresholds.lambda_critical.toFixed(2)}`,
                      position: "insideTopRight",
                      fill: "#fbbf24",
                      fontSize: 10,
                      fontFamily: "monospace",
                    }}
                  />
                )}
                {showThresholds && visibleSeries.redundancy_R && (
                  <ReferenceLine
                    y={thresholds.tau_R}
                    stroke="#f43f5e"
                    strokeDasharray="4 4"
                    strokeOpacity={0.5}
                    label={{
                      value: `τ_R=${thresholds.tau_R.toFixed(2)}`,
                      position: "insideBottomRight",
                      fill: "#fda4af",
                      fontSize: 10,
                      fontFamily: "monospace",
                    }}
                  />
                )}
                {showThresholds && visibleSeries.energy_E && (
                  <ReferenceLine
                    y={thresholds.tau_E}
                    stroke="#a855f7"
                    strokeDasharray="4 4"
                    strokeOpacity={0.5}
                    label={{
                      value: `τ_E=${thresholds.tau_E.toFixed(2)}`,
                      position: "insideTopLeft",
                      fill: "#d8b4fe",
                      fontSize: 10,
                      fontFamily: "monospace",
                    }}
                  />
                )}

                {SERIES_CONFIG.map(
                  (s) =>
                    visibleSeries[s.key] && (
                      <Area
                        key={s.key}
                        type="monotone"
                        dataKey={s.key}
                        name={s.label}
                        stroke={s.color}
                        strokeWidth={2}
                        fillOpacity={1}
                        fill={`url(#${s.gradId})`}
                        isAnimationActive={false}
                        activeDot={{ r: 4, strokeWidth: 0, fill: s.color }}
                      />
                    ),
                )}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Section 4: Recent Telemetry Frame Strip */}
      {recentFrames.length > 0 && (
        <div className="relative z-10 rounded-xl border border-white/10 bg-black/45 p-3">
          <div className="mb-2 flex items-center justify-between font-mono text-[10px] uppercase tracking-wider text-slate-400">
            <span className="inline-flex items-center gap-1.5">
              <Cpu size={12} className="text-purple-400" />
              Live Telemetry Frames (Newest First)
            </span>
            <span>
              Theory Eval: {evals.total_theories} · Macro Comp Efficiency:{" "}
              {evals.compression_efficiency.toFixed(1)}%
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-[11px]">
              <thead>
                <tr className="border-b border-white/10 text-[10px] uppercase text-slate-500">
                  <th className="py-1.5 pr-3">Seq</th>
                  <th className="py-1.5 pr-3">Time</th>
                  <th className="py-1.5 pr-3">Event</th>
                  <th className="py-1.5 pr-3 text-rose-300">R</th>
                  <th className="py-1.5 pr-3 text-emerald-300">N</th>
                  <th className="py-1.5 pr-3 text-amber-300">λ̂</th>
                  <th className="py-1.5 pr-3 text-cyan-300">Ĥ</th>
                  <th className="py-1.5 pr-3 text-purple-300">E</th>
                  <th className="py-1.5 pr-3 text-sky-300">D̂</th>
                  <th className="py-1.5 pr-3 text-fuchsia-300">CR</th>
                  <th className="py-1.5 text-right">Cycles Δ</th>
                </tr>
              </thead>
              <tbody>
                {recentFrames.map((f) => (
                  <tr
                    key={`${f.seq}-${f.label}`}
                    className="border-b border-white/5 hover:bg-white/[0.03]"
                  >
                    <td className="py-1.5 pr-3 text-slate-400">#{f.seq}</td>
                    <td className="py-1.5 pr-3 text-slate-300">{f.label}</td>
                    <td className="py-1.5 pr-3">
                      <span
                        className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[9px] ${actionBadgeStyle(
                          f.action,
                        )}`}
                      >
                        <GitBranch size={9} />
                        {f.action}
                      </span>
                    </td>
                    <td className="py-1.5 pr-3 text-rose-300">
                      {fmt4(f.redundancy_R)}
                    </td>
                    <td className="py-1.5 pr-3 text-emerald-300">
                      {fmt4(f.novelty_N)}
                    </td>
                    <td className="py-1.5 pr-3 text-amber-300">
                      {fmt4(f.pressure_lambda)}
                    </td>
                    <td className="py-1.5 pr-3 text-cyan-300">
                      {fmt4(f.entropy_H)}
                    </td>
                    <td className="py-1.5 pr-3 text-purple-300">
                      {fmt4(f.energy_E)}
                    </td>
                    <td className="py-1.5 pr-3 text-sky-300">
                      {fmt4(f.d_hat)}
                    </td>
                    <td className="py-1.5 pr-3 text-fuchsia-300">
                      {fmt4(f.compression_ratio_cr)}
                    </td>
                    <td className="py-1.5 text-right text-slate-400">
                      <span className="inline-flex items-center gap-1">
                        <Sparkles size={10} className="text-purple-400" />+
                        {f.merges_count}m / +{f.macros_count}i
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
