"use client";

/* eslint-disable react/jsx-key --
   Table cell JSX lives in row arrays passed to <DTable/>, which assigns
   stable keys to every row and cell at render time. */

import React, {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Braces,
  CheckCircle2,
  ChevronDown,
  CircleDashed,
  Database,
  Dna,
  FlaskConical,
  GitMerge,
  GraduationCap,
  Layers,
  Lock,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Table as TableIcon,
  X,
  Zap,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/* =============================================================================
   FAIM Evolution — User Manual
   Full-screen reference: architecture, algorithm internals, API, UI guide.
============================================================================= */

type TocItem = {
  id: string;
  label: string;
  children?: { id: string; label: string }[];
};

const TOC: TocItem[] = [
  {
    id: "overview",
    label: "1. Introduction",
    children: [
      { id: "overview-what", label: "What is Self-Evolution" },
      { id: "overview-new", label: "What's New — Phase 0032" },
      { id: "overview-quickstart", label: "Quick Start" },
    ],
  },
  {
    id: "journey",
    label: "2. How Evolution Works — End to End",
    children: [
      { id: "journey-what", label: "What Evolution Is" },
      { id: "journey-page", label: "What the Page Shows" },
      { id: "journey-run", label: "What Happens When You Press Run" },
      { id: "journey-learn", label: "How It Gets Smarter Over Time" },
      { id: "journey-self", label: "The Three Self Capabilities" },
    ],
  },
  {
    id: "architecture",
    label: "3. Architecture",
    children: [
      { id: "arch-system", label: "System Overview" },
      { id: "arch-map", label: "Component Map" },
      { id: "arch-dataflow", label: "Data Flow" },
    ],
  },
  {
    id: "cycle",
    label: "4. Evolution Cycle",
    children: [
      { id: "cycle-before", label: "Before: Diagnostics & Context" },
      { id: "cycle-during", label: "During: Merge / Prune / Invent" },
      { id: "cycle-after", label: "After: Reward & Persistence" },
      { id: "cycle-probe", label: "The Retrieval Probe" },
    ],
  },
  {
    id: "knobs",
    label: "5. Learnable Knobs",
    children: [
      { id: "knobs-four", label: "The Four Knobs" },
      { id: "knobs-grids", label: "Action Grids" },
      { id: "knobs-defaults", label: "Defaults vs Learned" },
    ],
  },
  {
    id: "winner",
    label: "6. Semantic Winner Selection",
    children: [
      { id: "winner-problem", label: "Why Hash Order Failed" },
      { id: "winner-score", label: "The 5-Term Score" },
      { id: "winner-flow", label: "Decision Flow" },
    ],
  },
  {
    id: "bandit",
    label: "7. LinUCB Contextual Bandit",
    children: [
      { id: "bandit-how", label: "How It Works" },
      { id: "bandit-math", label: "The Math" },
      { id: "bandit-explore", label: "Exploration vs Exploitation" },
    ],
  },
  {
    id: "reward",
    label: "8. Reward & Lambda Calibration",
    children: [
      { id: "reward-formula", label: "Reward Formula" },
      { id: "reward-lambda", label: "Lambda Calibration (Welford)" },
    ],
  },
  {
    id: "meta",
    label: "9. Meta-Metrics & Maturity",
    children: [
      { id: "meta-five", label: "The Five Metrics" },
      { id: "meta-alerts", label: "Alert Conditions" },
    ],
  },
  {
    id: "storage",
    label: "10. Storage & Persistence",
    children: [
      { id: "storage-tables", label: "Database Tables" },
      { id: "storage-schema", label: "Schema v2 & Migration" },
    ],
  },
  {
    id: "api",
    label: "11. API Reference",
    children: [
      { id: "api-endpoints", label: "Endpoints" },
      { id: "api-samples", label: "Response Shapes" },
    ],
  },
  {
    id: "frontend",
    label: "12. Frontend Guide",
    children: [
      { id: "frontend-panes", label: "Dashboard Panes" },
      { id: "frontend-visuals", label: "Visual Sub-Tabs" },
      { id: "frontend-learning", label: "Learning & Self-Optimization Panel" },
    ],
  },
  {
    id: "config",
    label: "13. Configuration",
    children: [{ id: "config-flags", label: "Feature Flags & Env Vars" }],
  },
  {
    id: "invention",
    label: "14. The Invention Engine",
    children: [
      { id: "invention-modes", label: "Self-Invent Modes" },
      { id: "invention-overrides", label: "Invention Overrides" },
      { id: "invention-types", label: "Cognitive Types" },
    ],
  },
  {
    id: "prune",
    label: "15. Prune Policy & Protection",
    children: [
      { id: "prune-rules", label: "Prune Rules" },
      { id: "prune-protection", label: "Macro Protection" },
    ],
  },
  {
    id: "invariants",
    label: "16. Invariants & Diagnostics",
    children: [
      { id: "invariants-seven", label: "The Seven Metrics" },
      { id: "invariants-context", label: "How Context Uses Them" },
    ],
  },
  {
    id: "events",
    label: "17. Events & Timeline",
    children: [{ id: "events-kinds", label: "Event Kinds" }],
  },
  {
    id: "modes",
    label: "18. Profiles & Persist Modes",
    children: [
      { id: "modes-profile", label: "Profiles" },
      { id: "modes-persist", label: "Persist Modes & Durability" },
    ],
  },
  {
    id: "response",
    label: "19. Evolve Response Reference",
    children: [{ id: "response-fields", label: "Response Fields" }],
  },
  {
    id: "faq",
    label: "20. Troubleshooting & FAQ",
  },
];

/* ------------------------------- styling kit ------------------------------- */

const K = {
  card: "rounded-[16px] border border-white/8 bg-white/[0.03] p-4",
  sub: "text-[10px] font-medium uppercase tracking-widest text-slate-500",
  mono: "font-mono",
  chip: "rounded-md border border-white/8 bg-white/[0.04] px-1.5 py-0.5 font-mono text-[10px] text-slate-300",
};

function SectionHeading({
  id,
  kicker,
  title,
  children,
}: {
  id: string;
  kicker: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24 border-b border-white/6 pb-10">
      <div className="mb-5">
        <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-fuchsia-300/80">
          {kicker}
        </p>
        <h2 className="mt-1 text-xl font-semibold tracking-tight text-white">
          {title}
        </h2>
      </div>
      <div className="space-y-4 text-sm leading-relaxed text-slate-300">
        {children}
      </div>
    </section>
  );
}

function SubHeading({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h3 id={id} className="scroll-mt-24 pt-5 text-sm font-semibold text-cyan-200">
      {children}
    </h3>
  );
}

function Callout({
  tone,
  title,
  children,
}: {
  tone: "info" | "success" | "warn";
  title: string;
  children: React.ReactNode;
}) {
  const tones = {
    info: { border: "border-sky-400/30", bg: "bg-sky-400/[0.06]", text: "text-sky-300", Icon: FlaskConical },
    success: { border: "border-emerald-400/30", bg: "bg-emerald-400/[0.06]", text: "text-emerald-300", Icon: CheckCircle2 },
    warn: { border: "border-amber-400/30", bg: "bg-amber-400/[0.06]", text: "text-amber-300", Icon: AlertTriangle },
  } as const;
  const t = tones[tone];
  const Icon = t.Icon;
  return (
    <div className={`flex gap-3 rounded-[14px] border ${t.border} ${t.bg} p-4`}>
      <Icon size={16} className={`mt-0.5 shrink-0 ${t.text}`} />
      <div>
        <p className={`text-xs font-semibold ${t.text}`}>{title}</p>
        <div className="mt-1 text-xs leading-relaxed text-slate-300">{children}</div>
      </div>
    </div>
  );
}

function DTable({ head, rows }: { head: string[]; rows: React.ReactNode[][] }) {
  return (
    <div className="overflow-x-auto rounded-[14px] border border-white/8">
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="border-b border-white/8 text-[10px] uppercase tracking-widest text-slate-500">
            {head.map((h) => (
              <th key={h} className="px-3 py-2 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              className="border-b border-white/4 last:border-b-0 text-slate-300"
            >
              {row.map((cell, j) => (
                <td key={j} className="px-3 py-2 align-top">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ChartFrame({ caption, children }: { caption: string; children: React.ReactNode }) {
  return (
    <div className={`${K.card} !p-0 overflow-hidden`}>
      <div className="border-b border-white/6 px-4 py-2">
        <p className="font-mono text-[10px] uppercase tracking-widest text-slate-500">
          {caption}
        </p>
      </div>
      <div className="p-3">{children}</div>
    </div>
  );
}

const AXIS_TICK = { fill: "#64748b", fontSize: 10, fontFamily: "monospace" } as const;

/* ------------------------------ SVG diagrams ------------------------------- */

function ArchitectureDiagram() {
  const layers: { title: string; accent: string; items: string[] }[] = [
    {
      title: "Presentation — React / Next.js",
      accent: "#38bdf8",
      items: ["Evolution Control Plane", "Learning & Self-Optimization Panel", "Invention Flow Canvas", "Physics Stream"],
    },
    {
      title: "API — FastAPI Routers",
      accent: "#c084fc",
      items: ["/evolve (POST)", "/evolve/status · /evolve/control", "/evolve/invention/flow", "/evolve/learning/{state|outcomes|meta}"],
    },
    {
      title: "Orchestration — evolve_flow.py",
      accent: "#f472b6",
      items: ["Context build (R,N,D,H,λ,node_count)", "LinUCB resolve_knobs(context)", "Retrieval probe (before · after)", "Learning outcome + meta-metrics"],
    },
    {
      title: "Core Dynamics — evolution_native.py",
      accent: "#34d399",
      items: ["evolve_once (merge · prune · invent)", "Semantic winner selection", "D/H/λ diagnostics"],
    },
    {
      title: "Storage — PostgreSQL",
      accent: "#fbbf24",
      items: ["evolution_outcomes", "evolution_policy_state", "evolution_meta_metrics", "nodes · edges · events"],
    },
  ];
  return (
    <div className="space-y-2">
      {layers.map((layer, i) => (
        <div key={layer.title}>
          <div className="relative rounded-[14px] border bg-white/[0.02] p-3" style={{ borderColor: `${layer.accent}33` }}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-md px-2 py-1 font-mono text-[9px] font-semibold uppercase tracking-[0.14em]" style={{ backgroundColor: `${layer.accent}1E`, color: layer.accent }}>
                Layer {i + 1} · {layer.title}
              </span>
              {layer.items.map((item) => (
                <span key={item} className={K.chip}>
                  {item}
                </span>
              ))}
            </div>
          </div>
          {i < layers.length - 1 && (
            <div className="flex justify-center py-0.5 text-slate-600">
              <ChevronDown size={14} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function CycleDiagram() {
  const steps = [
    { accent: "#38bdf8", title: "BEFORE", desc: "Diagnostics snapshot: R, N, D, H, λ, node_count", note: "probe retrieval quality" },
    { accent: "#c084fc", title: "RESOLVE", desc: "LinUCB picks merge/prune/invent knobs for this context", note: "epsilon-greedy 10%" },
    { accent: "#f472b6", title: "EXECUTE", desc: "evolve_once: merges (semantic winner), prunes, inventions", note: "hard-bounded knobs" },
    { accent: "#34d399", title: "MEASURE", desc: "After diagnostics + retrieval probe again", note: "delta = (after − before)/before" },
    { accent: "#fbbf24", title: "REWARD", desc: "composite reward in [−1,1] feeds ridge regression", note: "blends retrieval 40%" },
    { accent: "#fb7185", title: "PERSIST", desc: "outcome row + meta-metrics + policy state v+1", note: "best effort, fail-open" },
  ];
  return (
    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {steps.map((step, i) => (
        <div key={step.title} className="relative rounded-[14px] border bg-white/[0.02] p-3" style={{ borderColor: `${step.accent}33` }}>
          <div className="flex items-center justify-between">
            <span className="font-mono text-[9px] font-semibold uppercase tracking-[0.16em]" style={{ color: step.accent }}>
              {String(i + 1).padStart(2, "0")} · {step.title}
            </span>
            {i < steps.length - 1 && <ArrowRight size={12} className="text-slate-600" />}
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-slate-300">{step.desc}</p>
          <p className="mt-1 font-mono text-[10px] text-slate-500">{step.note}</p>
        </div>
      ))}
    </div>
  );
}

function WinnerFlowDiagram() {
  const boxes = [
    { x: 30, y: 12, w: 300, h: 40, label: "Candidate pair (node_a, node_b)", accent: "#38bdf8" },
    { x: 30, y: 80, w: 300, h: 40, label: "score_a vs score_b (5-term semantic)", accent: "#c084fc" },
    { x: 30, y: 148, w: 300, h: 40, label: "Tie? → legacy vector_hash rule", accent: "#f472b6" },
    { x: 30, y: 216, w: 300, h: 40, label: "Winner keeps info → loser merged away", accent: "#34d399" },
  ];
  return (
    <div className="overflow-x-auto">
      <svg viewBox="0 0 360 280" className="w-full max-w-[460px]">
        {boxes.map((b, i) => (
          <g key={i}>
            <rect x={b.x} y={b.y} width={b.w} height={b.h} rx={10} fill={`${b.accent}14`} stroke={`${b.accent}55`} />
            <text x={b.x + b.w / 2} y={b.y + 25} textAnchor="middle" fill={b.accent} fontSize="11" fontFamily="monospace">
              {String(i + 1).padStart(2, "0")}
            </text>
            <text x={b.x + b.w / 2} y={b.y + 25 + 12} textAnchor="middle" fill="#cbd5e1" fontSize="11">
              {b.label}
            </text>
            {i < boxes.length - 1 && (
              <line x1={180} y1={b.y + b.h} x2={180} y2={b.y + b.h + 16} stroke="#475569" strokeWidth="1.5" />
            )}
          </g>
        ))}
        <text x={180} y={272} textAnchor="middle" fill="#64748b" fontSize="9" fontFamily="monospace">
          deterministic · auditable · fallback on any error
        </text>
      </svg>
    </div>
  );
}

/* ------------------------------ recharts data ------------------------------ */

const SCORE_WEIGHTS = [
  { name: "Evidence", weight: 25, fill: "#38bdf8" },
  { name: "Usage", weight: 20, fill: "#c084fc" },
  { name: "Recency", weight: 15, fill: "#f472b6" },
  { name: "Source", weight: 20, fill: "#34d399" },
  { name: "Residual", weight: 20, fill: "#fbbf24" },
];

const REWARD_BLEND = [
  { name: "Redundancy ↓", pct: 50, fill: "#38bdf8" },
  { name: "Boundedness ↑", pct: 30, fill: "#34d399" },
  { name: "Novelty held", pct: 20, fill: "#c084fc" },
];

const RETRIEVAL_BLEND = [
  { name: "Outcome reward", pct: 60, fill: "#38bdf8" },
  { name: "Retrieval delta", pct: 40, fill: "#f472b6" },
];

const GRID_DATA = [
  { name: "merge_threshold", values: "0.90 · 0.92 · 0.94 · 0.95 · 0.96 · 0.97 · 0.98" },
  { name: "prune_similarity_threshold", values: "0.93 · 0.95 · 0.96 · 0.97 · 0.98 · 0.99" },
  { name: "prune_min_age_days", values: "3 · 5 · 7 · 10 · 14 · 21" },
  { name: "lambda_threshold", values: "0.15 · 0.20 · 0.25 · 0.30 · 0.35 · 0.40 · 0.50" },
];

const GRID_SPREAD = [
  { name: "merge", spread: 7 },
  { name: "prune-sim", spread: 6 },
  { name: "age", spread: 6 },
  { name: "lambda", spread: 7 },
];

const EXPLORE_CURVE = [
  { n: "0", bonus: 1.6 },
  { n: "2", bonus: 1.1 },
  { n: "5", bonus: 0.72 },
  { n: "10", bonus: 0.51 },
  { n: "20", bonus: 0.36 },
  { n: "50", bonus: 0.23 },
  { n: "100", bonus: 0.16 },
  { n: "200", bonus: 0.11 },
];

const META_TREND = [
  { cycle: "c1", usefulness: 0.42, utilization: 0.1, regret: 0.31 },
  { cycle: "c2", usefulness: 0.55, utilization: 0.22, regret: 0.24 },
  { cycle: "c3", usefulness: 0.63, utilization: 0.33, regret: 0.18 },
  { cycle: "c4", usefulness: 0.71, utilization: 0.41, regret: 0.12 },
  { cycle: "c5", usefulness: 0.78, utilization: 0.5, regret: 0.08 },
  { cycle: "c6", usefulness: 0.83, utilization: 0.56, regret: 0.05 },
];

const LEARNED_TRACK = [
  { cycle: "v0", merge: 0.95, prune: 0.98, age: 7, lambda: 0.3 },
  { cycle: "v1", merge: 0.95, prune: 0.98, age: 7, lambda: 0.3 },
  { cycle: "v5", merge: 0.94, prune: 0.97, age: 5, lambda: 0.31 },
  { cycle: "v10", merge: 0.93, prune: 0.96, age: 5, lambda: 0.32 },
  { cycle: "v20", merge: 0.92, prune: 0.96, age: 3, lambda: 0.33 },
  { cycle: "v30", merge: 0.91, prune: 0.95, age: 3, lambda: 0.34 },
];

/* ================================= manual ================================== */

export function EvolutionManual({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [activeId, setActiveId] = useState<string>("overview");
  const contentRef = useRef<HTMLDivElement | null>(null);

  const allIds = useMemo(() => {
    const ids: string[] = [];
    for (const item of TOC) {
      ids.push(item.id);
      for (const child of item.children ?? []) ids.push(child.id);
    }
    return ids;
  }, []);

  useEffect(() => {
    if (!open) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActiveId(entry.target.id);
        }
      },
      { root: contentRef.current, rootMargin: "-10% 0px -75% 0px" },
    );
    for (const id of allIds) {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [allIds, open]);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  const scrollTo = (id: string) => {
    setActiveId(id);
    const el = document.getElementById(id);
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-[100] flex flex-col bg-[#04060c]/97 backdrop-blur-xl text-slate-100">
      {/* Top bar */}
      <div className="flex items-center justify-between gap-4 border-b border-white/8 bg-black/40 px-5 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-fuchsia-400/30 bg-fuchsia-400/10 text-fuchsia-300">
            <BookOpen size={16} />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-semibold tracking-tight text-white">
              FAIM Evolution — User Manual
            </p>
            <p className="truncate font-mono text-[10px] uppercase tracking-widest text-slate-500">
              Self-Evolving Knowledge Graph · Phase 0032 · v2
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden sm:inline-flex rounded-lg border border-emerald-400/30 bg-emerald-400/10 px-2 py-1 font-mono text-[10px] text-emerald-300">
            READ-ONLY
          </span>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 text-slate-300 transition-colors hover:bg-white/5 hover:text-white"
            aria-label="Close manual"
          >
            <X size={15} />
          </button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        {/* Left: TOC */}
        <aside className="hidden w-[300px] shrink-0 border-r border-white/8 bg-black/30 lg:block overflow-y-auto custom-scrollbar">
          <div className="p-4">
            <p className="px-2 font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
              Table of Contents
            </p>
            <nav className="mt-3 space-y-1">
              {TOC.map((item) => {
                const active = activeId === item.id;
                const childActive = item.children?.some((c) => c.id === activeId);
                return (
                  <div key={item.id}>
                    <button
                      type="button"
                      onClick={() => scrollTo(item.id)}
                      className={`flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-left text-xs transition-colors ${
                        active || childActive
                          ? "bg-fuchsia-400/10 text-fuchsia-200"
                          : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
                      }`}
                    >
                      <span className={active || childActive ? "font-semibold" : ""}>
                        {item.label}
                      </span>
                      {childActive && !active && (
                        <span className="h-1.5 w-1.5 rounded-full bg-fuchsia-400" />
                      )}
                    </button>
                    {item.children && (active || childActive) && (
                      <div className="ml-3 space-y-0.5 border-l border-white/8 pl-2">
                        {item.children.map((child) => (
                          <button
                            key={child.id}
                            type="button"
                            onClick={() => scrollTo(child.id)}
                            className={`block w-full rounded-md px-2 py-1.5 text-left text-[11px] transition-colors ${
                              activeId === child.id
                                ? "bg-cyan-400/10 text-cyan-200 font-medium"
                                : "text-slate-500 hover:text-slate-300"
                            }`}
                          >
                            {child.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </nav>
          </div>
        </aside>

        {/* Mobile TOC chips */}
        <div className="lg:hidden border-b border-white/8 bg-black/30 px-4 py-2 overflow-x-auto custom-scrollbar">
          <div className="flex gap-1.5">
            {TOC.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => scrollTo(item.id)}
                className={`shrink-0 rounded-lg border px-2.5 py-1.5 text-[10px] font-mono transition-colors ${
                  activeId === item.id
                    ? "border-fuchsia-400/40 bg-fuchsia-400/10 text-fuchsia-200"
                    : "border-white/10 text-slate-400"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {/* Right: content preview */}
        <main
          ref={contentRef}
          className="min-w-0 flex-1 overflow-y-auto custom-scrollbar"
        >
          <div className="mx-auto max-w-4xl space-y-10 px-5 py-8 sm:px-8">
            {/* ============ 1. INTRODUCTION ============ */}
            <SectionHeading id="overview" kicker="Chapter 01" title="Introduction">
              <p>
                FAIM's Evolution system is the autonomous maintenance engine of
                your knowledge graph. Each cycle it scans for redundancy,
                merges near-duplicate atoms, prunes stale or contradictory
                structure, and invents higher-order abstractions (macros) —
                all while preserving novel information.
              </p>
              <SubHeading id="overview-what">What is Self-Evolution</SubHeading>
              <p>
                A single evolution cycle (POST /api/v1/evolve) runs four
                operations against the active graph:{" "}
                <span className="font-mono text-cyan-300">merge</span> (collapse
                redundant atoms), <span className="font-mono text-cyan-300">prune</span>{" "}
                (remove stale/contradictory structure),{" "}
                <span className="font-mono text-cyan-300">invent</span> (form
                macros from recurring evidence), and{" "}
                <span className="font-mono text-cyan-300">theorize</span> (derive
                explanations). Before and after every cycle the system measures
                five invariants: redundancy (R), novelty (N), dimension (D),
                entropy (H), and pressure (λ).
              </p>
              <SubHeading id="overview-new">What's New — Phase 0032</SubHeading>
              <p>This manual covers the Phase 0032 "self-optimizing" release:</p>
              <DTable
                head={["Capability", "Before", "Now"]}
                rows={[
                  [
                    "Evolution constants",
                    "Fixed (merge 0.95, prune 0.98 …)",
                    <span className="text-emerald-300">Learned per graph via LinUCB</span>,
                  ],
                  [
                    "Merge winner",
                    "Lexicographic vector hash",
                    <span className="text-emerald-300">Semantic 5-term information score</span>,
                  ],
                  [
                    "λ threshold",
                    "Fixed 0.30",
                    <span className="text-emerald-300">Welford-calibrated from graph history</span>,
                  ],
                  [
                    "Retrieval quality",
                    "Not measured",
                    <span className="text-emerald-300">Probed before/after, feeds reward</span>,
                  ],
                  [
                    "Maturity proof",
                    "None",
                    <span className="text-emerald-300">Meta-metrics per cycle (5 metrics + alerts)</span>,
                  ],
                  [
                    "Observability",
                    "None",
                    <span className="text-emerald-300">3 read-only API endpoints + UI panel</span>,
                  ],
                ]}
              />
              <SubHeading id="overview-quickstart">Quick Start</SubHeading>
              <div className="space-y-2 font-mono text-xs text-slate-300">
                <p className="rounded-lg border border-white/8 bg-black/40 px-3 py-2">
                  <span className="text-fuchsia-300">$</span> export FAIM_EVOLUTION_LEARNING_ENABLED=true
                </p>
                <p className="rounded-lg border border-white/8 bg-black/40 px-3 py-2">
                  <span className="text-fuchsia-300">$</span> python -m store.pg.migrate up&nbsp;&nbsp;<span className="text-slate-500"># applies migration 0032 (3 tables)</span>
                </p>
                <p className="rounded-lg border border-white/8 bg-black/40 px-3 py-2">
                  <span className="text-fuchsia-300">$</span> Open <span className="text-cyan-300">Dashboard → Evolution</span>, run a cycle, then watch the Learning panel fill with outcomes.
                </p>
              </div>
              <Callout tone="info" title="Opt-in by design">
                Learning is disabled by default. With the flag off, evolution
                behaves byte-for-byte as before — defaults are used and no rows
                are written.
              </Callout>
            </SectionHeading>

            {/* ============ 2. HOW EVOLUTION WORKS ============ */}
            <SectionHeading id="journey" kicker="Chapter 02" title="How Evolution Works — End to End">
              <p>
                If you read only one chapter, read this one. It tells the whole
                story in plain words — from pressing Run to the graph getting
                smarter on its own. Every later chapter goes deep into one
                piece of this journey.
              </p>
              <SubHeading id="journey-what">What Evolution Is</SubHeading>
              <p>
                Your knowledge graph is a growing collection of facts, stored
                as connected nodes. Over time it gets messy: duplicate facts,
                stale facts, forgotten connections. <strong>Evolution is the
                automatic cleanup-and-organize crew</strong>. It merges
                near-duplicates into one, removes what's old and unused, and
                creates higher-level summary facts ("macros") out of patterns
                it spots. Left alone, the graph keeps itself tidy.
              </p>
              <SubHeading id="journey-page">What the Page Shows</SubHeading>
              <p>The Evolution page is the control room for this crew:</p>
              <DTable
                head={["Screen", "What you see"]}
                rows={[
                  [
                    <span className="text-sky-300">Overview & Controls</span>,
                    "The dashboard: how healthy the graph is, switches for the autonomous features, and the Run Evolution button",
                  ],
                  [
                    <span className="text-purple-300">Physics & Topology</span>,
                    "The pretty part: a diagram of your facts flowing through the pipeline, plus charts of the graph's health over time",
                  ],
                  [
                    <span className="text-emerald-300">Timeline & Logs</span>,
                    "The history feed: every action the crew takes, logged as an event",
                  ],
                  [
                    <span className="text-fuchsia-300">Learning panel</span>,
                    "The memory: what settings the system has learned, how confident it is, and scorecards proving the graph is improving",
                  ],
                ]}
              />
              <SubHeading id="journey-run">What Happens When You Press Run</SubHeading>
              <p>The full journey, step by step:</p>
              <DTable
                head={["Step", "What happens", "Where you see it"]}
                rows={[
                  [
                    "1 · It looks around",
                    "The system measures the graph: how much duplication exists, how much new information, how organized it is",
                    "Scorecard cards refresh",
                  ],
                  [
                    "2 · It decides how aggressive to be",
                    "It picks its settings for THIS graph, in THIS situation — tight or loose merge threshold, young or old enough to prune, when to invent",
                    "Learning panel shows the chosen knobs",
                  ],
                  [
                    "3 · It merges duplicates",
                    "Near-identical facts combine into one. The better fact survives — the one with more evidence, more use, more recent activity",
                    "Invention flow diagram updates",
                  ],
                  [
                    "4 · It prunes stale facts",
                    "Old, unused, contradictory facts are removed — but the big summary macros are never touched",
                    "Timeline logs the prunes",
                  ],
                  [
                    "5 · It invents summaries",
                    "Recurring patterns become new higher-level macros",
                    "Timeline logs the inventions",
                  ],
                  [
                    "6 · It checks the result",
                    "Did duplication actually drop? Did searching the graph get better? It measures before and after",
                    "Physics charts move",
                  ],
                  [
                    "7 · It remembers",
                    "It writes everything to the database: what it did, whether it helped, and the graph's new state",
                    "Learning panel fills with outcomes + scorecards",
                  ],
                  [
                    "8 · It reports back",
                    "The cycle completes and every panel refreshes so you see the result instantly",
                    "Green 'completed' toast + refreshed page",
                  ],
                ]}
              />
              <SubHeading id="journey-learn">How It Gets Smarter Over Time</SubHeading>
              <p>
                This is the heart of "self-improving". Every run, the system
                remembers what worked and what didn't, in the situation it was
                in:
              </p>
              <ul className="list-disc space-y-1 pl-5 text-slate-300">
                <li>
                  If an aggressive cleanup clearly helped a messy graph, it
                  learns <em>"for messy graphs, be more aggressive"</em>.
                </li>
                <li>
                  If it cleaned too hard and destroyed useful information, it
                  learns <em>"for this kind of graph, be gentler"</em>.
                </li>
                <li>
                  After enough cycles it stops guessing and starts picking the
                  right settings for your graph automatically — like a chef who
                  learns your taste after a few meals.
                </li>
              </ul>
              <Callout tone="success" title="The full loop">
                Click Run → it cleans → it measures → it learns → next run is
                smarter. Each cycle feeds the next, forever.
              </Callout>
              <SubHeading id="journey-self">The Three Self Capabilities</SubHeading>
              <DTable
                head={["Capability", "What it does", "Switch"]}
                rows={[
                  [
                    <span className="text-sky-300">Self-evolve</span>,
                    "Runs evolution automatically — after uploads or on a schedule — without you pressing anything",
                    <span className="font-mono">FAIM_SELF_EVOLVE_ENABLED</span>,
                  ],
                  [
                    <span className="text-purple-300">Self-invent</span>,
                    "Creates the summary macros automatically",
                    <span className="font-mono">Self-invent mode (Off / On evolve / After upload / Both)</span>,
                  ],
                  [
                    <span className="text-fuchsia-300">Self-improve</span>,
                    "Adjusts its own settings based on what worked before",
                    <span className="font-mono">FAIM_EVOLUTION_LEARNING_ENABLED</span>,
                  ],
                ]}
              />
              <Callout tone="info" title="Nothing breaks">
                All three are switches. Turn them off and the system behaves
                exactly as it did before learning existed — your graph is never
                at risk.
              </Callout>
            </SectionHeading>

            {/* ============ 3. ARCHITECTURE ============ */}
            <SectionHeading id="architecture" kicker="Chapter 03" title="Architecture">
              <SubHeading id="arch-system">System Overview</SubHeading>
              <ArchitectureDiagram />
              <SubHeading id="arch-map">Component Map</SubHeading>
              <DTable
                head={["Component", "Path", "Role"]}
                rows={[
                  [
                    "Winner selection",
                    <span className="font-mono">core/dynamics/winner_selection.py</span>,
                    "5-term semantic score; picks merge winners; tie-breaks on legacy hash",
                  ],
                  [
                    "Policy learner",
                    <span className="font-mono">core/learning/evolution_policy.py</span>,
                    "LinUCB arms per knob, Welford λ calibration, reward math, schema v2",
                  ],
                  [
                    "Evolution core",
                    <span className="font-mono">core/dynamics/evolution_native.py</span>,
                    "evolve_once — merge/prune/invent engine with injectable winner selector",
                  ],
                  [
                    "Orchestration",
                    <span className="font-mono">orchestration/evolve_flow.py</span>,
                    "Context build, knob resolution, retrieval probes, outcome + meta-metrics recording",
                  ],
                  [
                    "Persistence",
                    <span className="font-mono">store/pg/repos/evolution_learning_repo.py</span>,
                    "Fail-closed reads, fail-open writes for the 3 new tables",
                  ],
                  [
                    "API",
                    <span className="font-mono">api/routers/evolve.py</span>,
                    "Invention flow + 3 read-only learning endpoints",
                  ],
                ]}
              />
              <SubHeading id="arch-dataflow">Data Flow</SubHeading>
              <p>
                One cycle, end to end: the frontend posts an evolve request →
                the flow builds pre-cycle diagnostics → the policy resolves
                learned knobs for that exact context → evolve_once executes
                with the semantic winner selector → post-cycle diagnostics and
                a second retrieval probe are taken → the reward updates the
                bandits → outcome, meta-metrics, and policy state are persisted
                → the learning summary returns to the UI.
              </p>
              <Callout tone="success" title="Deterministic & auditable">
                Every knob decision, score component, reward, and alert is
                persisted in JSONB — the full reasoning trail survives restarts.
              </Callout>
            </SectionHeading>

            {/* ============ 3. EVOLUTION CYCLE ============ */}
            <SectionHeading id="cycle" kicker="Chapter 04" title="Evolution Cycle">
              <CycleDiagram />
              <SubHeading id="cycle-before">Before: Diagnostics & Context</SubHeading>
              <p>
                The flow snapshots the graph state into a feature vector used
                by the bandits:{" "}
                <span className="font-mono text-cyan-300">[1, R, N, D, H, node_count/1000]</span>.
                Missing fields default to 0; R, N, D, H are clamped to [0,1].
              </p>
              <SubHeading id="cycle-during">During: Merge / Prune / Invent</SubHeading>
              <p>
                With learning enabled, the resolved knobs override the fixed
                constants: merge threshold, prune similarity threshold, prune
                minimum age, and the invention λ threshold. Each merge uses the
                semantic winner selector (Chapter 6). The core never exceeds
                its action budget and never leaves the knob safety ranges.
              </p>
              <SubHeading id="cycle-after">After: Reward & Persistence</SubHeading>
              <p>
                Post-cycle diagnostics are compared with the before snapshot.
                A composite reward in [−1, 1] (Chapter 8) is computed and fed
                to every bandit arm that acted, the Welford calibration ingests
                the new λ, and three rows are persisted: an outcome, a
                meta-metric snapshot, and the updated policy state (version
                incremented).
              </p>
              <SubHeading id="cycle-probe">The Retrieval Probe</SubHeading>
              <p>
                The probe answers: <em>"did evolution make the graph more
                retrievable?"</em> It deterministically samples the 3 most-used
                nodes, runs local cosine top-3 retrieval per sample, and scores
                each hit set as{" "}
                <span className="font-mono">0.5·mean_similarity + 0.5·(1 − mean_pairwise_sim)</span>{" "}
                — rewarding results that are relevant <em>and</em> diverse. The
                relative delta between before/after probes (clamped to ±1) feeds
                40% of the reward and is stored on every outcome row.
              </p>
              <Callout tone="warn" title="Probe is best-effort">
                If the graph has fewer than 2 vectorized nodes, or any step
                fails, the probe returns null and the reward falls back to the
                pure metric blend — the cycle is never blocked.
              </Callout>
            </SectionHeading>

            {/* ============ 4. LEARNABLE KNOBS ============ */}
            <SectionHeading id="knobs" kicker="Chapter 05" title="Learnable Knobs">
              <SubHeading id="knobs-four">The Four Knobs</SubHeading>
              <DTable
                head={["Knob", "Meaning", "Default"]}
                rows={[
                  [
                    <span className="font-mono text-cyan-300">merge_threshold</span>,
                    "Cosine similarity at which atoms are merged",
                    "0.95",
                  ],
                  [
                    <span className="font-mono text-cyan-300">prune_similarity_threshold</span>,
                    "Similarity above which pruning treats atoms as redundant",
                    "0.98",
                  ],
                  [
                    <span className="font-mono text-cyan-300">prune_min_age_days</span>,
                    "Minimum age before a node is eligible for pruning",
                    "7 days",
                  ],
                  [
                    <span className="font-mono text-cyan-300">lambda_threshold</span>,
                    "Invention pressure threshold (overridden by calibration)",
                    "0.30",
                  ],
                ]}
              />
              <SubHeading id="knobs-grids">Action Grids</SubHeading>
              <p>
                Each knob is a discrete action set. The bandit never proposes a
                value outside its grid — learned values are always safe.
              </p>
              <DTable
                head={["Knob", "Allowed values", "Actions"]}
                rows={GRID_DATA.map((g) => [
                  <span key={g.name} className="font-mono">{g.name}</span>,
                  <span key={g.values} className="font-mono text-slate-400">{g.values}</span>,
                  <span key={g.values + "n"} className="text-slate-400">{g.values.split("·").length}</span>,
                ])}
              />
              <ChartFrame caption="Fig 4.1 — Action count per knob (discrete grid size)">
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={GRID_SPREAD} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                      <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="name" tick={AXIS_TICK} />
                      <YAxis tick={AXIS_TICK} allowDecimals={false} />
                      <Tooltip contentStyle={{ background: "#0b1120", border: "1px solid #1e293b", fontSize: 12 }} />
                      <Bar dataKey="spread" radius={[6, 6, 0, 0]}>
                        {GRID_SPREAD.map((d) => (
                          <Cell key={d.name} fill={d.name === "merge" ? "#38bdf8" : d.name === "lambda" ? "#fbbf24" : "#c084fc"} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </ChartFrame>
              <SubHeading id="knobs-defaults">Defaults vs Learned</SubHeading>
              <p>
                Fresh graphs run the defaults exactly (untried arms are ignored,
                so pre-learning behavior is preserved bit-for-bit). An arm is
                trusted only after 5 visits; until then the default stands. The
                chart below shows an illustrative learning trajectory — the
                policy migrating from conservative defaults to context-appropriate
                values as cycles accrue.
              </p>
              <ChartFrame caption="Fig 4.2 — Knob evolution across policy versions (illustrative)">
                <div className="h-[220px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={LEARNED_TRACK} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                      <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="cycle" tick={AXIS_TICK} />
                      <YAxis tick={AXIS_TICK} domain={[0, 1]} />
                      <Tooltip contentStyle={{ background: "#0b1120", border: "1px solid #1e293b", fontSize: 12 }} />
                      <Line type="monotone" dataKey="merge" stroke="#38bdf8" strokeWidth={2} dot={{ r: 3 }} name="merge_threshold" />
                      <Line type="monotone" dataKey="prune" stroke="#c084fc" strokeWidth={2} dot={{ r: 3 }} name="prune_similarity_threshold" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </ChartFrame>
            </SectionHeading>

            {/* ============ 5. SEMANTIC WINNER SELECTION ============ */}
            <SectionHeading id="winner" kicker="Chapter 06" title="Semantic Winner Selection">
              <SubHeading id="winner-problem">Why Hash Order Failed</SubHeading>
              <p>
                Legacy behavior picked the merge winner by which vector_hash
                string sorts first. Deterministic — but semantically blind: it
                destroyed the better node roughly half the time. When two atoms
                merge, the loser is deleted, so an arbitrary rule could delete
                the node with more evidence, more usage, or fresher exposure.
              </p>
              <SubHeading id="winner-score">The 5-Term Score</SubHeading>
              <p>
                Each candidate is scored in [0,1] as a weighted sum of five
                information-value signals:
              </p>
              <DTable
                head={["Term", "Weight", "Signal", "Saturation"]}
                rows={[
                  [
                    <span className="text-sky-300">Evidence</span>, "25%",
                    "Member count (opp_signature) or evidence list length",
                    "10 members",
                  ],
                  [
                    <span className="text-purple-300">Usage</span>, "20%",
                    "touch_count — how often the node was retrieved",
                    "50 touches",
                  ],
                  [
                    <span className="text-pink-300">Recency</span>, "15%",
                    "Exponential decay of last_access, half-life 14 days",
                    "unknown = neutral 0.5",
                  ],
                  [
                    <span className="text-emerald-300">Source</span>, "20%",
                    "Macro kind +0.6 · long_term +0.2 · provenance +0.15 · anchor +0.1 · level",
                    "level/8",
                  ],
                  [
                    <span className="text-amber-300">Residual</span>, "20%",
                    "Novel information content (auto-detects int×1e9 storage)",
                    "1.0",
                  ],
                ]}
              />
              <ChartFrame caption="Fig 5.1 — Semantic score weight composition (sum = 100%)">
                <div className="h-[220px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={SCORE_WEIGHTS} dataKey="weight" nameKey="name" cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={3}>
                        {SCORE_WEIGHTS.map((s) => (
                          <Cell key={s.name} fill={s.fill} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ background: "#0b1120", border: "1px solid #1e293b", fontSize: 12 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex flex-wrap gap-x-4 gap-y-1 px-2 pb-2">
                  {SCORE_WEIGHTS.map((s) => (
                    <span key={s.name} className="flex items-center gap-1.5 font-mono text-[10px] text-slate-400">
                      <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: s.fill }} />
                      {s.name} {s.weight}%
                    </span>
                  ))}
                </div>
              </ChartFrame>
              <SubHeading id="winner-flow">Decision Flow</SubHeading>
              <WinnerFlowDiagram />
              <Callout tone="info" title="Determinism preserved">
                Exact ties fall back to the legacy lexicographic hash rule, and
                any error in the selector falls back to legacy behavior — the
                merge pipeline never breaks.
              </Callout>
            </SectionHeading>

            {/* ============ 6. LINUCB ============ */}
            <SectionHeading id="bandit" kicker="Chapter 07" title="LinUCB Contextual Bandit">
              <SubHeading id="bandit-how">How It Works</SubHeading>
              <p>
                Each knob is a <em>contextual bandit</em> with one ridge
                regression per grid value. On every cycle the policy looks at
                the graph's context vector and scores each candidate value as
                <span className="font-mono text-cyan-300"> μ(x) + α·σ(x)</span> —
                the learned expected reward plus an uncertainty bonus. Higher
                bonus for poorly-explored values = natural exploration; higher
                mean for well-explored values = exploitation. The best score
                wins, with an additional 10% ε-greedy random pick.
              </p>
              <SubHeading id="bandit-math">The Math</SubHeading>
              <DTable
                head={["Step", "Formula", "Meaning"]}
                rows={[
                  [
                    "Features", <span className="font-mono">x = [1, R, N, D, H, count/1000]</span>,
                    "Context fingerprint of the graph pre-cycle",
                  ],
                  [
                    "Online update", <span className="font-mono">A += xxᵀ, b += r·x</span>,
                    "A is a 6×6 design matrix with ridge prior λ=1; b accumulates rewards",
                  ],
                  [
                    "Mean estimate", <span className="font-mono">θ = A⁻¹b, μ = θ·x</span>,
                    "Ridge regression via Gauss–Jordan inversion (singular → prior inverse)",
                  ],
                  [
                    "Uncertainty", <span className="font-mono">σ² = xᵀA⁻¹x</span>,
                    "Confidence shrinks as the arm accumulates visits",
                  ],
                  [
                    "Selection", <span className="font-mono">argmax (μ + α√σ²)</span>,
                    "α = 0.6 default (policy-level, per-arm); untried values = +∞",
                  ],
                ]}
              />
              <SubHeading id="bandit-explore">Exploration vs Exploitation</SubHeading>
              <p>
                The chart shows how the uncertainty bonus decays as an arm is
                visited — the bandit starts exploratory and becomes greedy as
                confidence grows.
              </p>
              <ChartFrame caption="Fig 6.1 — Uncertainty bonus vs visits (α = 0.6)">
                <div className="h-[220px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={EXPLORE_CURVE} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                      <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="n" tick={AXIS_TICK} label={{ value: "visits", position: "insideBottom", offset: -2, fill: "#64748b", fontSize: 10 }} />
                      <YAxis tick={AXIS_TICK} />
                      <Tooltip contentStyle={{ background: "#0b1120", border: "1px solid #1e293b", fontSize: 12 }} />
                      <Line type="monotone" dataKey="bonus" stroke="#f472b6" strokeWidth={2.5} dot={{ r: 3 }} name="α·√σ²" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </ChartFrame>
              <Callout tone="success" title="Contextual, not global">
                The same knob value is judged differently in a high-redundancy
                graph than in a high-novelty one — the policy learns
                <em> per graph, per context</em>.
              </Callout>
            </SectionHeading>

            {/* ============ 7. REWARD & CALIBRATION ============ */}
            <SectionHeading id="reward" kicker="Chapter 08" title="Reward & Lambda Calibration">
              <SubHeading id="reward-formula">Reward Formula</SubHeading>
              <p>
                The reward in [−1, 1] blends three invariants, then optionally
                folds in the retrieval probe:
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                <ChartFrame caption="Fig 7.1 — Metric blend (no probe)">
                  <div className="h-[180px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={REWARD_BLEND} dataKey="pct" nameKey="name" cx="50%" cy="50%" innerRadius={38} outerRadius={62} paddingAngle={3}>
                          {REWARD_BLEND.map((s) => (
                            <Cell key={s.name} fill={s.fill} />
                          ))}
                        </Pie>
                        <Tooltip contentStyle={{ background: "#0b1120", border: "1px solid #1e293b", fontSize: 12 }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </ChartFrame>
                <ChartFrame caption="Fig 7.2 — Final blend with retrieval probe">
                  <div className="h-[180px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={RETRIEVAL_BLEND} dataKey="pct" nameKey="name" cx="50%" cy="50%" innerRadius={38} outerRadius={62} paddingAngle={3}>
                          {RETRIEVAL_BLEND.map((s) => (
                            <Cell key={s.name} fill={s.fill} />
                          ))}
                        </Pie>
                        <Tooltip contentStyle={{ background: "#0b1120", border: "1px solid #1e293b", fontSize: 12 }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </ChartFrame>
              </div>
              <DTable
                head={["Component", "Formula", "Clamp"]}
                rows={[
                  [
                    "Redundancy reduction",
                    <span className="font-mono">(R_before − R_after) / R_before</span>,
                    "[0,1]",
                  ],
                  [
                    "Boundedness gain",
                    <span className="font-mono">(E_before − E_after) / E_before</span>,
                    "[0,1]",
                  ],
                  [
                    "Novelty retention",
                    <span className="font-mono">(N_after − N_before)/2 + 0.5</span>,
                    "[0,1]",
                  ],
                  [
                    "Retrieval component",
                    <span className="font-mono">(probe_after − probe_before)/probe_before</span>,
                    "[−1,1] → [0,1]",
                  ],
                  [
                    "No-improvement penalty",
                    <span className="font-mono">−0.05 if acted but R didn't fall</span>,
                    "—",
                  ],
                ]}
              />
              <SubHeading id="reward-lambda">Lambda Calibration (Welford)</SubHeading>
              <p>
                λ is the graph's own "pressure" invariant. Instead of a fixed
                0.30 threshold, the system tracks a rolling mean and variance
                (Welford's online algorithm — one pass, constant memory). After
                at least 10 samples the threshold becomes{" "}
                <span className="font-mono text-cyan-300">mean + 0.5·std</span>, so
                "high pressure" is relative to this graph's baseline, and the
                result is clamped to the lambda grid bounds.
              </p>
              <DTable
                head={["State", "Field", "Meaning"]}
                rows={[
                  ["n", <span className="font-mono">lambda_calibration.n</span>, "Sample count"],
                  ["mean", <span className="font-mono">lambda_calibration.mean</span>, "Rolling mean of λ"],
                  ["m2", <span className="font-mono">lambda_calibration.m2</span>, "Sum of squared deviations (std = √(m2/(n−1)))"],
                ]}
              />
            </SectionHeading>

            {/* ============ 8. META-METRICS ============ */}
            <SectionHeading id="meta" kicker="Chapter 09" title="Meta-Metrics & Maturity">
              <SubHeading id="meta-five">The Five Metrics</SubHeading>
              <p>
                Meta-metrics prove that evolution is actually improving the
                graph — they are the "meta loop" on top of the outcome rows.
              </p>
              <DTable
                head={["Metric", "Definition", "Healthy sign"]}
                rows={[
                  [
                    <span className="font-mono text-emerald-300">merge_usefulness</span>,
                    "Fraction of redundancy actually removed by merges (0.5 when no merges)",
                    "→ 1.0",
                  ],
                  [
                    <span className="font-mono text-emerald-300">invention_utilization</span>,
                    "Fraction of macros with touch_count > 0 — do invented abstractions get used?",
                    "→ 1.0",
                  ],
                  [
                    <span className="font-mono text-emerald-300">prune_regret</span>,
                    "Pruning that failed to relieve redundancy (wasted work)",
                    "→ 0.0",
                  ],
                  [
                    <span className="font-mono text-emerald-300">d_drift</span>,
                    "|D_after − D_before| — structural stability",
                    "small",
                  ],
                  [
                    <span className="font-mono text-emerald-300">h_drift</span>,
                    "|H_after − H_before| — entropy stability",
                    "small",
                  ],
                ]}
              />
              <ChartFrame caption="Fig 8.1 — Illustrative maturity trajectory across cycles">
                <div className="h-[220px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={META_TREND} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                      <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="cycle" tick={AXIS_TICK} />
                      <YAxis tick={AXIS_TICK} domain={[0, 1]} />
                      <Tooltip contentStyle={{ background: "#0b1120", border: "1px solid #1e293b", fontSize: 12 }} />
                      <Line type="monotone" dataKey="usefulness" stroke="#34d399" strokeWidth={2.5} dot={{ r: 3 }} name="merge_usefulness" />
                      <Line type="monotone" dataKey="utilization" stroke="#38bdf8" strokeWidth={2.5} dot={{ r: 3 }} name="invention_utilization" />
                      <Line type="monotone" dataKey="regret" stroke="#fb7185" strokeWidth={2.5} dot={{ r: 3 }} name="prune_regret" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </ChartFrame>
              <SubHeading id="meta-alerts">Alert Conditions</SubHeading>
              <DTable
                head={["Alert", "Trigger", "Meaning"]}
                rows={[
                  [
                    <span className="font-mono text-amber-300">over_merge_risk</span>,
                    "merges > 0 and R_after > R_before + 0.01",
                    "Merging made redundancy worse",
                  ],
                  [
                    <span className="font-mono text-amber-300">d_collapse</span>,
                    "D_after < D_before − 0.05",
                    "Dimension collapse = over-merging",
                  ],
                  [
                    <span className="font-mono text-amber-300">prune_regret_high</span>,
                    "prunes > 0 and prune_regret > 0.5",
                    "Pruning wasted effort",
                  ],
                ]}
              />
            </SectionHeading>

            {/* ============ 9. STORAGE ============ */}
            <SectionHeading id="storage" kicker="Chapter 10" title="Storage & Persistence">
              <SubHeading id="storage-tables">Database Tables</SubHeading>
              <p>
                Migration <span className="font-mono">0032_evolution_learning.sql</span>{" "}
                adds three tables (auto-applied by the glob-based migration
                runner):
              </p>
              <DTable
                head={["Table", "Purpose", "Key columns"]}
                rows={[
                  [
                    <span className="font-mono text-cyan-300">evolution_outcomes</span>,
                    "One row per cycle: before/after diagnostics + reward",
                    <span className="font-mono">graph_version · r/n/d/h/e before+after · retrieval_delta · reward · policy_snapshot</span>,
                  ],
                  [
                    <span className="font-mono text-cyan-300">evolution_policy_state</span>,
                    "One row per (tenant, graph): the learned policy",
                    <span className="font-mono">policy_version · arms (JSONB) · lambda_calibration (JSONB) · meta</span>,
                  ],
                  [
                    <span className="font-mono text-cyan-300">evolution_meta_metrics</span>,
                    "Rolling maturity metrics",
                    <span className="font-mono">merge_usefulness · invention_utilization · prune_regret · d_drift · h_drift · alerts</span>,
                  ],
                ]}
              />
              <DTable
                head={["Guarantee", "Behavior"]}
                rows={[
                  [
                    "Reads fail-closed",
                    "Missing/corrupt rows resolve to safe defaults — the pipeline never depends on learning state",
                  ],
                  [
                    "Writes fail-open",
                    "record/save never raise; failures return zero sentinels (best effort)",
                  ],
                  [
                    "Tenant isolation",
                    "Every row is scoped by tenant_id; indexes keyed on (tenant_id, graph_id)",
                  ],
                ]}
              />
              <SubHeading id="storage-schema">Schema v2 & Migration</SubHeading>
              <p>
                Policy state carries a <span className="font-mono">schema</span>{" "}
                tag. v2 adds the LinUCB feature matrices (A, b) per grid value
                and per-arm α. v1 states (UCB1-style, no context) are detected
                and migrated safely: the lambda calibration is preserved, but
                arms are reset because v1 rewards carry no context and cannot
                seed ridge regressions. Corrupt or unknown schemas produce a
                fresh policy with defaults.
              </p>
              <DTable
                head={["Schema", "Arms", "Lambda calibration", "Version"]}
                rows={[
                  [
                    <span className="font-mono">v1</span>, "Reset on load", <span className="text-emerald-300">Preserved</span>, "Reset to 0",
                  ],
                  [
                    <span className="font-mono">v2</span>, <span className="text-emerald-300">Fully restored (A, b, visits, rewards)</span>, <span className="text-emerald-300">Preserved</span>, <span className="text-emerald-300">Restored</span>,
                  ],
                  [
                    <span className="font-mono">unknown</span>, "Fresh defaults", "Fresh defaults", "0",
                  ],
                ]}
              />
            </SectionHeading>

            {/* ============ 10. API ============ */}
            <SectionHeading id="api" kicker="Chapter 11" title="API Reference">
              <SubHeading id="api-endpoints">Endpoints</SubHeading>
              <DTable
                head={["Method · Path", "Purpose", "Auth"]}
                rows={[
                  [
                    <span className="font-mono text-cyan-300">POST /api/v1/evolve</span>,
                    "Run one evolution cycle (merge/prune/invent/theorize)",
                    "JWT + tenant key",
                  ],
                  [
                    <span className="font-mono text-cyan-300">GET /api/v1/evolve/status</span>,
                    "Scheduler, control, guardrails, due-state",
                    "JWT + tenant key",
                  ],
                  [
                    <span className="font-mono text-cyan-300">PATCH /api/v1/evolve/control</span>,
                    "Toggle self-evolve / self-invent autonomy",
                    "JWT + tenant key",
                  ],
                  [
                    <span className="font-mono text-cyan-300">GET /api/v1/evolve/invention/flow</span>,
                    "2.5D invention-flow topology (atoms → macros → merges)",
                    "JWT + tenant key",
                  ],
                  [
                    <span className="font-mono text-cyan-300">GET /api/v1/evolve/learning/state</span>,
                    "Learned policy: knobs, source, schema, version, λ calibration, per-arm samples, defaults",
                    "JWT + tenant key",
                  ],
                  [
                    <span className="font-mono text-cyan-300">GET /api/v1/evolve/learning/outcomes</span>,
                    "Recent outcome rows (newest first, limit 1–200)",
                    "JWT + tenant key",
                  ],
                  [
                    <span className="font-mono text-cyan-300">GET /api/v1/evolve/learning/meta</span>,
                    "Recent meta-metric rows",
                    "JWT + tenant key",
                  ],
                ]}
              />
              <Callout tone="info" title="Read-only guarantee">
                All learning endpoints are strictly read-only — repeated GETs
                never mutate state (verified by acceptance tests).
              </Callout>
              <SubHeading id="api-samples">Response Shapes</SubHeading>
              <div className="space-y-2">
                <p className="font-mono text-[10px] uppercase tracking-widest text-slate-500">
                  GET /evolve/learning/state — excerpt
                </p>
                <pre className="overflow-x-auto rounded-[14px] border border-white/8 bg-black/50 p-4 text-[11px] leading-relaxed text-slate-300">
{`{
  "graph_id": "my_graph",
  "enabled": true,
  "schema_tag": "v2",
  "policy_version": 27,
  "source": "bandit",
  "learned": true,
  "knobs": { "merge_threshold": 0.92, "lambda_threshold": 0.33, ... },
  "calibration": { "n": 27, "mean": 0.312, "m2": 0.004 },
  "samples": { "merge_threshold": {
      "visits": { "0.95": 14, "0.92": 6 },
      "mean_reward": { "0.95": 0.61, "0.92": 0.74 } } },
  "defaults": { "merge_threshold": 0.95, ... }
}`}
                </pre>
                <p className="font-mono text-[10px] uppercase tracking-widest text-slate-500 pt-2">
                  GET /evolve/learning/outcomes — one row
                </p>
                <pre className="overflow-x-auto rounded-[14px] border border-white/8 bg-black/50 p-4 text-[11px] leading-relaxed text-slate-300">
{`{
  "graph_version": 8,
  "cycle_ts": "2026-08-09T12:00:00+00:00",
  "merges": 3, "prunes": 1, "inventions": 1,
  "r_before": 0.5,  "r_after": 0.12,
  "retrieval_delta": 0.14,
  "reward": 0.82,
  "policy_snapshot": { "merge_threshold": 0.92 }
}`}
                </pre>
              </div>
            </SectionHeading>

            {/* ============ 11. FRONTEND ============ */}
            <SectionHeading id="frontend" kicker="Chapter 12" title="Frontend Guide">
              <SubHeading id="frontend-panes">Dashboard Panes</SubHeading>
              <p>
                The Evolution Control Plane organizes everything into three
                panes (navigation bar at the top of the page):
              </p>
              <DTable
                head={["Pane", "Contains", "Icon"]}
                rows={[
                  [
                    <span className="text-sky-300">Overview & Controls</span>,
                    "Graph context, profile/persist modes, autonomy toggles, run-cycle button, scorecard, scheduler state, metric details, storage, learning panel",
                    <span className="inline-flex items-center gap-1"><Dna size={12} /> Dna</span>,
                  ],
                  [
                    <span className="text-purple-300">Physics & Topology</span>,
                    "2.5D invention flow canvas, physics invariants stream",
                    <span className="inline-flex items-center gap-1"><Activity size={12} /> Activity</span>,
                  ],
                  [
                    <span className="text-emerald-300">Timeline & Logs</span>,
                    "Evolution event stream with evolution-only filter and auto-refresh",
                    <span className="inline-flex items-center gap-1"><Zap size={12} /> Clock3</span>,
                  ],
                ]}
              />
              <SubHeading id="frontend-visuals">Visual Sub-Tabs</SubHeading>
              <DTable
                head={["Sub-tab", "Description"]}
                rows={[
                  [
                    <span className="font-mono">2.5D Invention Flow</span>,
                    "Left-to-right pipeline: atoms → macros → merges, with merge losers highlighted",
                  ],
                  [
                    <span className="font-mono">Physics Stream</span>,
                    "Entropy / redundancy / novelty / pressure / energy over the last cycles",
                  ],
                ]}
              />
              <SubHeading id="frontend-learning">Learning & Self-Optimization Panel</SubHeading>
              <p>
                A dedicated card on the Overview pane renders the three learning
                endpoints live:
              </p>
              <DTable
                head={["Widget", "Shows"]}
                rows={[
                  [
                    "Status badges",
                    "Learning on/off, schema tag, policy version, knob source (defaults / bandit)",
                  ],
                  [
                    "Learned knobs",
                    "Current value per knob vs. default — learned values highlighted",
                  ],
                  [
                    "Lambda calibration",
                    "Sample count and rolling mean λ",
                  ],
                  [
                    "Bandit visits",
                    "Per-value visit chips, e.g. 0.95×12",
                  ],
                  [
                    "Recent outcomes",
                    "+merges −prunes +inventions, reward, retrieval δ",
                  ],
                  [
                    "Maturity metrics",
                    "merge_usefulness · invention_utilization · prune_regret · d-drift per cycle",
                  ],
                  [
                    "Refresh",
                    "Re-fetches all three endpoints on demand",
                  ],
                ]}
              />
              <Callout tone="success" title="Non-fatal by design">
                If learning is disabled or the endpoints are unreachable, the
                panel shows a graceful state and the rest of the dashboard keeps
                working.
              </Callout>
            </SectionHeading>

            {/* ============ 12. CONFIGURATION ============ */}
            <SectionHeading id="config" kicker="Chapter 13" title="Configuration">
              <SubHeading id="config-flags">Feature Flags & Env Vars</SubHeading>
              <DTable
                head={["Variable", "Default", "Effect"]}
                rows={[
                  [
                    <span className="font-mono text-cyan-300">FAIM_EVOLUTION_LEARNING_ENABLED</span>,
                    "false",
                    "Master switch: semantic winners, learned knobs, probes, outcomes, meta-metrics",
                  ],
                  [
                    <span className="font-mono">FAIM_SELF_EVOLVE_ENABLED</span>,
                    "false",
                    "Scheduler autonomy (manual / post_upload / periodic / hybrid)",
                  ],
                  [
                    <span className="font-mono">FAIM_SELF_EVOLVE_TRIGGER_MODE</span>,
                    "manual",
                    "How often autonomous cycles may run",
                  ],
                  [
                    <span className="font-mono">FAIM_SELF_EVOLVE_MAX_ACTIONS</span>,
                    "25",
                    "Per-cycle action budget (core enforcement)",
                  ],
                  [
                    <span className="font-mono">FAIM_SELF_EVOLVE_MIN_INTERVAL_SECONDS</span>,
                    "300",
                    "Minimum seconds between autonomous cycles",
                  ],
                  [
                    <span className="font-mono">FAIM_SELF_EVOLVE_MIN_VERSION_DELTA</span>,
                    "1",
                    "Minimum graph versions between cycles",
                  ],
                ]}
              />
              <Callout tone="warn" title="Production guardrail">
                Enabling learning in production emits a validation warning
                (never an error): "learned knobs override fixed evolution
                constants (hard bounds always enforced)."
              </Callout>
              <p>
                Bandit internals are configurable in code:{" "}
                <span className="font-mono">EXPLORATION_RATE 0.10</span>,{" "}
                <span className="font-mono">LINUCB_ALPHA 0.6</span>,{" "}
                <span className="font-mono">RIDGE_LAMBDA 1.0</span>,{" "}
                <span className="font-mono">MIN_VISITS_BEFORE_LEARNED 5</span>,{" "}
                <span className="font-mono">MIN_LAMBDA_SAMPLES 10</span>.
              </p>
            </SectionHeading>

            {/* ============ PART II DIVIDER ============ */}
            <div className="flex items-center gap-3 pt-2">
              <span className="h-px flex-1 bg-gradient-to-r from-transparent via-fuchsia-400/40 to-transparent" />
              <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.3em] text-fuchsia-300/80">
                Part II — Deep Reference
              </span>
              <span className="h-px flex-1 bg-gradient-to-r from-transparent via-fuchsia-400/40 to-transparent" />
            </div>

            {/* ============ 13. INVENTION ENGINE ============ */}
            <SectionHeading id="invention" kicker="Chapter 14" title="The Invention Engine">
              <p>
                Invention is what separates FAIM from a mere deduplicator: the
                engine distills recurring evidence into{" "}
                <span className="font-mono text-cyan-300">macros</span> —
                higher-order abstractions that summarize many atoms. When
                learning is enabled, the policy's λ threshold directly
                regulates how much invention happens each cycle.
              </p>
              <SubHeading id="invention-modes">Self-Invent Modes</SubHeading>
              <DTable
                head={["Mode", "Behavior"]}
                rows={[
                  [
                    <span className="font-mono">Off</span>,
                    "No invention. Merges and prunes still run.",
                  ],
                  [
                    <span className="font-mono">On evolve</span>,
                    "Invent macros as part of every evolution cycle.",
                  ],
                  [
                    <span className="font-mono">After upload</span>,
                    "Invent following a document upload / graph ingestion.",
                  ],
                  [
                    <span className="font-mono">Both</span>,
                    "On evolve and after upload.",
                  ],
                ]}
              />
              <SubHeading id="invention-overrides">Invention Overrides</SubHeading>
              <p>
                Each cycle resolves invention parameters; with learning active,
                the bandit's{" "}
                <span className="font-mono text-cyan-300">lambda_threshold</span>{" "}
                replaces the runtime default so invention pressure follows the
                graph's own history:
              </p>
              <DTable
                head={["Parameter", "Base", "Conservative", "Aggressive", "Meaning"]}
                rows={[
                  [
                    <span className="font-mono">lambda_threshold</span>,
                    "0.30",
                    <span className="text-slate-400">+0.10 (harder to invent)</span>,
                    <span className="text-slate-400">−0.05 (easier to invent)</span>,
                    "Pressure needed to form a macro",
                  ],
                  [
                    <span className="font-mono">max_macros_per_cycle</span>,
                    "3",
                    "3",
                    "3",
                    "Capped by evolve_invention_max_macros_cap",
                  ],
                  [
                    <span className="font-mono">min_redundancy_reduction</span>,
                    "0.01",
                    <span className="text-slate-400">+0.02</span>,
                    <span className="text-slate-400">−0.005</span>,
                    "Evidence the macro must reduce redundancy",
                  ],
                ]}
              />
              <SubHeading id="invention-types">Cognitive Types</SubHeading>
              <p>
                Invented and existing nodes carry a cognitive type that shapes
                the invention-flow visualization:
              </p>
              <DTable
                head={["Type", "Meaning"]}
                rows={[
                  [<span className="font-mono">fact</span>, "Asserted factual statement"],
                  [<span className="font-mono">procedure</span>, "How-to / process knowledge"],
                  [<span className="font-mono">event</span>, "Occurrence anchored in time"],
                  [<span className="font-mono">contradiction</span>, "Conflicting evidence pair"],
                  [<span className="font-mono">work</span>, "Artifact or deliverable"],
                ]}
              />
              <Callout tone="success" title="Measured, not assumed">
                Every invented macro counts toward{" "}
                <span className="font-mono">invention_utilization</span> — the
                system tracks whether abstractions are actually retrieved
                (touch_count &gt; 0), so invention is held accountable.
              </Callout>
            </SectionHeading>

            {/* ============ 14. PRUNE POLICY ============ */}
            <SectionHeading id="prune" kicker="Chapter 15" title="Prune Policy & Protection">
              <SubHeading id="prune-rules">Prune Rules</SubHeading>
              <p>
                The prune pass removes stale or redundant structure using a
                policy of three criteria:
              </p>
              <DTable
                head={["Criterion", "Source", "Learned?"]}
                rows={[
                  [
                    <span className="font-mono">min_age_days</span>,
                    "Nodes younger than this are never pruned",
                    <span className="text-emerald-300">Yes — bandit arm (3–21 days)</span>,
                  ],
                  [
                    <span className="font-mono">max_touch_count</span>,
                    "Frequently-used nodes are preserved (usage signal)",
                    "Runtime policy",
                  ],
                  [
                    <span className="font-mono">min_similarity_for_redundancy</span>,
                    "Similarity above which another node counts as redundant",
                    <span className="text-emerald-300">Yes — bandit arm (0.93–0.99)</span>,
                  ],
                ]}
              />
              <SubHeading id="prune-protection">Macro Protection</SubHeading>
              <Callout tone="warn" title="protect_macros = true">
                Invented macros are <em>never</em> pruned. Higher-order
                abstractions are structural investments — the system may merge
                their redundant children but will not delete the macro itself.
              </Callout>
              <p>
                The prune pass is also audited: if pruning runs but redundancy
                does not fall, the cycle records{" "}
                <span className="font-mono text-amber-300">prune_regret</span>{" "}
                (see Chapter 9) — wasted work is surfaced, not hidden.
              </p>
            </SectionHeading>

            {/* ============ 15. INVARIANTS ============ */}
            <SectionHeading id="invariants" kicker="Chapter 16" title="Invariants & Diagnostics">
              <SubHeading id="invariants-seven">The Seven Metrics</SubHeading>
              <p>
                Every cycle snapshots the graph into a stable, ordered set of
                invariants. These are the language the whole system speaks —
                scorecards, bandit features, rewards, and the physics stream:
              </p>
              <DTable
                head={["Key", "Invariant", "Meaning"]}
                rows={[
                  [<span className="font-mono">CR</span>, "Compression ratio", "How compactly the graph encodes its content"],
                  [<span className="font-mono">R</span>, "Redundancy", "Fraction of duplicated information (target: ↓)"],
                  [<span className="font-mono">D_hat</span>, "Fractal dimension", "Structural depth / self-similarity estimate"],
                  [<span className="font-mono">H_hat</span>, "Entropy", "Disorder / information spread (target: ↓)"],
                  [<span className="font-mono">lambda_hat</span>, "Pressure", "Readiness to evolve / invent"],
                  [<span className="font-mono">novelty</span>, "Novelty", "Amount of new information (target: hold or ↑)"],
                  [<span className="font-mono">energy</span>, "Energy / boundedness", "Structural boundedness (target: ↓)"],
                ]}
              />
              <SubHeading id="invariants-context">How Context Uses Them</SubHeading>
              <DTable
                head={["Consumer", "Uses"]}
                rows={[
                  [
                    <span className="text-sky-300">LinUCB features</span>,
                    <span className="font-mono">[1, R, N, D, H, node_count/1000]</span>,
                  ],
                  [
                    <span className="text-emerald-300">Reward</span>,
                    "R reduction (50%), energy boundedness (30%), novelty retention (20%)",
                  ],
                  [
                    <span className="text-fuchsia-300">Meta-metrics</span>,
                    "d_drift and h_drift from before/after deltas",
                  ],
                  [
                    <span className="text-amber-300">UI physics stream</span>,
                    "Entropy / redundancy / novelty / pressure / energy trend lines",
                  ],
                  [
                    <span className="text-purple-300">Alerts</span>,
                    "R rise after merges, D collapse, H instability",
                  ],
                ]}
              />
            </SectionHeading>

            {/* ============ 16. EVENTS ============ */}
            <SectionHeading id="events" kicker="Chapter 17" title="Events & Timeline">
              <p>
                Every evolution action emits an event into the graph's durable
                event stream — the same stream the Timeline pane renders. Event
                kinds are stable and filterable:
              </p>
              <SubHeading id="events-kinds">Event Kinds</SubHeading>
              <DTable
                head={["Event", "Meaning"]}
                rows={[
                  [<span className="font-mono text-sky-300">DIAGNOSTICS_SNAPSHOT</span>, "Pre/post-cycle invariants (D_hat, H_hat, lambda_hat, R, N, E)"],
                  [<span className="font-mono text-sky-300">EVOLUTION_START</span>, "Cycle begins"],
                  [<span className="font-mono text-sky-300">EVOLUTION_MERGE</span>, "One merge executed (winner kept, loser absorbed)"],
                  [<span className="font-mono text-sky-300">EVOLUTION_INVENTION_SUMMARY</span>, "Macros formed this cycle"],
                  [<span className="font-mono text-sky-300">EVOLUTION_INVENTION_ERROR</span>, "Invention step failed (non-fatal)"],
                  [<span className="font-mono text-sky-300">EVOLUTION_PERSISTENCE_APPLIED</span>, "State persisted to graph version"],
                  [<span className="font-mono text-sky-300">EVOLUTION_COMPLETE</span>, "Cycle finished with actions"],
                  [<span className="font-mono text-sky-300">EVOLUTION_SKIPPED</span>, "Cycle ran but nothing qualified"],
                  [<span className="font-mono text-sky-300">EVOLUTION_ERROR</span>, "Cycle failed (fatal for the run)"],
                ]}
              />
              <Callout tone="info" title="Timeline tips">
                The Timeline pane's "Evolution-only" filter shows exactly these
                kinds; the auto-refresh toggle polls the stream every few
                seconds.
              </Callout>
            </SectionHeading>

            {/* ============ 17. PROFILES & PERSIST ============ */}
            <SectionHeading id="modes" kicker="Chapter 18" title="Profiles & Persist Modes">
              <SubHeading id="modes-profile">Profiles</SubHeading>
              <p>
                The profile shapes how aggressively the cycle evolves. It is
                combined with a persist mode via the profile/persist policy
                helper:
              </p>
              <DTable
                head={["Profile", "Character"]}
                rows={[
                  [<span className="font-mono">Strict</span>, "Conservative, maximal evidence before structural change"],
                  [<span className="font-mono">Fast</span>, "Balanced — quick gains with moderate risk"],
                  [<span className="font-mono">Relaxed</span>, "Progressive — more aggressive merging and invention"],
                ]}
              />
              <SubHeading id="modes-persist">Persist Modes & Durability</SubHeading>
              <DTable
                head={["Persist mode", "Completion mode", "Durability path"]}
                rows={[
                  [
                    <span className="font-mono">Strict</span>,
                    <span className="font-mono">sync_strict</span>,
                    "State must persist or the run reports failure",
                  ],
                  [
                    <span className="font-mono">Relaxed</span>,
                    <span className="font-mono">core_sync_state_best_effort</span>,
                    "State update is best-effort; failures are non-fatal and reported via state_update_status / state_update_error",
                  ],
                ]}
              />
              <Callout tone="info" title="Requested vs effective">
                The response carries both requested and effective
                profile/persist pairs — the effective values are what the core
                actually honored.
              </Callout>
            </SectionHeading>

            {/* ============ 18. RESPONSE ============ */}
            <SectionHeading id="response" kicker="Chapter 19" title="Evolve Response Reference">
              <SubHeading id="response-fields">Response Fields</SubHeading>
              <p>
                POST /api/v1/evolve returns the full cycle report, including a
                nested learning summary when enabled:
              </p>
              <DTable
                head={["Field", "Meaning"]}
                rows={[
                  [<span className="font-mono">status</span>, "completed / error"],
                  [<span className="font-mono">graph_version</span>, "New graph version after the cycle"],
                  [<span className="font-mono">merges / prunes / inventions</span>, "Action counts"],
                  [<span className="font-mono">diagnostics</span>, "Post-cycle invariants snapshot"],
                  [<span className="font-mono">events_emitted</span>, "Event kinds emitted this run"],
                  [<span className="font-mono">latency_ms</span>, "Cycle wall time"],
                  [<span className="font-mono">effective_profile / effective_persist_mode</span>, "What was actually honored"],
                  [<span className="font-mono">completion_mode / durability_path</span>, "Persistence contract used"],
                  [<span className="font-mono">state_update_status / state_update_error</span>, "Relaxed-persistence outcome"],
                  [<span className="font-mono">learning</span>, "Reward, retrieval_delta, meta-metrics, policy_version, knobs used (only when learning enabled)"],
                ]}
              />
              <pre className="overflow-x-auto rounded-[14px] border border-white/8 bg-black/50 p-4 text-[11px] leading-relaxed text-slate-300">
{`{
  "status": "completed",
  "graph_version": 8,
  "merges": 3, "prunes": 1, "inventions": 1,
  "events_emitted": ["DIAGNOSTICS_SNAPSHOT", "EVOLUTION_MERGE", "EVOLUTION_COMPLETE"],
  "effective_profile": "strict",
  "effective_persist_mode": "relaxed",
  "state_update_status": "applied",
  "learning": {
    "reward": 0.82,
    "retrieval_delta": 0.14,
    "policy_version": 27,
    "knobs": { "merge_threshold": 0.92, "lambda_threshold": 0.33 },
    "meta_metrics": { "merge_usefulness": 0.9, "prune_regret": 0.05, "alerts": {} }
  }
}`}
              </pre>
            </SectionHeading>

            {/* ============ 19. FAQ ============ */}
            <SectionHeading id="faq" kicker="Chapter 20" title="Troubleshooting & FAQ">
              <DTable
                head={["Question", "Answer"]}
                rows={[
                  [
                    "Learning is on but knobs stay at defaults — why?",
                    "Fresh arms (0 visits) always resolve to defaults. Run several cycles; arms become trusted after 5 visits.",
                  ],
                  [
                    "Policy version stays 1 forever",
                    "The state must round-trip with schema tag v2. Older state tagged v1 resets arms by design (see Chapter 10).",
                  ],
                  [
                    "The learning panel is empty",
                    "Check the flag is true, migration 0032 applied, and at least one cycle has completed on this graph.",
                  ],
                  [
                    "Can learning damage my graph?",
                    "No. Values are clamped to hard-bound grids, writes are best-effort, and disabling the flag restores legacy behavior exactly.",
                  ],
                  [
                    "Where do the before/after numbers come from?",
                    "The same diagnostics snapshot the core already computes: R (redundancy), N (novelty), D (dimension), H (entropy), E (energy), λ (pressure).",
                  ],
                  [
                    "Is any ML library required?",
                    "No. LinUCB is implemented from scratch (Gauss–Jordan inverse, no numpy) — deterministic and auditable.",
                  ],
                ]}
              />
              <div className="flex items-center gap-2 pt-2 text-[11px] text-slate-500">
                <ShieldCheck size={13} className="text-emerald-400" />
                FAIM Evolution · Phase 0032 · deterministic · opt-in · auditable
              </div>
            </SectionHeading>
          </div>
        </main>
      </div>
    </div>,
    document.body,
  );
}
