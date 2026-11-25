"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ArrowUpRight,
  CheckCircle2,
  Cpu,
  Layers,
  ShieldAlert,
} from "lucide-react";

import {
  BENCHMARK_HIGHLIGHTS,
  BENCHMARK_REPORT_DATE,
  BENCHMARK_SCENARIOS,
  CROSS_SYSTEM_ROWS,
  LOCOMO_CATEGORY_BREAKDOWN,
  type ScenarioId,
} from "@/lib/benchmarkResults";

const ACCENT_CLASSES: Record<string, string> = {
  cyan: "border-cyan-400/25 bg-cyan-400/[0.05] text-cyan-300",
  emerald: "border-emerald-400/25 bg-emerald-400/[0.05] text-emerald-300",
  purple: "border-purple-400/25 bg-purple-400/[0.05] text-purple-300",
  amber: "border-amber-400/25 bg-amber-400/[0.05] text-amber-300",
};

const GATE_STYLES: Record<string, string> = {
  READY: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
  BASELINE: "border-slate-600/50 bg-slate-800/70 text-slate-300",
  STOPPED: "border-amber-400/30 bg-amber-400/10 text-amber-300",
};

export default function BenchmarkResultsBoard({
  compact = false,
  showFullPageLink = true,
}: {
  compact?: boolean;
  showFullPageLink?: boolean;
}) {
  const [selectedId, setSelectedId] = useState<ScenarioId>("3-gpu-granite");
  const activeScenario =
    BENCHMARK_SCENARIOS.find((item) => item.id === selectedId) ??
    BENCHMARK_SCENARIOS[0];

  return (
    <div className="space-y-8">
      {/* KPI Highlights */}
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

      {/* Scenario Explorer */}
      <div className="rounded-2xl border border-slate-700/60 bg-slate-900/50 p-5 sm:p-7">
        <div className="flex flex-col gap-4 border-b border-slate-800 pb-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-cyan-300">
              Signed Scenario Matrix · {BENCHMARK_REPORT_DATE}
            </p>
            <h3 className="mt-1 text-xl font-bold text-white">
              {activeScenario.name}
            </h3>
            <p className="mt-1 text-xs text-slate-400">{activeScenario.mode}</p>
          </div>
          <span className="inline-flex w-fit items-center gap-1.5 rounded-full border border-cyan-400/25 bg-cyan-400/10 px-3 py-1 font-mono text-[11px] text-cyan-200">
            <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
            {activeScenario.badge}
          </span>
        </div>

        {/* Scenario Selector Tabs */}
        <div className="mt-4 flex flex-wrap gap-2">
          {BENCHMARK_SCENARIOS.map((scenario) => {
            const active = scenario.id === activeScenario.id;
            return (
              <button
                key={scenario.id}
                type="button"
                onClick={() => setSelectedId(scenario.id)}
                className={`rounded-xl border px-3 py-1.5 text-xs font-medium transition-all ${
                  active
                    ? "border-cyan-400/50 bg-cyan-400/15 text-white shadow-sm shadow-cyan-500/10"
                    : "border-slate-700/60 bg-slate-950/50 text-slate-400 hover:border-slate-600 hover:text-slate-200"
                }`}
              >
                {scenario.shortLabel}
              </button>
            );
          })}
        </div>

        <p className="mt-4 rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-xs leading-relaxed text-slate-300">
          <span className="font-semibold text-white">
            Hardware &amp; Finding:{" "}
          </span>
          {activeScenario.hardware}. {activeScenario.highlight}
        </p>

        {/* Active Scenario Metrics Table */}
        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[680px] border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 font-mono text-[10px] uppercase tracking-wider text-slate-400">
                <th className="py-3 pr-4">Dataset</th>
                <th className="py-3 pr-4">Primary Accuracy</th>
                <th className="py-3 pr-4">Secondary Metrics</th>
                <th className="py-3 pr-4 text-right">P50</th>
                <th className="py-3 pr-4 text-right">P95</th>
                <th className="py-3 text-right">Gate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {activeScenario.rows.map((row) => (
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
                      className={`inline-block rounded-full border px-2 py-0.5 font-mono text-[10px] ${GATE_STYLES[row.gate]}`}
                    >
                      {row.gate}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Cross-Scenario Summary & Honest LoCoMo Disclosure */}
      {!compact && (
        <div className="grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
          <div className="rounded-2xl border border-slate-700/60 bg-slate-900/40 p-6">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-purple-300">
              <Layers className="h-4 w-4" aria-hidden="true" />
              Head-to-Head Summary (2026-11-24 Full Splits)
            </div>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[640px] border-collapse text-left text-[11px]">
                <thead>
                  <tr className="border-b border-slate-800 font-mono text-[10px] uppercase text-slate-400">
                    <th className="py-2.5 pr-3">Suite</th>
                    <th className="py-2.5 pr-3 text-cyan-300">
                      FAIM + Granite GPU
                    </th>
                    <th className="py-2.5 pr-3 text-emerald-300">
                      Pure FAIM CPU
                    </th>
                    <th className="py-2.5 pr-3">CPU CI (FAST)</th>
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
                        {row.graniteGpu}
                      </td>
                      <td className="py-3 pr-3 text-emerald-100">
                        {row.pureCpuDocker}
                      </td>
                      <td className="py-3 pr-3 text-slate-300">
                        {row.pureCpuCi}
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
              <ShieldAlert className="h-4 w-4" aria-hidden="true" />
              LoCoMo Breakdown (`3-gpu-granite`)
            </div>
            <p className="mt-2 text-xs leading-relaxed text-slate-400">
              Published honestly without omission: FAIM&apos;s extractive span
              mode keeps context tight (`11.9` avg tokens vs BM25&apos;s
              `92.3`), scoring highest on `single_hop` (`0.1011`) and
              `adversarial` (`0.1009`), while `multi_hop` / `temporal` QA remain
              active research areas.
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
      )}

      {/* Dynamic Runtime Routing Callout + Verification Footer */}
      <div className="flex flex-col gap-4 rounded-2xl border border-emerald-400/20 bg-emerald-400/[0.04] p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <Cpu
            className="mt-0.5 h-5 w-5 shrink-0 text-emerald-300"
            aria-hidden="true"
          />
          <div className="text-xs leading-relaxed text-slate-300">
            <p className="font-semibold text-white">
              Dynamic Hybrid &amp; CPU-Only Execution
              (`FAIM_FAST_ML_EMBEDDING=auto`)
            </p>
            <p className="mt-1 text-slate-400">
              In live deployments, English `FAST` requests execute via zero-ML
              FAIM-Pure while non-English `FAST` and regular (`STRICT` /
              `BALANCED` / `RELAXED`) requests invoke Granite 97M on GPU or CPU
              with automatic fail-open FAIM-Pure fallback. Metrics above reflect
              the signed `2026-11-24` fixed-mode scenario runs
              (`faim-benchmarks/results/RESULTS.md`).
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
