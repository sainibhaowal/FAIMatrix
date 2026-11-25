"use client";

import { useMemo, useState } from "react";
import {
  BookOpen,
  Cpu,
  Database,
  GitBranch,
  Layers,
  Lock,
  Network,
  Shield,
  Sliders,
  Sparkles,
  Zap,
} from "lucide-react";
import {
  BENCHMARK_HIGHLIGHTS,
  HISTORICAL_PROGRESSION,
} from "@/lib/benchmarkResults";

// ---------------------------------------------------------------------------
// 1. Notebook / Book-Themed Masthead Banner
// ---------------------------------------------------------------------------
export function DocsBookBanner({
  chapterNumber,
  totalChapters,
  groupTitle,
  sectionTitle,
  version,
}: {
  chapterNumber: number;
  totalChapters: number;
  groupTitle: string;
  sectionTitle: string;
  version: string;
}) {
  const padded = String(chapterNumber).padStart(2, "0");
  const paddedTotal = String(totalChapters).padStart(2, "0");

  return (
    <div className="relative overflow-hidden rounded-2xl border border-slate-800/90 bg-gradient-to-br from-slate-900/90 via-slate-950/95 to-cyan-950/25 p-5 sm:p-6 mb-7 shadow-xl shadow-slate-950/50">
      {/* Subtle notebook grid lines */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.06]"
        style={{
          backgroundImage:
            "linear-gradient(to right, #94a3b8 1px, transparent 1px), linear-gradient(to bottom, #94a3b8 1px, transparent 1px)",
          backgroundSize: "28px 28px",
        }}
      />
      {/* Left book spine accent */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-cyan-400 via-purple-400 to-emerald-400"
      />

      <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/25 text-cyan-300">
              <BookOpen className="w-3 h-3" />
              CHAPTER {padded} / {paddedTotal}
            </span>
            <span className="text-slate-500 uppercase tracking-wider">
              {groupTitle}
            </span>
            <span className="text-slate-700">/</span>
            <span className="text-slate-300">{sectionTitle}</span>
          </div>
          <h1 className="text-lg sm:text-xl font-semibold text-white tracking-tight">
            FAIM Technical Reference &amp; Research Handbook
          </h1>
          <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
            Verified internals of the 256-dim native math engine, Granite 97M
            hybrid dense acceleration, typed knowledge graph reasoning, and
            provenance-bound retrieval.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2 shrink-0 text-right sm:text-left">
          <div className="rounded-xl border border-slate-800 bg-slate-950/75 px-3 py-2">
            <p className="text-[10px] font-mono text-slate-500 uppercase">
              Runtime
            </p>
            <p className="text-xs font-mono font-semibold text-cyan-300">
              {version} Hybrid
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/75 px-3 py-2">
            <p className="text-[10px] font-mono text-slate-500 uppercase">
              SciFact nDCG@10
            </p>
            <p className="text-xs font-mono font-semibold text-emerald-300">
              0.6900 / 0.6871
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 2. Interactive End-to-End Architecture Flow Diagram
// ---------------------------------------------------------------------------
const PIPELINE_STAGES = [
  {
    id: "ingest",
    short: "01. Ingest",
    title: "Layout & Block Extraction",
    color: "#22d3ee",
    summary:
      "Documents (PDF, DOCX, PPTX, XLSX, images, text) are segmented deterministically into EvidenceBlocks with page, section, column, and char-offset anchors.",
    spec: "PyMuPDF + 300 DPI Tesseract OCR + Double-Extraction Guard",
  },
  {
    id: "encode",
    short: "02. Encode",
    title: "Dual Native + Neural Vectors",
    color: "#a78bfa",
    summary:
      "Every block receives a canonical 256-dim pure-math v_native vector (240 n-gram buckets + 16 text stats) alongside an optional 384-dim Granite 97M Multilingual embedding.",
    spec: "v_native (256-dim) + Granite 97M R2 (384-dim, 32K ctx)",
  },
  {
    id: "sidecars",
    short: "03. Enrich",
    title: "Representation V2 & Registry",
    color: "#fbbf24",
    summary:
      "Additive sparse sidecars capture stemmed tokens, bigrams, skip-grams, aliases, transliterations, temporal markers, and ConceptNet + multilingual bridges.",
    spec: "2,172,991 ConceptNet + 146,598 Multilingual Terms = 2,319,589",
  },
  {
    id: "graph",
    short: "04. Graph",
    title: "Typed Graph & SHA-256 Lineage",
    color: "#34d399",
    summary:
      "Nodes are deduplicated by SHA-256 content+anchor fingerprints and linked via inheritance, antisymmetric opposition, causal, and PMI semantic edges.",
    spec: "Idempotent touch_count + Temporal Conflict Suppression",
  },
  {
    id: "rank",
    short: "05. Rank",
    title: "Hybrid Recall & Reranker V2",
    color: "#60a5fa",
    summary:
      "Fuses Block-Max WAND sparse lists, deterministic VP-tree / Qdrant shortlists, K-hop PageRank diffusion (1 to 24 hops), and 7-component Reranker V2.",
    spec: "compute_node_score + Pairwise Dominance + Pulse-v2 Ledger",
  },
  {
    id: "answer",
    short: "06. Ground",
    title: "Extractive Citation Synthesis",
    color: "#f472b6",
    summary:
      "Returns verifiable extractive spans with file, page, section, conflict flags, and bounded [0, 1] confidence without generative hallucination.",
    spec: "Confidence = 0.45*span + 0.30*breadth + 0.25*active - penalty",
  },
];

export function VisualArchitectureFlow() {
  const [selectedId, setSelectedId] = useState("encode");
  const current =
    PIPELINE_STAGES.find((s) => s.id === selectedId) ?? PIPELINE_STAGES[0];

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-mono uppercase tracking-wider text-cyan-300">
            Interactive Architecture Flow
          </p>
          <p className="text-xs text-slate-500">
            Click any stage to inspect its exact mathematical contract and
            runtime artifacts.
          </p>
        </div>
        <span className="text-[10px] font-mono text-slate-500 px-2 py-0.5 rounded bg-slate-950 border border-slate-800">
          6 Deterministic Stages
        </span>
      </div>

      {/* Stage selector strip with connecting connectors */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        {PIPELINE_STAGES.map((stage) => {
          const active = stage.id === selectedId;
          return (
            <button
              key={stage.id}
              type="button"
              onClick={() => setSelectedId(stage.id)}
              className={`rounded-xl px-3 py-2.5 text-left transition-all border ${
                active
                  ? "bg-slate-950 text-white shadow-lg"
                  : "bg-slate-950/40 text-slate-400 border-slate-800/80 hover:border-slate-700 hover:text-slate-200"
              }`}
              style={{
                borderColor: active ? stage.color : undefined,
                boxShadow: active ? `0 0 0 1px ${stage.color}40` : undefined,
              }}
            >
              <span
                className="block text-[10px] font-mono font-bold"
                style={{ color: stage.color }}
              >
                {stage.short}
              </span>
              <span className="block text-xs font-medium mt-0.5 truncate">
                {stage.title.split(" ")[0]}
              </span>
            </button>
          );
        })}
      </div>

      {/* Active detail callout */}
      <div
        className="rounded-xl border bg-slate-950/75 p-4 transition-all"
        style={{ borderColor: `${current.color}40` }}
      >
        <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
          <h4 className="text-sm font-semibold text-white">{current.title}</h4>
          <code
            className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800"
            style={{ color: current.color }}
          >
            {current.spec}
          </code>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">
          {current.summary}
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 3. Interactive Verified Benchmark Chart
// ---------------------------------------------------------------------------
type ChartMetricKey = "scifact-ndcg" | "scifact-r5" | "nfcorpus" | "history";

export function VisualBenchmarkChart() {
  const [tab, setTab] = useState<ChartMetricKey>("scifact-ndcg");

  const barSets: Record<
    Exclude<ChartMetricKey, "history">,
    {
      title: string;
      subtitle: string;
      unit: string;
      max: number;
      bars: { label: string; value: number; note: string; color: string }[];
    }
  > = {
    "scifact-ndcg": {
      title: "BeIR / SciFact Accuracy (nDCG@10)",
      subtitle: "Full 5,183-doc / 300-query split (Signed 2026-11-24)",
      unit: "nDCG@10",
      max: 0.85,
      bars: [
        {
          label: "FAIM + Granite 97M",
          value: 0.69,
          note: "140.17 ms P50",
          color: "#22d3ee",
        },
        {
          label: "FAIM-Pure Zero-ML CPU",
          value: 0.6871,
          note: "86.31 ms CPU CI",
          color: "#34d399",
        },
        {
          label: "Standalone Granite 97M",
          value: 0.6806,
          note: "GPU only baseline",
          color: "#a78bfa",
        },
        {
          label: "BM25 Lexical Baseline",
          value: 0.6644,
          note: "45.76 ms P50",
          color: "#64748b",
        },
      ],
    },
    "scifact-r5": {
      title: "BeIR / SciFact Top-5 Coverage (Recall@5)",
      subtitle: "Full 300-query split comparing deterministic + hybrid paths",
      unit: "Recall@5",
      max: 0.9,
      bars: [
        {
          label: "FAIM + Granite 97M",
          value: 0.7704,
          note: "+0.0511 over BM25",
          color: "#22d3ee",
        },
        {
          label: "FAIM-Pure Zero-ML CPU",
          value: 0.7554,
          note: "+0.0361 over BM25",
          color: "#34d399",
        },
        {
          label: "Standalone Granite 97M",
          value: 0.7522,
          note: "Neural dense only",
          color: "#a78bfa",
        },
        {
          label: "BM25 Lexical Baseline",
          value: 0.7193,
          note: "Standard sparse baseline",
          color: "#64748b",
        },
      ],
    },
    nfcorpus: {
      title: "BeIR / NFCorpus Medical Retrieval (nDCG@10)",
      subtitle: "323-query full split evaluation",
      unit: "nDCG@10",
      max: 0.42,
      bars: [
        {
          label: "FAIM + Granite 97M",
          value: 0.3314,
          note: "101.62 ms P50 (+6.6% vs BM25)",
          color: "#22d3ee",
        },
        {
          label: "FAIM-Pure Zero-ML CPU",
          value: 0.3267,
          note: "49.91 ms P50 (Zero GPU)",
          color: "#34d399",
        },
        {
          label: "BM25 Lexical Baseline",
          value: 0.311,
          note: "3.32 ms P50",
          color: "#64748b",
        },
      ],
    },
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-mono uppercase tracking-wider text-emerald-300">
            Verified Measurement Chart
          </p>
          <p className="text-xs text-slate-400">
            {tab === "history"
              ? "Engine evolution across 4 major releases on BeIR / SciFact"
              : barSets[tab].subtitle}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {(
            [
              ["scifact-ndcg", "SciFact nDCG@10"],
              ["scifact-r5", "SciFact Recall@5"],
              ["nfcorpus", "NFCorpus"],
              ["history", "v9 to v18 Speedup"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setTab(key)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-mono transition-colors border ${
                tab === key
                  ? "bg-cyan-500/15 border-cyan-500/40 text-cyan-200"
                  : "bg-slate-950/60 border-slate-800 text-slate-400 hover:text-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {tab === "history" ? (
        <div className="space-y-2.5">
          {HISTORICAL_PROGRESSION.map((row) => {
            const val = parseFloat(row.ndcgAt10);
            const widthPct = Math.min(100, Math.round((val / 0.8) * 100));
            return (
              <div
                key={row.generation}
                className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-3 space-y-1.5"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <span className="font-semibold text-white">
                    {row.generation}
                  </span>
                  <span className="font-mono text-cyan-300">
                    nDCG@10 {row.ndcgAt10} | P50 {row.p50Ms}
                  </span>
                </div>
                <div className="h-2.5 w-full rounded-full bg-slate-900 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-emerald-400 transition-all duration-500"
                    style={{ width: `${widthPct}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-400">{row.deltaSummary}</p>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {BENCHMARK_HIGHLIGHTS.map((item) => (
              <div
                key={item.label}
                className="rounded-xl border border-slate-800/80 bg-slate-950/60 px-3 py-2"
              >
                <p className="text-base font-mono font-bold text-white">
                  {item.value}
                </p>
                <p className="text-[10px] font-mono text-cyan-300 truncate">
                  {item.unit}
                </p>
              </div>
            ))}
          </div>
          <div className="space-y-2.5">
            {barSets[tab].bars.map((bar) => {
              const widthPct = Math.max(
                4,
                Math.round((bar.value / barSets[tab].max) * 100),
              );
              return (
                <div key={bar.label} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-slate-200">
                      {bar.label}
                    </span>
                    <span className="font-mono text-slate-300">
                      {bar.value.toFixed(4)}{" "}
                      <span className="text-slate-500">({bar.note})</span>
                    </span>
                  </div>
                  <div className="h-2.5 w-full rounded-full bg-slate-950 border border-slate-800/80 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${widthPct}%`,
                        backgroundColor: bar.color,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 4. Interactive Vector Anatomy + Hot/Warm/Cold Tier Classifier
// ---------------------------------------------------------------------------
export function VisualVectorTierExplorer() {
  const [daysAgo, setDaysAgo] = useState(5);
  const [touchCount, setTouchCount] = useState(2);
  const [longTerm, setLongTerm] = useState(false);

  const tier = useMemo(() => {
    if (longTerm) {
      return {
        label: "PROTECTED (LONG-TERM)",
        color: "#34d399",
        reason:
          "Excluded from cold pruning WHERE clause (long_term = true) regardless of age or access count.",
      };
    }
    if (daysAgo <= 7) {
      return {
        label: "HOT MEMORY",
        color: "#f97316",
        reason:
          "Accessed within the last 7 days. Assigned highest recency priority in retrieval.",
      };
    }
    if (daysAgo <= 30 || touchCount >= 5) {
      return {
        label: "WARM MEMORY",
        color: "#fbbf24",
        reason:
          "Accessed within 30 days or frequently retrieved (touch_count >= 5). Active working memory.",
      };
    }
    if (daysAgo > 90) {
      return {
        label: "COLD (PRUNE CANDIDATE)",
        color: "#94a3b8",
        reason:
          "Older than 90 days without protective flags. Eligible for dry-run and live cold pruning.",
      };
    }
    return {
      label: "COOLING STORAGE",
      color: "#64748b",
      reason:
        "Between 31 and 90 days inactive. Retained until prune threshold.",
    };
  }, [daysAgo, touchCount, longTerm]);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-5">
      <div>
        <p className="text-xs font-mono uppercase tracking-wider text-cyan-300 mb-1">
          256-Dimensional Native Vector Layout
        </p>
        <p className="text-xs text-slate-400 mb-3">
          Fixed proportion: 240 SHA-256 character n-gram buckets (93.75%) plus
          16 normalized structural statistics (6.25%), plus optional 384-dim
          Granite sidecar.
        </p>
        <div className="h-7 w-full rounded-xl overflow-hidden flex border border-slate-800 font-mono text-[10px]">
          <div
            className="bg-cyan-500/25 border-r border-cyan-500/40 flex items-center justify-center text-cyan-200 px-2"
            style={{ width: "60%" }}
          >
            dims 0..239: n-gram hashes (240 dims)
          </div>
          <div
            className="bg-purple-500/25 border-r border-purple-500/40 flex items-center justify-center text-purple-200 px-2"
            style={{ width: "16%" }}
          >
            16 stats
          </div>
          <div
            className="bg-emerald-500/20 flex items-center justify-center text-emerald-200 px-2"
            style={{ width: "24%" }}
          >
            + 384d Granite (optional)
          </div>
        </div>
      </div>

      {/* Live Memory Temperature Simulator */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="flex items-center gap-1.5 text-xs font-semibold text-white">
            <Sliders className="w-3.5 h-3.5 text-amber-400" />
            Interactive Tier &amp; Pruning Simulator
          </span>
          <span
            className="text-xs font-mono font-bold px-2.5 py-0.5 rounded-md border"
            style={{
              color: tier.color,
              borderColor: `${tier.color}55`,
              backgroundColor: `${tier.color}15`,
            }}
          >
            {tier.label}
          </span>
        </div>

        <div className="grid sm:grid-cols-3 gap-4 text-xs">
          <label className="space-y-1">
            <span className="flex justify-between font-mono text-slate-400">
              <span>Days since access</span>
              <span className="text-white">{daysAgo}d</span>
            </span>
            <input
              type="range"
              min={0}
              max={120}
              value={daysAgo}
              onChange={(e) => setDaysAgo(Number(e.target.value))}
              className="w-full accent-cyan-400"
            />
          </label>
          <label className="space-y-1">
            <span className="flex justify-between font-mono text-slate-400">
              <span>touch_count</span>
              <span className="text-white">{touchCount}</span>
            </span>
            <input
              type="range"
              min={0}
              max={15}
              value={touchCount}
              onChange={(e) => setTouchCount(Number(e.target.value))}
              className="w-full accent-amber-400"
            />
          </label>
          <label className="flex items-center gap-2 pt-3 cursor-pointer text-slate-300 font-mono">
            <input
              type="checkbox"
              checked={longTerm}
              onChange={(e) => setLongTerm(e.target.checked)}
              className="rounded border-slate-700 accent-emerald-400"
            />
            long_term = true
          </label>
        </div>

        <p className="text-xs text-slate-400">{tier.reason}</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 5. Interactive Knowledge Graph Topology & Hop Decay SVG
// ---------------------------------------------------------------------------
export function VisualGraphTopology() {
  const [hops, setHops] = useState(3);
  const alpha = 0.85;

  const hopCurve = useMemo(() => {
    const steps = Math.min(8, Math.max(2, hops));
    return Array.from({ length: steps }, (_, idx) => {
      const k = idx + 1;
      const influence = Number(Math.pow(alpha, k).toFixed(3));
      return { k, influence };
    });
  }, [hops]);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-mono uppercase tracking-wider text-purple-300">
            Typed Graph Topology &amp; Bounded Diffusion
          </p>
          <p className="text-xs text-slate-400">
            Visual representation of inheritance, opposition, semantic, and
            causal edges plus geometric hop decay.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="text-slate-400">graph_max_hops:</span>
          <input
            type="range"
            min={1}
            max={24}
            value={hops}
            onChange={(e) => setHops(Number(e.target.value))}
            className="w-24 accent-purple-400"
          />
          <span className="text-purple-300 w-6 text-right">{hops}</span>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4 items-center">
        {/* Clean SVG Knowledge Graph */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3">
          <svg
            viewBox="0 0 360 190"
            className="w-full h-auto"
            role="img"
            aria-label="FAIM knowledge graph edge relationships diagram"
          >
            {/* Edges */}
            <line
              x1="180"
              y1="36"
              x2="92"
              y2="98"
              stroke="#60a5fa"
              strokeWidth="2"
            />
            <line
              x1="180"
              y1="36"
              x2="268"
              y2="98"
              stroke="#60a5fa"
              strokeWidth="2"
            />
            <line
              x1="92"
              y1="98"
              x2="268"
              y2="98"
              stroke="#f87171"
              strokeWidth="2"
              strokeDasharray="5 4"
            />
            <line
              x1="92"
              y1="98"
              x2="132"
              y2="158"
              stroke="#a78bfa"
              strokeWidth="2"
            />
            <line
              x1="268"
              y1="98"
              x2="228"
              y2="158"
              stroke="#fbbf24"
              strokeWidth="2"
            />

            {/* Edge labels */}
            <text
              x="104"
              y="62"
              fill="#60a5fa"
              fontSize="9"
              fontFamily="monospace"
            >
              inheritance
            </text>
            <text
              x="206"
              y="62"
              fill="#60a5fa"
              fontSize="9"
              fontFamily="monospace"
            >
              inheritance
            </text>
            <text
              x="148"
              y="92"
              fill="#f87171"
              fontSize="9"
              fontFamily="monospace"
            >
              opposition
            </text>
            <text
              x="58"
              y="138"
              fill="#a78bfa"
              fontSize="9"
              fontFamily="monospace"
            >
              semantic
            </text>
            <text
              x="256"
              y="138"
              fill="#fbbf24"
              fontSize="9"
              fontFamily="monospace"
            >
              causal
            </text>

            {/* Nodes */}
            <circle
              cx="180"
              cy="36"
              r="18"
              fill="#0f172a"
              stroke="#22d3ee"
              strokeWidth="2"
            />
            <text
              x="180"
              y="39"
              textAnchor="middle"
              fill="#67e8f9"
              fontSize="9"
              fontFamily="monospace"
            >
              Macro
            </text>

            <circle
              cx="92"
              cy="98"
              r="17"
              fill="#0f172a"
              stroke="#34d399"
              strokeWidth="2"
            />
            <text
              x="92"
              y="101"
              textAnchor="middle"
              fill="#6ee7b7"
              fontSize="9"
              fontFamily="monospace"
            >
              Atom A
            </text>

            <circle
              cx="268"
              cy="98"
              r="17"
              fill="#0f172a"
              stroke="#f87171"
              strokeWidth="2"
            />
            <text
              x="268"
              y="101"
              textAnchor="middle"
              fill="#fca5a5"
              fontSize="9"
              fontFamily="monospace"
            >
              Old A*
            </text>

            <circle
              cx="132"
              cy="158"
              r="16"
              fill="#0f172a"
              stroke="#a78bfa"
              strokeWidth="2"
            />
            <text
              x="132"
              y="161"
              textAnchor="middle"
              fill="#ddd6fe"
              fontSize="9"
              fontFamily="monospace"
            >
              Atom B
            </text>

            <circle
              cx="228"
              cy="158"
              r="16"
              fill="#0f172a"
              stroke="#fbbf24"
              strokeWidth="2"
            />
            <text
              x="228"
              y="161"
              textAnchor="middle"
              fill="#fde68a"
              fontSize="9"
              fontFamily="monospace"
            >
              Effect
            </text>
          </svg>
        </div>

        {/* Geometric Decay Preview */}
        <div className="space-y-2">
          <p className="text-xs font-mono text-slate-300">
            Diffusion Decay at alpha = {alpha} (First {hopCurve.length} hops)
          </p>
          {hopCurve.map((pt) => (
            <div key={pt.k} className="space-y-1">
              <div className="flex justify-between text-[11px] font-mono text-slate-400">
                <span>Hop {pt.k}</span>
                <span className="text-purple-300">
                  {(pt.influence * 100).toFixed(1)}% carry
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-950 border border-slate-800 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-purple-400 to-cyan-400"
                  style={{ width: `${Math.round(pt.influence * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 6. Interactive 7-Component Scoring & Extractive Confidence Simulator
// ---------------------------------------------------------------------------
export function VisualScoreCalculator({
  mode = "scoring",
}: {
  mode?: "scoring" | "confidence";
}) {
  const [sim, setSim] = useState(0.84);
  const [novel, setNovel] = useState(0.6);
  const [opp, setOpp] = useState(0.0);
  const [rec, setRec] = useState(0.8);
  const [profile, setProfile] = useState<"DEFAULT" | "STRICT">("DEFAULT");

  // Confidence controls
  const [avgSpan, setAvgSpan] = useState(0.85);
  const [uniqueDocs, setUniqueDocs] = useState(3);
  const [activeRatio, setActiveRatio] = useState(1.0);
  const [conflicts, setConflicts] = useState(0);

  const weights =
    profile === "STRICT"
      ? {
          sim: 0.5,
          novel: 0.2,
          opp: 0.1,
          red: 0.05,
          rec: 0.05,
          use: 0.05,
          lvl: 0.05,
        }
      : {
          sim: 0.4,
          novel: 0.15,
          opp: 0.1,
          red: 0.1,
          rec: 0.1,
          use: 0.1,
          lvl: 0.05,
        };

  const nodeScore =
    weights.sim * sim +
    weights.novel * novel -
    weights.opp * opp +
    weights.rec * rec +
    weights.use * 0.5;

  const breadth = Math.min(1.0, uniqueDocs / 3.0);
  const penalty = Math.min(0.5, 0.15 * conflicts);
  const confidence = Math.max(
    0,
    Math.min(1, 0.45 * avgSpan + 0.3 * breadth + 0.25 * activeRatio - penalty),
  );

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-mono uppercase tracking-wider text-amber-300">
            {mode === "confidence"
              ? "Live Evidence Confidence Calculator"
              : "Live 7-Component Node Scorer (query_engine.py)"}
          </p>
          <p className="text-xs text-slate-400">
            {mode === "confidence"
              ? "Verified formula: clamp(0.45*span + 0.30*breadth + 0.25*active - min(0.5, 0.15*conflicts))"
              : "Adjust signal values using exact DEFAULT_WEIGHTS and STRICT_WEIGHTS profiles."}
          </p>
        </div>
        {mode === "scoring" && (
          <div className="flex gap-1.5">
            {(["DEFAULT", "STRICT"] as const).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setProfile(p)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-mono border ${
                  profile === p
                    ? "bg-amber-500/15 border-amber-500/40 text-amber-200"
                    : "bg-slate-950/60 border-slate-800 text-slate-400"
                }`}
              >
                {p}_WEIGHTS
              </button>
            ))}
          </div>
        )}
      </div>

      {mode === "confidence" ? (
        <div className="space-y-4">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
            <label className="space-y-1">
              <span className="flex justify-between font-mono text-slate-400">
                <span>Avg Span</span>
                <span className="text-white">{avgSpan.toFixed(2)}</span>
              </span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={avgSpan}
                onChange={(e) => setAvgSpan(Number(e.target.value))}
                className="w-full accent-cyan-400"
              />
            </label>
            <label className="space-y-1">
              <span className="flex justify-between font-mono text-slate-400">
                <span>Unique Docs</span>
                <span className="text-white">{uniqueDocs}</span>
              </span>
              <input
                type="range"
                min={1}
                max={5}
                value={uniqueDocs}
                onChange={(e) => setUniqueDocs(Number(e.target.value))}
                className="w-full accent-emerald-400"
              />
            </label>
            <label className="space-y-1">
              <span className="flex justify-between font-mono text-slate-400">
                <span>Active Ratio</span>
                <span className="text-white">{activeRatio.toFixed(2)}</span>
              </span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={activeRatio}
                onChange={(e) => setActiveRatio(Number(e.target.value))}
                className="w-full accent-purple-400"
              />
            </label>
            <label className="space-y-1">
              <span className="flex justify-between font-mono text-slate-400">
                <span>Conflicts</span>
                <span className="text-red-300">{conflicts}</span>
              </span>
              <input
                type="range"
                min={0}
                max={4}
                value={conflicts}
                onChange={(e) => setConflicts(Number(e.target.value))}
                className="w-full accent-red-400"
              />
            </label>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400">
              Bounded Evidence Confidence in [0, 1]
            </span>
            <span className="text-lg font-mono font-bold text-emerald-300">
              {confidence.toFixed(3)}
            </span>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
            <label className="space-y-1">
              <span className="flex justify-between font-mono text-slate-400">
                <span>sim (w={weights.sim})</span>
                <span className="text-white">{sim.toFixed(2)}</span>
              </span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.02}
                value={sim}
                onChange={(e) => setSim(Number(e.target.value))}
                className="w-full accent-cyan-400"
              />
            </label>
            <label className="space-y-1">
              <span className="flex justify-between font-mono text-slate-400">
                <span>novel (w={weights.novel})</span>
                <span className="text-white">{novel.toFixed(2)}</span>
              </span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={novel}
                onChange={(e) => setNovel(Number(e.target.value))}
                className="w-full accent-purple-400"
              />
            </label>
            <label className="space-y-1">
              <span className="flex justify-between font-mono text-slate-400">
                <span>recency (w={weights.rec})</span>
                <span className="text-white">{rec.toFixed(2)}</span>
              </span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={rec}
                onChange={(e) => setRec(Number(e.target.value))}
                className="w-full accent-emerald-400"
              />
            </label>
            <label className="space-y-1">
              <span className="flex justify-between font-mono text-slate-400">
                <span>opp penalty (w={weights.opp})</span>
                <span className="text-red-300">{opp.toFixed(2)}</span>
              </span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={opp}
                onChange={(e) => setOpp(Number(e.target.value))}
                className="w-full accent-red-400"
              />
            </label>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-mono text-slate-400">
              Deterministic Base Score (with fixed use=0.5, red=0, lvl=0)
            </span>
            <span className="text-lg font-mono font-bold text-cyan-300">
              {nodeScore.toFixed(4)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 7. Interactive Dynamic CPU/GPU Routing Decision Simulator
// ---------------------------------------------------------------------------
export function VisualHybridRouter() {
  const [profile, setProfile] = useState<"FAST" | "BALANCED" | "STRICT">(
    "FAST",
  );
  const [language, setLanguage] = useState<"en" | "non-en">("en");
  const [envMode, setEnvMode] = useState<"auto" | "false" | "true">("auto");

  const result = useMemo(() => {
    const isFast = profile === "FAST";
    if (envMode === "false") {
      return isFast
        ? {
            useMl: false,
            reason: "fast_pure_forced",
            engine: "FAIM-Pure (256-dim Native Core)",
            color: "#34d399",
          }
        : {
            useMl: true,
            reason: "regular_embedding",
            engine: "Granite 97M Dense (384-dim) + Native Core",
            color: "#a78bfa",
          };
    }
    if (envMode === "true") {
      return {
        useMl: true,
        reason: isFast ? "ml_embedding_forced" : "regular_embedding",
        engine: "Granite 97M Dense (384-dim) + Native Core",
        color: "#a78bfa",
      };
    }
    if (!isFast) {
      return {
        useMl: true,
        reason: "regular_embedding",
        engine: "Granite 97M Dense (384-dim) + Native Core",
        color: "#a78bfa",
      };
    }
    if (language === "en") {
      return {
        useMl: false,
        reason: "fast_pure_english",
        engine: "FAIM-Pure Zero-ML CPU Fast Path (256-dim)",
        color: "#34d399",
      };
    }
    return {
      useMl: true,
      reason: "fast_multilingual_embedding",
      engine: "Granite 97M Multilingual Dense (384-dim)",
      color: "#22d3ee",
    };
  }, [profile, language, envMode]);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
      <div>
        <p className="text-xs font-mono uppercase tracking-wider text-cyan-300">
          Live Routing Simulator (resolve_fast_ml_embedding_mode)
        </p>
        <p className="text-xs text-slate-400">
          Select query profile, text language, and environment override to see
          exact backend engine selection.
        </p>
      </div>

      <div className="grid sm:grid-cols-3 gap-3 text-xs">
        <div className="space-y-1.5">
          <p className="font-mono text-slate-400">Query Profile</p>
          <div className="flex gap-1">
            {(["FAST", "BALANCED", "STRICT"] as const).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setProfile(p)}
                className={`flex-1 py-1.5 rounded-lg font-mono border text-[11px] ${
                  profile === p
                    ? "bg-cyan-500/15 border-cyan-500/40 text-cyan-200"
                    : "bg-slate-950/60 border-slate-800 text-slate-400"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
        <div className="space-y-1.5">
          <p className="font-mono text-slate-400">Detected Text Language</p>
          <div className="flex gap-1">
            {(
              [
                ["en", "English"],
                ["non-en", "DE / ES / FR / NL"],
              ] as const
            ).map(([k, lbl]) => (
              <button
                key={k}
                type="button"
                onClick={() => setLanguage(k)}
                className={`flex-1 py-1.5 rounded-lg font-mono border text-[11px] ${
                  language === k
                    ? "bg-purple-500/15 border-purple-500/40 text-purple-200"
                    : "bg-slate-950/60 border-slate-800 text-slate-400"
                }`}
              >
                {lbl}
              </button>
            ))}
          </div>
        </div>
        <div className="space-y-1.5">
          <p className="font-mono text-slate-400">FAIM_FAST_ML_EMBEDDING</p>
          <div className="flex gap-1">
            {(["auto", "false", "true"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setEnvMode(m)}
                className={`flex-1 py-1.5 rounded-lg font-mono border text-[11px] ${
                  envMode === m
                    ? "bg-amber-500/15 border-amber-500/40 text-amber-200"
                    : "bg-slate-950/60 border-slate-800 text-slate-400"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div
        className="rounded-xl border bg-slate-950/80 p-4 flex flex-wrap items-center justify-between gap-3"
        style={{ borderColor: `${result.color}55` }}
      >
        <div className="flex items-center gap-2.5">
          {result.useMl ? (
            <Sparkles className="w-4 h-4 text-purple-300 shrink-0" />
          ) : (
            <Zap className="w-4 h-4 text-emerald-300 shrink-0" />
          )}
          <div>
            <p className="text-xs font-semibold text-white">{result.engine}</p>
            <p className="text-[11px] font-mono text-slate-400">
              Decision reason:{" "}
              <span style={{ color: result.color }}>{result.reason}</span>
            </p>
          </div>
        </div>
        <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
          ML Embedding: {result.useMl ? "true" : "false"}
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 8. Measured Semantic Registry Composition Graphic
// ---------------------------------------------------------------------------
export function VisualLexiconDistribution() {
  const langs = [
    { code: "EN", name: "English" },
    { code: "DE", name: "German" },
    { code: "ES", name: "Spanish" },
    { code: "FR", name: "French" },
    { code: "IT", name: "Italian" },
    { code: "NL", name: "Dutch" },
    { code: "PT", name: "Portuguese" },
  ];

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-mono uppercase tracking-wider text-amber-300">
            Shipped Semantic Registry Runtime Composition
          </p>
          <p className="text-xs text-slate-400">
            Exact measured term counts loaded into memory from compressed
            deterministic assets (2,319,589 total terms).
          </p>
        </div>
        <span className="text-xs font-mono font-bold text-white px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800">
          2,319,589 Terms
        </span>
      </div>

      {/* Proportional bar */}
      <div className="h-6 w-full rounded-xl overflow-hidden flex border border-slate-800 font-mono text-[10px]">
        <div
          className="bg-cyan-500/30 border-r border-cyan-500/40 flex items-center justify-center text-cyan-200 px-2"
          style={{ width: "93.68%" }}
        >
          ConceptNet Keys: 2,172,991 (93.7%)
        </div>
        <div
          className="bg-emerald-500/30 flex items-center justify-center text-emerald-200 px-1 truncate"
          style={{ width: "6.32%" }}
          title="Static Multilingual Surfaces: 146,598"
        >
          146.6K
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {langs.map((l) => (
          <span
            key={l.code}
            className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-slate-950/70 border border-slate-800 text-slate-300"
          >
            <strong className="text-emerald-300">{l.code}</strong> {l.name}
          </span>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 9. Focused Domain Infographics (Security, Extraction, API/MCP, Plans, Deploy)
// ---------------------------------------------------------------------------
export function VisualDomainDiagram({
  kind,
}: {
  kind:
    | "security"
    | "extraction"
    | "api"
    | "mcp"
    | "fig"
    | "deployment"
    | "billing";
}) {
  if (kind === "security") {
    const chain = [
      {
        icon: Shield,
        title: "JWT / API Key Auth",
        detail: "Token-derived tenant + graph scope",
      },
      {
        icon: Layers,
        title: "PostgreSQL Row Scoping",
        detail: "Strict tenant_id & graph_id filtering",
      },
      {
        icon: Lock,
        title: "Envelope DEK/KEK Crypto",
        detail: "Rotatable master key wrapping",
      },
      {
        icon: Database,
        title: "SHA-256 Lineage",
        detail: "Immutable packet_hash + vector_hash",
      },
    ];
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
        <p className="text-xs font-mono uppercase tracking-wider text-emerald-300 mb-3">
          Zero-Trust Verification &amp; Isolation Boundary
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {chain.map((step, i) => {
            const Icon = step.icon;
            return (
              <div
                key={step.title}
                className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <Icon className="w-4 h-4 text-emerald-400" />
                  <span className="text-[10px] font-mono text-slate-600">
                    GATE 0{i + 1}
                  </span>
                </div>
                <p className="text-xs font-semibold text-white">{step.title}</p>
                <p className="text-[11px] text-slate-400">{step.detail}</p>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  if (kind === "extraction") {
    const formats = [
      {
        fmt: "PDF",
        parser: "PyMuPDF + X-gap columns",
        special: "300 DPI Tesseract OCR on scan pages",
      },
      {
        fmt: "DOCX",
        parser: "python-docx",
        special: "Heading tree + table header preservation",
      },
      {
        fmt: "PPTX",
        parser: "python-pptx",
        special: "Sorted shape coordinates + speaker notes",
      },
      {
        fmt: "XLSX",
        parser: "openpyxl (data_only)",
        special: "Sheet + row range anchoring",
      },
      {
        fmt: "Figures",
        parser: "PyMuPDF type=1 image blocks",
        special: "bbox (x0/y0/x1/y1) + pHash fingerprint",
      },
    ];
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
        <p className="text-xs font-mono uppercase tracking-wider text-cyan-300 mb-3">
          Deterministic Multi-Format Extraction Surface
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
          {formats.map((f) => (
            <div
              key={f.fmt}
              className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 space-y-1"
            >
              <span className="text-xs font-mono font-bold text-cyan-300">
                {f.fmt}
              </span>
              <p className="text-[11px] font-medium text-white">{f.parser}</p>
              <p className="text-[10px] text-slate-400">{f.special}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (kind === "deployment") {
    const targets = [
      {
        icon: Cpu,
        title: "CPU-Only VPS",
        vars: "FAIM_CONTAINER_RUNTIME=runc | FAIM_EMBEDDING_DEVICE=cpu",
        detail:
          "Zero GPU requirement. Ideal for FAIM-Pure fast paths and compact self-hosting.",
      },
      {
        icon: Zap,
        title: "NVIDIA CUDA Host",
        vars: "FAIM_CONTAINER_RUNTIME=nvidia | FAIM_EMBEDDING_DEVICE=auto",
        detail:
          "Unlocks CUDA inference for Granite 97M R2 via the exact same docker-compose.yml.",
      },
      {
        icon: Network,
        title: "Production Edge",
        vars: "docker compose --profile vps up -d + Caddyfile.vps",
        detail:
          "Automated HTTPS termination and clean upstream routing across API, MCP, and Next.js.",
      },
    ];
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
        <p className="text-xs font-mono uppercase tracking-wider text-purple-300 mb-3">
          Single-Compose Unified Deployment Targets
        </p>
        <div className="grid md:grid-cols-3 gap-3">
          {targets.map((t) => {
            const Icon = t.icon;
            return (
              <div
                key={t.title}
                className="rounded-xl border border-slate-800 bg-slate-950/70 p-3.5 space-y-1.5"
              >
                <div className="flex items-center gap-2">
                  <Icon className="w-4 h-4 text-purple-300" />
                  <p className="text-xs font-semibold text-white">{t.title}</p>
                </div>
                <p className="text-[10px] font-mono text-cyan-300 break-words">
                  {t.vars}
                </p>
                <p className="text-[11px] text-slate-400">{t.detail}</p>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  if (kind === "billing") {
    const tiers = [
      {
        name: "Explorer",
        price: "$0",
        nodes: "1,000",
        hops: "1 Hop",
        width: 15,
        color: "#94a3b8",
      },
      {
        name: "Architect",
        price: "$29/mo",
        nodes: "10,000",
        hops: "4 Hops",
        width: 40,
        color: "#22d3ee",
      },
      {
        name: "Neural",
        price: "$99/mo",
        nodes: "100,000",
        hops: "24 Hops",
        width: 72,
        color: "#a78bfa",
      },
      {
        name: "Matrix",
        price: "Custom",
        nodes: "Unlimited",
        hops: "Custom",
        width: 100,
        color: "#34d399",
      },
    ];
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-3">
        <p className="text-xs font-mono uppercase tracking-wider text-purple-300">
          Cognitive Capacity &amp; Reasoning Depth Scaling
        </p>
        {tiers.map((t) => (
          <div key={t.name} className="space-y-1">
            <div className="flex justify-between text-xs font-mono">
              <span className="text-white font-semibold">
                {t.name} ({t.price})
              </span>
              <span className="text-slate-400">
                {t.nodes} nodes | {t.hops}
              </span>
            </div>
            <div className="h-2.5 w-full rounded-full bg-slate-950 border border-slate-800 overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{ width: `${t.width}%`, backgroundColor: t.color }}
              />
            </div>
          </div>
        ))}
      </div>
    );
  }

  // api / mcp / fig unified node topology graphic
  const nodes =
    kind === "mcp"
      ? [
          { tag: "faim_query", role: "Hybrid + bounded hop query" },
          { tag: "faim_memory_search", role: "Direct memory search" },
          { tag: "faim_memory_write", role: "Idempotent node upsert" },
          { tag: "faim_ingest_text", role: "Raw block ingestion" },
          { tag: "faim_memory_get", role: "Node + provenance lookup" },
          { tag: "faim_graph_surface", role: "3D surface export" },
        ]
      : kind === "fig"
        ? [
            { tag: "Surface (500 nodes)", role: "Overview cluster galaxy" },
            {
              tag: "Neighborhood (K-hop)",
              role: "Local seed radius inspection",
            },
            { tag: "Timeline", role: "Chronological node growth" },
            { tag: "Path (Pulse-v2)", role: "Exact causal & reasoning path" },
            { tag: "Analyze", role: "Density D, Entropy H, Spectral lambda" },
            {
              tag: "6 Overlays",
              role: "Cognitive, Retrieval, Evolution, Time, Causal",
            },
          ]
        : [
            { tag: "GET /health & /ready", role: "Public readiness probes" },
            {
              tag: "POST /api/v1/query",
              role: "Hybrid query + explain ledger",
            },
            {
              tag: "POST /api/v1/ingest/upload",
              role: "Document layout extraction",
            },
            {
              tag: "POST /api/v1/memory/*",
              role: "Search & idempotent writes",
            },
            { tag: "GET /api/v1/graph/*", role: "Surface & path provenance" },
            { tag: "POST /mcp", role: "OAuth 2.1 + PKCE agent stream" },
          ];

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
      <div className="flex items-center gap-2 mb-3">
        <GitBranch className="w-4 h-4 text-cyan-400" />
        <p className="text-xs font-mono uppercase tracking-wider text-cyan-300">
          {kind === "mcp"
            ? "6 Exposed MCP Tool Surfaces (/mcp + stdio)"
            : kind === "fig"
              ? "5 Canvas Modes & Pulse-v2 Visual Inspection"
              : "API Surface Topology Map"}
        </p>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
        {nodes.map((n) => (
          <div
            key={n.tag}
            className="rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-2.5"
          >
            <p className="text-xs font-mono text-cyan-300 truncate">{n.tag}</p>
            <p className="text-[11px] text-slate-400 mt-0.5">{n.role}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
