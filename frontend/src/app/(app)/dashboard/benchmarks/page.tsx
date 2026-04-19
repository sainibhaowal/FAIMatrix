"use client";

import React, { useEffect, useMemo, useState, useTransition } from "react";
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  Clock3,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { resolveGraphId } from "@/lib/api-client";
import { fetchBenchmarkRunById, fetchBenchmarkRuns, fetchBenchmarkSeries, fetchLatestBenchmark, runBenchmarkSuite } from "@/lib/benchmarks";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type { BenchmarkSeriesPoint, BenchmarkSuiteRun } from "@/types/benchmarks";

type MetricCardProps = {
  label: string;
  value: string;
  sub: string;
  icon: React.ReactNode;
  accent: string;
};

function MetricCard({ label, value, sub, icon, accent }: MetricCardProps) {
  return (
    <div className="rounded-xl border p-5" style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-1)" }}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-[10px] font-medium uppercase tracking-[0.24em] text-slate-500">{label}</p>
        <div className="opacity-70" style={{ color: accent }}>{icon}</div>
      </div>
      <div className="mt-4 text-[30px] font-semibold leading-none tabular-nums" style={{ color: accent }}>
        {value}
      </div>
      <p className="mt-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">{sub}</p>
    </div>
  );
}

function SectionShell({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="overflow-hidden rounded-2xl border" style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-1)" }}>
      <div className="flex items-center justify-between gap-3 border-b px-5 py-3" style={{ borderColor: "var(--os-stroke)" }}>
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-slate-400">{title}</p>
          {subtitle ? <p className="mt-0.5 text-[10px] text-slate-500">{subtitle}</p> : null}
        </div>
      </div>
      {children}
    </section>
  );
}

function formatScore(value: number): string {
  return `${Math.round(value)}%`;
}

function formatLatency(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return "—";
  if (value >= 1000) return `${(value / 1000).toFixed(2)}s`;
  return `${Math.round(value)}ms`;
}

const BENCHMARK_COLORS = ["#34d399", "#22d3ee", "#f59e0b", "#f472b6", "#a78bfa", "#60a5fa", "#f87171", "#fb7185", "#c084fc"];

export default function BenchmarksPage() {
  const graphId = useMemo(() => resolveGraphId(), []);
  const [latest, setLatest] = useState<BenchmarkSuiteRun | null>(null);
  const [series, setSeries] = useState<BenchmarkSeriesPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingSeries, setLoadingSeries] = useState(true);
  const [runs, setRuns] = useState<BenchmarkSuiteRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const refresh = async () => {
    if (!graphId) {
      setLoading(false);
      setLoadingSeries(false);
      setLatest(null);
      setSeries([]);
      return;
    }

    setError(null);
    setLoading(true);
    setLoadingSeries(true);
    try {
      const [latestRun, history] = await Promise.all([
        fetchLatestBenchmark(graphId),
        fetchBenchmarkSeries(graphId),
      ]);
      setLatest(latestRun);
      setSeries(history);
      const historyRuns = await fetchBenchmarkRuns(graphId, 25);
      setRuns(historyRuns);
      if (latestRun?.run_id) {
        setSelectedRunId(latestRun.run_id);
      }
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Failed to load benchmarks");
    } finally {
      setLoading(false);
      setLoadingSeries(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, [graphId]);

  const latestBenchmarks = latest?.benchmarks ?? [];
  const scoreData = latestBenchmarks.map((item) => ({
    name: item.benchmark_id,
    label: item.name,
    score: item.score,
    passed: item.passed,
  }));

  const latencyData = series.slice(-12).map((point) => ({
    timestamp: point.timestamp ? new Date(point.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "now",
    store: point.latency.store_p50_ms,
    retrieve: point.latency.retrieve_p50_ms,
    p95: point.latency.retrieve_p95_ms,
  }));

  const summaryCards = latest
    ? [
        { label: "Overall Score", value: formatScore(latest.overall_score), sub: `${latest.passed_count}/${latest.benchmark_count} benchmarks passed`, icon: <Sparkles size={18} />, accent: "#34d399" },
        { label: "Graph Integrity", value: latest.graph_hash.slice(0, 12), sub: `Diagnostics ${latest.diagnostics_hash.slice(0, 12)}`, icon: <ShieldCheck size={18} />, accent: "#22d3ee" },
        { label: "Latency", value: formatLatency(Number(latest.summary?.latest_ingest_latency_ms ?? latest.duration_ms)), sub: `Run duration ${formatLatency(latest.duration_ms)}`, icon: <Clock3 size={18} />, accent: "#f59e0b" },
        { label: "Throughput", value: latest.throughput_synapses_per_sec.toFixed(1), sub: "synapses / sec", icon: <Activity size={18} />, accent: "#60a5fa" },
      ]
    : [
        { label: "Overall Score", value: "—", sub: "Run the suite to collect evidence", icon: <Sparkles size={18} />, accent: "#34d399" },
        { label: "Graph Integrity", value: "—", sub: "No benchmark run yet", icon: <ShieldCheck size={18} />, accent: "#22d3ee" },
        { label: "Latency", value: "—", sub: "Waiting for ingest evidence", icon: <Clock3 size={18} />, accent: "#f59e0b" },
        { label: "Throughput", value: "—", sub: "Waiting for live telemetry", icon: <Activity size={18} />, accent: "#60a5fa" },
      ];

  return (
    <div className="relative space-y-5 pb-8 px-1 text-slate-100">
      <div className="faim-grid" />

      <GlassHeader
        title="Benchmark Evidence"
        subtitle="Live BM-1 to BM-9 proof suite with real graph, latency, and isolation evidence"
        icon={BarChart3}
        actions={
          <div className="flex items-center gap-2">
            <Badge variant="outline" size="md" className="border-cyan-500/30 bg-cyan-500/5 text-cyan-300">
              {graphId || "No graph selected"}
            </Badge>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                startTransition(() => {
                  void runBenchmarkSuite(graphId).then((result) => {
                    if (result) {
                      setLatest(result);
                      setSelectedRunId(result.run_id);
                      void refresh();
                    }
                  });
                });
              }}
              disabled={!graphId || isPending}
            >
              {isPending ? "Running..." : "Run Benchmark Suite"}
            </Button>
          </div>
        }
      />

      {error ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {summaryCards.map((card) => (
          <MetricCard
            key={card.label}
            label={card.label}
            value={loading ? "…" : card.value}
            sub={card.sub}
            icon={card.icon}
            accent={card.accent}
          />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-5">
        <div className="xl:col-span-3">
          <SectionShell title="BM-1 to BM-9 Scores" subtitle="Each score is derived from the live backend benchmark run">
            <div className="p-5">
              {loading ? (
                <div className="h-64 animate-pulse rounded-xl bg-white/5" />
              ) : scoreData.length ? (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={scoreData} margin={{ top: 10, right: 16, left: 0, bottom: 10 }}>
                      <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />
                      <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} />
                      <YAxis domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} />
                      <Tooltip
                        contentStyle={{ background: "#07111d", border: "1px solid rgba(148,163,184,0.2)", borderRadius: 12 }}
                        formatter={(value) => [`${Number(value).toFixed(1)}%`, "Score"]}
                        labelFormatter={(label, payload) => payload?.[0]?.payload?.label ?? label}
                      />
                      <Bar dataKey="score" radius={[10, 10, 0, 0]}>
                        {scoreData.map((entry, index) => (
                          <Cell key={entry.name} fill={BENCHMARK_COLORS[index % BENCHMARK_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-slate-700/70 px-4 py-12 text-center text-sm text-slate-500">
                  No benchmark run exists yet. Run the suite to collect real BM-1 to BM-9 evidence.
                </div>
              )}
            </div>
          </SectionShell>
        </div>

        <div className="xl:col-span-2">
          <SectionShell title="Evidence Summary" subtitle="The latest run is stored as append-only event data">
            <div className="space-y-4 p-5">
              {latest ? (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl border px-4 py-3" style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-2)" }}>
                      <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">Graph Nodes</p>
                      <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-100">{latest.node_count}</p>
                    </div>
                    <div className="rounded-xl border px-4 py-3" style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-2)" }}>
                      <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">Graph Edges</p>
                      <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-100">{latest.edge_count}</p>
                    </div>
                    <div className="rounded-xl border px-4 py-3" style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-2)" }}>
                      <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">Compression</p>
                      <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-100">{latest.compression_ratio.toFixed(3)}</p>
                    </div>
                    <div className="rounded-xl border px-4 py-3" style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-2)" }}>
                      <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">Budget</p>
                      <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-100">{latest.budget_profile}</p>
                    </div>
                  </div>

                  <div className="rounded-2xl border p-4" style={{ borderColor: "var(--os-stroke)", background: "rgba(14,19,30,0.7)" }}>
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">Latest Evidence</p>
                        <p className="mt-1 text-xs text-slate-500">Run {latest.run_id.slice(0, 12)} · {new Date(latest.computed_at).toLocaleString()}</p>
                      </div>
                      <Badge variant="outline" size="sm" className="border-emerald-500/30 text-emerald-300">
                        {latest.overall_score.toFixed(1)}%
                      </Badge>
                    </div>
                    <div className="mt-4 space-y-2 text-sm text-slate-300">
                      {latest.benchmarks.map((item) => (
                        <div key={item.benchmark_id} className="flex items-center justify-between rounded-lg border px-3 py-2" style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-2)" }}>
                          <div className="flex items-center gap-2">
                            {item.passed ? <CheckCircle2 size={15} className="text-emerald-400" /> : <ShieldCheck size={15} className="text-amber-400" />}
                            <span>{item.benchmark_id} · {item.name}</span>
                          </div>
                          <span className="font-mono text-xs text-slate-400">{item.score.toFixed(1)}% · {item.evidence_hash.slice(0, 8)}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-2xl border p-4" style={{ borderColor: "var(--os-stroke)", background: "rgba(7,17,29,0.72)" }}>
                    <div className="mb-3 flex items-center justify-between gap-2">
                      <p className="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">Recent Runs</p>
                      <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500">{runs.length} recorded</span>
                    </div>
                    <div className="space-y-2">
                      {runs.length ? runs.slice().reverse().slice(0, 8).map((run) => (
                        <button
                          key={run.run_id}
                          type="button"
                          className="flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left"
                          style={{
                            borderColor: selectedRunId === run.run_id ? "rgba(52,211,153,0.35)" : "var(--os-stroke)",
                            background: selectedRunId === run.run_id ? "rgba(52,211,153,0.08)" : "var(--os-surface-2)",
                          }}
                          onClick={() => {
                            void fetchBenchmarkRunById(graphId, run.run_id).then((fullRun) => {
                              if (fullRun) {
                                setLatest(fullRun);
                                setSelectedRunId(fullRun.run_id);
                              }
                            });
                          }}
                        >
                          <span className="text-xs text-slate-300">{run.run_id.slice(0, 12)} · {new Date(run.computed_at).toLocaleTimeString()}</span>
                          <span className="font-mono text-xs text-slate-400">{run.overall_score.toFixed(1)}%</span>
                        </button>
                      )) : (
                        <p className="text-xs text-slate-500">No historical runs yet.</p>
                      )}
                    </div>
                  </div>
                </>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-700/70 px-4 py-10 text-sm text-slate-500">
                  This graph has no benchmark history yet. Run the suite to generate a real evidence trail.
                </div>
              )}
            </div>
          </SectionShell>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-5">
        <div className="xl:col-span-3">
          <SectionShell title="Benchmark Timeline" subtitle="Series data returned by the backend benchmark history endpoint">
            <div className="p-5">
              {loadingSeries ? (
                <div className="h-64 animate-pulse rounded-xl bg-white/5" />
              ) : latencyData.length ? (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={latencyData} margin={{ top: 10, right: 16, left: 0, bottom: 10 }}>
                      <defs>
                        <linearGradient id="latencyStore" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#22d3ee" stopOpacity={0.02} />
                        </linearGradient>
                        <linearGradient id="latencyRetrieve" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#34d399" stopOpacity={0.35} />
                          <stop offset="95%" stopColor="#34d399" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />
                      <XAxis dataKey="timestamp" tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={{ background: "#07111d", border: "1px solid rgba(148,163,184,0.2)", borderRadius: 12 }} />
                      <Legend />
                      <Area type="monotone" dataKey="store" name="Store p50 ms" stroke="#22d3ee" fill="url(#latencyStore)" strokeWidth={2} />
                      <Area type="monotone" dataKey="retrieve" name="Retrieve p50 ms" stroke="#34d399" fill="url(#latencyRetrieve)" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-slate-700/70 px-4 py-12 text-center text-sm text-slate-500">
                  No benchmark series is available yet.
                </div>
              )}
            </div>
          </SectionShell>
        </div>

        <div className="xl:col-span-2">
          <SectionShell title="Latency Snapshot" subtitle="Recent ingest/query telemetry exposed by the benchmark history">
            <div className="p-5">
              {series.length ? (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={latencyData} margin={{ top: 10, right: 16, left: 0, bottom: 10 }}>
                      <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />
                      <XAxis dataKey="timestamp" tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={{ background: "#07111d", border: "1px solid rgba(148,163,184,0.2)", borderRadius: 12 }} />
                      <Line type="monotone" dataKey="p95" name="Retrieve p95 ms" stroke="#f59e0b" strokeWidth={2.5} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-slate-700/70 px-4 py-12 text-center text-sm text-slate-500">
                  Waiting for benchmark history.
                </div>
              )}
            </div>
          </SectionShell>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 rounded-2xl border px-5 py-4" style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-1)" }}>
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-slate-400">Evidence-Ready</p>
          <p className="mt-1 text-sm text-slate-500">The benchmark suite is backed by live graph hashes, diagnostics, ingest latency, query fidelity, and tenant-scoped evidence.</p>
        </div>
        <Button variant="ghost" size="sm" className="uppercase tracking-[0.2em] text-[10px]" rightIcon={<ArrowUpRight size={14} />} onClick={() => void refresh()} disabled={!graphId}>
          Refresh
        </Button>
      </div>
    </div>
  );
}
