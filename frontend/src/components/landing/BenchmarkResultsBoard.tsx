"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ArrowUpRight,
  CheckCircle2,
  Cpu,
  History,
  Layers,
  ShieldCheck,
} from "lucide-react";

import {
  BENCHMARK_HIGHLIGHTS,
  BENCHMARK_PROFILES,
  BENCHMARK_REPORT_DATE,
  CROSS_SYSTEM_ROWS,
  HISTORICAL_PROGRESSION,
  LOCOMO_CATEGORY_BREAKDOWN,
  type BenchmarkProfileId,
} from "@/lib/benchmarkResults";

const ACCENT_CLASSES: Record<string, string> = {
  cyan: "border-cyan-400/25 bg-cyan-400/[0.05] text-cyan-300",
  emerald: "border-emerald-400/25 bg-emerald-400/[0.05] text-emerald-300",
  purple: "border-purple-400/25 bg-purple-400/[0.05] text-purple-300",
  amber: "border-amber-400/25 bg-amber-400/[0.05] text-amber-300",
};

const STATUS_STYLES: Record<string, string> = {
  Verified: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
  Reference: "border-slate-600/50 bg-slate-800/70 text-slate-300",
};

export default function BenchmarkResultsBoard({
  compact = false,
  showFullPageLink = true,
}: {
  compact?: boolean;
  showFullPageLink?: boolean;
}) {
  const [selectedId, setSelectedId] =
    useState<BenchmarkProfileId>("faim-granite-gpu");
  const activeProfile =
    BENCHMARK_PROFILES.find((item) => item.id === selectedId) ??
    BENCHMARK_PROFILES[0];

  return (
    <div className="space-y-8">
      {/* Executive KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {BENCHMARK_HIGHLIGHTS.map((card) => (
          <div
            key={card.label}
            className={`rounded-2xl border p-5 ${ACCENT_CLASSES[card.accent]}`}
          >
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold tracking-tight text-white">
                {card.value}
              </span>
              <span className="font-mono text-xs uppercase tracking-wider">
                {card.unit}
              </span>
            </div>
            <p className="mt-2 text-xs font-semibold text-slate-200">
              {card.label}
            </p>
            <p className="mt-1 font-mono text-[11px] text-slate-400">
              {card.detail}
            </p>
          </div>
        ))}
      </div>

      {/* Interactive Runtime Profile Explorer */}
      <div className="rounded-2xl border border-slate-700/60 bg-slate-900/50 p-5 sm:p-7">
        <div className="flex flex-col gap-4 border-b border-slate-800 pb-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-cyan-300">
              Signed Production Evaluation Matrix · {BENCHMARK_REPORT_DATE}
            </p>
            <h3 className="mt-1 text-xl font-bold text-white">
              {activeProfile.name}
            </h3>
            <p className="mt-1 text-xs text-slate-400">{activeProfile.mode}</p>
          </div>
          <span className="inline-flex w-fit items-center gap-1.5 rounded-full border border-cyan-400/25 bg-cyan-400/10 px-3 py-1 font-mono text-[11px] text-cyan-200">
            <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
            {activeProfile.badge}
          </span>
        </div>

        {/* Profile Tabs */}
        <div className="mt-4 flex flex-wrap gap-2">
          {BENCHMARK_PROFILES.map((profile) => {
            const active = profile.id === activeProfile.id;
            return (
              <button
                key={profile.id}
                type="button"
                onClick={() => setSelectedId(profile.id)}
                className={`rounded-xl border px-3 py-1.5 text-xs font-medium transition-all ${
                  active
                    ? "border-cyan-400/50 bg-cyan-400/15 text-white shadow-sm shadow-cyan-500/10"
                    : "border-slate-700/60 bg-slate-950/50 text-slate-400 hover:border-slate-600 hover:text-slate-200"
                }`}
              >
                {profile.shortLabel}
              </button>
            );
          })}
        </div>

        <p className="mt-4 rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-xs leading-relaxed text-slate-300">
          <span className="font-semibold text-white">Runtime Profile: </span>
          {activeProfile.hardware}. {activeProfile.summary}
        </p>

        {/* Active Profile Results Table */}
        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[680px] border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 font-mono text-[10px] uppercase tracking-wider text-slate-400">
                <th className="py-3 pr-4">Dataset</th>
                <th className="py-3 pr-4">Primary Accuracy</th>
                <th className="py-3 pr-4">Secondary Metrics</th>
                <th className="py-3 pr-4 text-right">P50</th>
                <th className="py-3 pr-4 text-right">P95</th>
                <th className="py-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {activeProfile.rows.map((row) => (
                <tr key={row.dataset} className="hover:bg-slate-950/40">
                  <td className="py-3.5 pr-4">
                    <p className="font-semibold text-white">{row.label}</p>
                    <p className="text-[11px] text-slate-500">{row.task}</p>
                  </td>
                  <td className="py-3.5 pr-4 font-mono">
                    <span className="text-slate-400">
                      {row.primaryMetricName}:{" "}
                    </span>
                    <span className="font-bold text-cyan-200">
                      {row.primaryMetricValue}
                    </span>
                  </td>
                  <td className="py-3.5 pr-4 font-mono text-[11px] text-slate-300">
                    {row.secondaryMetrics}
                  </td>
                  <td className="py-3.5 pr-4 text-right font-mono text-slate-200">
                    {row.p50Ms}
                  </td>
                  <td className="py-3.5 pr-4 text-right font-mono text-slate-400">
                    {row.p95Ms}
                  </td>
                  <td className="py-3.5 text-right">
                    <span
                      className={`inline-block rounded-full border px-2 py-0.5 font-mono text-[10px] ${STATUS_STYLES[row.status]}`}
                    >
                      {row.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Head-to-Head + Before-vs-After Engine Progression */}
      {!compact && (
        <>
          <div className="grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
            <div className="rounded-2xl border border-slate-700/60 bg-slate-900/40 p-6">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-purple-300">
                <Layers className="h-4 w-4" aria-hidden="true" />
                Cross-Engine Retrieval Matrix (Locked Full Splits)
              </div>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[680px] border-collapse text-left text-[11px]">
                  <thead>
                    <tr className="border-b border-slate-800 font-mono text-[10px] uppercase text-slate-400">
                      <th className="py-2.5 pr-3">Suite</th>
                      <th className="py-2.5 pr-3 text-cyan-300">
                        FAIM + Granite GPU
                      </th>
                      <th className="py-2.5 pr-3 text-emerald-300">
                        FAIM-Pure CPU
                      </th>
                      <th className="py-2.5 pr-3 text-purple-200">
                        Granite 97M Alone
                      </th>
                      <th className="py-2.5">BM25 Baseline</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/70 font-mono">
                    {CROSS_SYSTEM_ROWS.map((row) => (
                      <tr key={row.dataset}>
                        <td className="py-3 pr-3 font-sans font-semibold text-white">
                          {row.dataset}
                        </td>
                        <td className="py-3 pr-3 text-cyan-100">
                          {row.graniteHybrid}
                        </td>
                        <td className="py-3 pr-3 text-emerald-100">
                          {row.pureCpu}
                        </td>
                        <td className="py-3 pr-3 text-slate-300">
                          {row.standaloneGranite}
                        </td>
                        <td className="py-3 text-slate-400">
                          {row.bm25Baseline}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-700/60 bg-slate-900/40 p-6">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-amber-300">
                <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                LoCoMo Category Breakdown
              </div>
              <p className="mt-2 text-xs leading-relaxed text-slate-400">
                Compact extractive mode emits an average of `11.9` context
                tokens (vs `92.3` for BM25), prioritizing precision on{" "}
                <code className="text-slate-200">single_hop</code> and{" "}
                <code className="text-slate-200">adversarial</code> splits while
                keeping multi-hop QA open for active improvement.
              </p>
              <div className="mt-4 space-y-2">
                {LOCOMO_CATEGORY_BREAKDOWN.map((item) => (
                  <div
                    key={item.category}
                    className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2 font-mono text-[11px]"
                  >
                    <span className="text-slate-200">
                      {item.category}{" "}
                      <span className="text-slate-500">({item.count})</span>
                    </span>
                    <span className="text-cyan-300">
                      FR {item.factRecall} · F1 {item.tokenF1}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Historical Progression (Before -> After) */}
          <div className="rounded-2xl border border-slate-700/60 bg-slate-900/40 p-6">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-cyan-300">
              <History className="h-4 w-4" aria-hidden="true" />
              Engine Progression on Full BeIR / SciFact (5,183 Docs / 300
              Queries)
            </div>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[660px] border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 font-mono text-[10px] uppercase tracking-wider text-slate-400">
                    <th className="py-2.5 pr-4">Engine Generation</th>
                    <th className="py-2.5 pr-4">Architecture</th>
                    <th className="py-2.5 pr-4 text-right">Recall@5</th>
                    <th className="py-2.5 pr-4 text-right">nDCG@10</th>
                    <th className="py-2.5 pr-4 text-right">Query P50</th>
                    <th className="py-2.5">Measured Gain</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/70">
                  {HISTORICAL_PROGRESSION.map((item) => (
                    <tr key={item.generation}>
                      <td className="py-3 pr-4 font-semibold text-white">
                        {item.generation}
                      </td>
                      <td className="py-3 pr-4 text-slate-400">
                        {item.architecture}
                      </td>
                      <td className="py-3 pr-4 text-right font-mono text-slate-200">
                        {item.recallAt5}
                      </td>
                      <td className="py-3 pr-4 text-right font-mono font-bold text-cyan-200">
                        {item.ndcgAt10}
                      </td>
                      <td className="py-3 pr-4 text-right font-mono text-emerald-200">
                        {item.p50Ms}
                      </td>
                      <td className="py-3 text-slate-300">
                        {item.deltaSummary}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Dynamic Runtime Routing Callout */}
      <div className="flex flex-col gap-4 rounded-2xl border border-emerald-400/20 bg-emerald-400/[0.04] p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <Cpu
            className="mt-0.5 h-5 w-5 shrink-0 text-emerald-300"
            aria-hidden="true"
          />
          <div className="text-xs leading-relaxed text-slate-300">
            <p className="font-semibold text-white">
              Dynamic Hybrid &amp; CPU-Only Execution (
              <code>FAIM_FAST_ML_EMBEDDING=auto</code>)
            </p>
            <p className="mt-1 text-slate-400">
              In production deployments, English{" "}
              <code className="text-slate-200">FAST</code> traffic runs via
              zero-ML FAIM-Pure while non-English and regular (
              <code className="text-slate-200">STRICT</code> /{" "}
              <code className="text-slate-200">BALANCED</code> /{" "}
              <code className="text-slate-200">RELAXED</code>) traffic routes to
              local Granite 97M on GPU or CPU with automatic fail-open FAIM-Pure
              fallback. Tables above report signed {BENCHMARK_REPORT_DATE}{" "}
              fixed-profile harness artifacts.
            </p>
          </div>
        </div>
        {showFullPageLink && (
          <Link
            href="/benchmarks"
            className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-cyan-400/35 bg-cyan-400/10 px-4 py-2.5 text-xs font-semibold text-cyan-200 transition-colors hover:bg-cyan-400/20"
          >
            Full Benchmark Report
            <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        )}
      </div>
    </div>
  );
}
