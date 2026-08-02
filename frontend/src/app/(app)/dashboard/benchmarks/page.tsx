"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  Activity,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useUser } from "@/contexts/UserContext";
import { resolveGraphId } from "@/lib/api-client";
import {
  fetchLatestBenchmark,
  runBenchmarkSuite,
  fetchGoldenSignals,
  fetchAlerts,
  runStressTest,
  exportBenchmarkReport,
  fetchPublicationLatest,
  fetchPublicationStatus,
  startPublicationSuite,
  runPublicationSuite,
} from "@/lib/benchmarks";
import type {
  BenchmarkSuiteRun,
  GoldenSignal,
  BenchmarkAlert,
  StressTestResult,
  BenchmarkReport,
  PublicationRun,
  PublicationJobStatus,
} from "@/types/benchmarks";

type Tab =
  | "overview"
  | "golden-signals"
  | "stress"
  | "alerts"
  | "export"
  | "track-b"
  | "track-c"
  | "track-a"
  | "track-d"
  | "publication"
  | "publication-system"
  | "publication-global"
  | "global-track-a"
  | "global-track-b"
  | "global-track-c"
  | "global-track-d"
  | "global-track-e"
  | "global-track-f";
type BenchmarkView = "system" | "global";

const SYSTEM_TABS = [
  "overview",
  "golden-signals",
  "stress",
  "alerts",
  "export",
] as const;
const GLOBAL_TABS = [
  "global-track-a",
  "global-track-b",
  "global-track-c",
  "global-track-d",
  "global-track-e",
  "global-track-f",
] as const;

const BM_DESCRIPTIONS: Record<string, string> = {
  "BM-1":
    "Computes graph hash twice from live DB rows. Checks both outputs are identical — proves the hash function is deterministic.",
  "BM-2":
    "Compares current graph hash against the hash stored in the last DIAGNOSTICS_SNAPSHOT event. Detects silent data drift.",
  "BM-3":
    "Runs check_all_invariants() against real node/edge rows: inheritance rules, weight bounds, event consistency.",
  "BM-4":
    "Reads process environment — confirms no OpenAI/Anthropic/Google API keys are set. Core engine must work without cloud LLMs.",
  "BM-5":
    "Counts touch_count on every node in DB. High value = same content re-ingested many times and correctly collapsed into existing nodes.",
  "BM-6":
    "Reads SelfEvolutionStateRepo and SelfInventionStateRepo from DB. Measures lambda_hat pressure and recent merge/prune/invention counts.",
  "BM-7":
    "Reads the latest INGEST_PHASE_LATENCY event stored in DB by the real ingest pipeline. Score = actual latency vs STRICT budget target.",
  "BM-8":
    "Executes run_query() twice with identical input. If both results hash identically, query is deterministic.",
  "BM-9":
    "Scans all nodes, edges, and events in DB. Every row must have tenant_id matching the current session.",
};

function EvidenceRow({ label, value }: { label: string; value: unknown }) {
  const display =
    typeof value === "boolean"
      ? value
        ? "✓ true"
        : "✗ false"
      : typeof value === "object"
        ? JSON.stringify(value, null, 2)
        : String(value ?? "—");
  return (
    <div className="flex gap-3 text-[11px]">
      <span className="text-slate-500 min-w-[160px] shrink-0">{label}</span>
      <span
        className={`font-mono break-all ${typeof value === "boolean" ? (value ? "text-green-400" : "text-red-400") : "text-slate-300"}`}
      >
        {display.length > 120 ? display.slice(0, 120) + "…" : display}
      </span>
    </div>
  );
}

function BenchmarkResultsList({
  benchmarks,
}: {
  benchmarks: import("@/types/benchmarks").BenchmarkItem[];
}) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-6">
      <h3 className="text-sm font-bold text-white mb-1">Benchmark Results</h3>
      <p className="text-[10px] text-slate-500 mb-4">
        Click any row to see the raw evidence data pulled from your live
        database.
      </p>
      <div className="space-y-2">
        {benchmarks.map((bm) => {
          const isOpen = expanded === bm.benchmark_id;
          return (
            <div
              key={bm.benchmark_id}
              className="rounded-lg border border-slate-700/50 overflow-hidden"
            >
              <button
                onClick={() => setExpanded(isOpen ? null : bm.benchmark_id)}
                className="w-full flex items-center justify-between p-3 bg-slate-800/30 hover:bg-slate-800/60 transition-colors text-left"
              >
                <div className="flex items-center gap-2">
                  {isOpen ? (
                    <ChevronDown className="h-4 w-4 text-slate-500" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-slate-500" />
                  )}
                  <div>
                    <p className="font-medium text-slate-200">
                      {bm.benchmark_id} — {bm.name}
                    </p>
                    <p className="text-[10px] text-slate-500">
                      {BM_DESCRIPTIONS[bm.benchmark_id] ?? bm.status}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-4">
                  <span
                    className={`text-lg font-bold ${bm.passed ? "text-green-400" : "text-amber-400"}`}
                  >
                    {bm.score.toFixed(1)}
                    <span className="text-[10px] text-slate-500 ml-0.5">
                      /100
                    </span>
                  </span>
                  {bm.passed ? (
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                  ) : (
                    <AlertCircle className="h-5 w-5 text-amber-500" />
                  )}
                </div>
              </button>
              {isOpen && (
                <div className="px-4 py-3 bg-slate-900/50 border-t border-slate-700/50 space-y-2">
                  <p className="text-[10px] font-bold text-slate-400 uppercase mb-2">
                    Evidence from live database
                  </p>
                  {Object.entries(bm.evidence || {}).map(([k, v]) => (
                    <EvidenceRow key={k} label={k} value={v} />
                  ))}
                  {bm.notes?.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-slate-700/40">
                      {bm.notes.map((note, i) => (
                        <p
                          key={i}
                          className="text-[10px] text-slate-500 italic"
                        >
                          {note}
                        </p>
                      ))}
                    </div>
                  )}
                  <div className="mt-2 pt-2 border-t border-slate-700/40">
                    <EvidenceRow
                      label="evidence_hash (SHA-256)"
                      value={bm.evidence_hash}
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function BenchmarksPage() {
  const { graphId: contextGraphId } = useUser();
  const graphId = resolveGraphId(contextGraphId ?? undefined);

  const [benchmark, setBenchmark] = useState<BenchmarkSuiteRun | null>(null);
  const [signals, setSignals] = useState<GoldenSignal | null>(null);
  const [alerts, setAlerts] = useState<BenchmarkAlert[]>([]);
  const [stressResults, setStressResults] = useState<StressTestResult[] | null>(
    null,
  );
  const [report, setReport] = useState<BenchmarkReport | null>(null);
  const [publication, setPublication] = useState<PublicationRun | null>(null);
  const [publicationJob, setPublicationJob] =
    useState<PublicationJobStatus | null>(null);

  const [loading, setLoading] = useState(false);
  const [benchmarkView, setBenchmarkView] = useState<BenchmarkView>("system");
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  // FAIM-Bench benchmark state
  const [trackBResult, setTrackBResult] = useState<any>(null);
  const [trackCResult, setTrackCResult] = useState<any>(null);
  const [trackAJob, setTrackAJob] = useState<any>(null);
  const [trackDResult, setTrackDResult] = useState<any>(null);
  const [trackLoading, setTrackLoading] = useState<string | null>(null);

  useEffect(() => {
    if (!graphId) return;
    const loadData = async () => {
      const [bm, sig, al] = await Promise.all([
        fetchLatestBenchmark(graphId),
        fetchGoldenSignals(graphId),
        fetchAlerts(graphId),
      ]);
      const pub = await fetchPublicationLatest(graphId);
      if (bm) setBenchmark(bm);
      if (sig) setSignals(sig);
      if (al?.alerts) setAlerts(al.alerts);
      if (pub) setPublication(pub);
    };
    loadData();
  }, [graphId]);

  const handleRunBenchmark = useCallback(async () => {
    if (!graphId) return;
    setLoading(true);
    try {
      const result = await runBenchmarkSuite(graphId);
      if (result) setBenchmark(result);
      const [sig, al] = await Promise.all([
        fetchGoldenSignals(graphId),
        fetchAlerts(graphId),
      ]);
      if (sig) setSignals(sig);
      if (al?.alerts) setAlerts(al.alerts);
    } finally {
      setLoading(false);
    }
  }, [graphId]);

  const handleRunStressTest = useCallback(async () => {
    if (!graphId) return;
    setLoading(true);
    try {
      const result = await runStressTest(graphId);
      if (result?.results) setStressResults(result.results);
    } finally {
      setLoading(false);
    }
  }, [graphId]);

  const handleExport = useCallback(async () => {
    if (!graphId) return;
    setLoading(true);
    try {
      const result = await exportBenchmarkReport(graphId);
      if (result) {
        setReport(result);
        const json = JSON.stringify(result, null, 2);
        const blob = new Blob([json], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `benchmark-${graphId}-${new Date().toISOString().split("T")[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } finally {
      setLoading(false);
    }
  }, [graphId]);

  const runTrackB = useCallback(async () => {
    if (!graphId) return;
    setTrackLoading("B");
    try {
      const res = await fetch(
        `/api/v1/faim-bench/${encodeURIComponent(graphId)}/track-b`,
        { method: "POST" },
      );
      if (res.ok) setTrackBResult(await res.json());
    } finally {
      setTrackLoading(null);
    }
  }, [graphId]);

  const runTrackC = useCallback(async () => {
    if (!graphId) return;
    setTrackLoading("C");
    try {
      const res = await fetch(
        `/api/v1/faim-bench/${encodeURIComponent(graphId)}/track-c`,
        { method: "POST" },
      );
      if (res.ok) setTrackCResult(await res.json());
    } finally {
      setTrackLoading(null);
    }
  }, [graphId]);

  const runTrackD = useCallback(async () => {
    if (!graphId) return;
    setTrackLoading("D");
    try {
      const res = await fetch(
        `/api/v1/faim-bench/${encodeURIComponent(graphId)}/track-d`,
        { method: "POST" },
      );
      if (res.ok) setTrackDResult(await res.json());
    } finally {
      setTrackLoading(null);
    }
  }, [graphId]);

  const startTrackA = useCallback(async () => {
    if (!graphId) return;
    setTrackLoading("A");
    try {
      const res = await fetch(
        `/api/v1/faim-bench/${encodeURIComponent(graphId)}/track-a/start`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            dataset_names: ["scifact", "nq", "hotpotqa", "fever", "msmarco"],
          }),
        },
      );
      if (res.ok) setTrackAJob(await res.json());
    } finally {
      setTrackLoading(null);
    }
  }, [graphId]);

  const runPublication = useCallback(async () => {
    if (!graphId) return;
    setTrackLoading("publication");
    try {
      const started = await startPublicationSuite(graphId);
      if (started) {
        setPublicationJob(started);
        return;
      }

      const res = await runPublicationSuite(graphId);
      if (res) {
        setPublication(res);
        setPublicationJob({
          run_id: res.run_id,
          graph_id: res.graph_id,
          status: "completed",
          progress_message: "Publication suite completed",
          total_duration_sec: res.total_duration_sec,
          result: res,
        });
      }
    } finally {
      setTrackLoading(null);
    }
  }, [graphId]);

  useEffect(() => {
    if (!graphId || !publicationJob || publicationJob.status !== "running")
      return;

    const iv = setInterval(async () => {
      const updated = await fetchPublicationStatus(
        graphId,
        publicationJob.run_id,
      );
      if (!updated) return;
      setPublicationJob(updated);
      if (updated.status === "completed" && updated.result) {
        setPublication(updated.result);
      }
      if (updated.status !== "running") clearInterval(iv);
    }, 2000);

    return () => clearInterval(iv);
  }, [graphId, publicationJob]);

  const openSystemView = useCallback(() => {
    setBenchmarkView("system");
    setActiveTab((prev) =>
      (SYSTEM_TABS as readonly string[]).includes(prev) ? prev : "overview",
    );
  }, []);

  const openGlobalView = useCallback(() => {
    setBenchmarkView("global");
    setActiveTab((prev) =>
      (GLOBAL_TABS as readonly string[]).includes(prev)
        ? prev
        : "global-track-a",
    );
  }, []);

  // Poll BEIR retrieval benchmark while running
  useEffect(() => {
    if (!trackAJob || trackAJob.status !== "running" || !graphId) return;
    const iv = setInterval(async () => {
      const res = await fetch(
        `/api/v1/faim-bench/${encodeURIComponent(graphId)}/track-a/status/${trackAJob.run_id}`,
      );
      if (res.ok) {
        const updated = await res.json();
        setTrackAJob(updated);
        if (updated.status !== "running") clearInterval(iv);
      }
    }, 3000);
    return () => clearInterval(iv);
  }, [trackAJob, graphId]);

  const criticalAlerts = alerts.filter((a) => a.severity === "critical");

  return (
    <div className="space-y-6">
      {criticalAlerts.length > 0 && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4">
          <div className="flex items-center gap-3 text-red-400">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <div>
              <p className="font-semibold">
                {criticalAlerts.length} Critical Alert(s)
              </p>
              <p className="text-sm text-red-300/80">
                {criticalAlerts[0]?.message}
              </p>
            </div>
          </div>
        </div>
      )}

      <GlassHeader
        icon={Activity}
        title="Engine Benchmarks"
        subtitle="Claimable benchmark results only: real BEIR retrieval, live telemetry, and live system property checks"
        actions={
          <div className="flex gap-2">
            <Button onClick={handleRunBenchmark} disabled={loading} size="sm">
              {loading ? "Running..." : "Run Benchmark"}
            </Button>
            <Button
              onClick={handleRunStressTest}
              disabled={loading}
              variant="secondary"
              size="sm"
            >
              Stress Test
            </Button>
            <Button
              onClick={handleExport}
              disabled={loading || !benchmark}
              variant="secondary"
              size="sm"
            >
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        }
      />

      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-[12px] text-slate-300">
        <p className="font-semibold text-amber-300 mb-1">Public claim rule</p>
        <p>
          Only BEIR Retrieval, Efficiency Telemetry, and BM-1 through BM-9
          should be cited publicly as benchmark results. Persistent Memory,
          Continuity, Workflow, and Real-World Task suites are internal
          validation scenarios and must not be presented as public performance
          claims.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={openSystemView}
          className="rounded-full border px-3 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] transition-all duration-200"
          style={
            benchmarkView === "system"
              ? {
                  borderColor: "rgba(6,182,212,0.4)",
                  backgroundColor: "rgba(6,182,212,0.12)",
                  color: "#06b6d4",
                }
              : {
                  borderColor: "rgba(255,255,255,0.1)",
                  backgroundColor: "rgba(255,255,255,0.03)",
                  color: "rgba(148,163,184,0.75)",
                }
          }
        >
          Claimable Benchmarks
        </button>
        <button
          type="button"
          onClick={openGlobalView}
          className="rounded-full border px-3 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] transition-all duration-200"
          style={
            benchmarkView === "global"
              ? {
                  borderColor: "rgba(139,92,246,0.4)",
                  backgroundColor: "rgba(139,92,246,0.12)",
                  color: "#8b5cf6",
                }
              : {
                  borderColor: "rgba(255,255,255,0.1)",
                  backgroundColor: "rgba(255,255,255,0.03)",
                  color: "rgba(148,163,184,0.75)",
                }
          }
        >
          Internal Validation
        </button>
      </div>

      {benchmarkView === "system" && !benchmark && !loading && (
        <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-8 text-center">
          <div className="max-w-md mx-auto">
            <div className="w-12 h-12 rounded-full bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mx-auto mb-4">
              <Activity className="h-6 w-6 text-cyan-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">
              No Benchmarks Run Yet
            </h3>
            <p className="text-slate-400 text-sm mb-6">
              Click &quot;Run Benchmark&quot; to execute the BM-1–BM-9 test
              suite and measure your graph&apos;s performance across ingest
              speed, retrieval latency, graph evolution, and stability.
            </p>
            <div className="space-y-3 text-sm text-slate-400">
              <div className="flex gap-3 items-start">
                <span className="text-cyan-400 font-semibold">1.</span>
                <span>
                  Click &quot;Run Benchmark&quot; — measures baseline
                  performance (ingest, retrieval, evolution, scoring)
                </span>
              </div>
              <div className="flex gap-3 items-start">
                <span className="text-cyan-400 font-semibold">2.</span>
                <span>
                  Click &quot;Stress Test&quot; — progressive load testing to
                  find your saturation point
                </span>
              </div>
              <div className="flex gap-3 items-start">
                <span className="text-cyan-400 font-semibold">3.</span>
                <span>
                  View Golden Signals — real-time CPU, memory, latency, error
                  rates from your system
                </span>
              </div>
              <div className="flex gap-3 items-start">
                <span className="text-cyan-400 font-semibold">4.</span>
                <span>
                  Check Alerts — 9 rule-based anomaly conditions (latency
                  spikes, memory pressure, invariants)
                </span>
              </div>
              <div className="flex gap-3 items-start">
                <span className="text-cyan-400 font-semibold">5.</span>
                <span>
                  Export Report — download complete snapshot with SHA-256
                  integrity hash
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {benchmarkView === "system" &&
        (signals ? (
          <div className="grid grid-cols-4 gap-4">
            <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                Latency
              </p>
              <p className="text-2xl font-bold text-cyan-400">
                {signals.latency.p95_ms
                  ? `${signals.latency.p95_ms.toFixed(0)}ms`
                  : "—"}
              </p>
              <p className="text-[10px] text-slate-500 mt-1">p95 latency</p>
            </div>

            <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                Traffic
              </p>
              <p className="text-2xl font-bold text-purple-400">
                {signals.traffic.requests_per_sec
                  ? `${signals.traffic.requests_per_sec.toFixed(1)}/s`
                  : "—"}
              </p>
              <p className="text-[10px] text-slate-500 mt-1">requests/sec</p>
            </div>

            <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                Errors
              </p>
              <p className="text-2xl font-bold text-amber-400">
                {signals.errors.error_rate
                  ? `${(signals.errors.error_rate * 100).toFixed(1)}%`
                  : "0%"}
              </p>
              <p className="text-[10px] text-slate-500 mt-1">error rate</p>
            </div>

            <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                Saturation
              </p>
              <p className="text-2xl font-bold text-orange-400">
                {signals.saturation.memory_percent
                  ? `${signals.saturation.memory_percent.toFixed(0)}%`
                  : "—"}
              </p>
              <p className="text-[10px] text-slate-500 mt-1">memory usage</p>
            </div>
          </div>
        ) : benchmark ? (
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: "Latency", color: "text-cyan-400" },
              { label: "Traffic", color: "text-purple-400" },
              { label: "Errors", color: "text-amber-400" },
              { label: "Saturation", color: "text-orange-400" },
            ].map((item) => (
              <div
                key={item.label}
                className="rounded-xl border border-slate-700 bg-slate-900/30 p-4"
              >
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                  {item.label}
                </p>
                <p className={`text-2xl font-bold ${item.color}`}>—</p>
                <p className="text-[10px] text-slate-500 mt-1">
                  run benchmark to load
                </p>
              </div>
            ))}
          </div>
        ) : null)}

      {benchmarkView === "system" && (
        <div className="flex gap-1 border-b border-slate-800 overflow-x-auto">
          {(SYSTEM_TABS as readonly Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-2 text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === tab
                  ? "border-b-2 border-cyan-500 text-cyan-400"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {tab === "overview" && "Overview"}
              {tab === "golden-signals" && "Golden Signals"}
              {tab === "stress" && "Stress Test"}
              {tab === "alerts" && `Alerts (${alerts.length})`}
              {tab === "export" && "Report"}
              {tab === "track-b" && (
                <span className="flex items-center gap-1">
                  Persistent Memory{" "}
                  <span className="text-[9px] px-1 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                    INTERNAL
                  </span>
                </span>
              )}
              {tab === "track-c" && (
                <span className="flex items-center gap-1">
                  Continuity Regression{" "}
                  <span className="text-[9px] px-1 py-0.5 rounded bg-purple-500/20 text-purple-400 border border-purple-500/30">
                    INTERNAL
                  </span>
                </span>
              )}
              {tab === "track-a" && (
                <span className="flex items-center gap-1">
                  BEIR Retrieval{" "}
                  <span className="text-[9px] px-1 py-0.5 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                    CLAIMABLE
                  </span>
                </span>
              )}
              {tab === "track-d" && (
                <span className="flex items-center gap-1">
                  Efficiency Telemetry{" "}
                  <span className="text-[9px] px-1 py-0.5 rounded bg-orange-500/20 text-orange-400 border border-orange-500/30">
                    CLAIMABLE
                  </span>
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {activeTab === "overview" && benchmark && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase">
                Score
              </p>
              <p className="text-3xl font-bold text-green-400 mt-2">
                {benchmark.overall_score.toFixed(0)}
              </p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase">
                Nodes
              </p>
              <p className="text-3xl font-bold text-blue-400 mt-2">
                {benchmark.node_count}
              </p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase">
                Edges
              </p>
              <p className="text-3xl font-bold text-purple-400 mt-2">
                {benchmark.edge_count}
              </p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase">
                Duration
              </p>
              <p className="text-3xl font-bold text-amber-400 mt-2">
                {(benchmark.duration_ms / 1000).toFixed(1)}s
              </p>
            </div>
          </div>

          <BenchmarkResultsList benchmarks={benchmark.benchmarks} />
        </div>
      )}

      {activeTab === "golden-signals" && signals && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(signals.saturation).map(([key, value]) => (
              <div
                key={key}
                className="rounded-xl border border-slate-700 bg-slate-900/30 p-4"
              >
                <p className="text-[10px] font-bold text-slate-500 uppercase mb-2">
                  {key.replace(/_/g, " ")}
                </p>
                <div className="w-full bg-slate-800 rounded-full h-2 mt-3">
                  <div
                    className="bg-gradient-to-r from-green-500 to-red-500 h-2 rounded-full"
                    style={{ width: `${Math.min(100, value || 0)}%` }}
                  />
                </div>
                <p className="text-lg font-bold text-slate-300 mt-2">
                  {(value || 0).toFixed(1)}%
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === "stress" && stressResults && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-6">
            <h3 className="text-sm font-bold text-white mb-4">
              Load Test Results
            </h3>
            <div className="space-y-3">
              {stressResults.map((result) => (
                <div
                  key={result.concurrency}
                  className="p-4 bg-slate-800/30 rounded-lg"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-slate-300">
                      Concurrency {result.concurrency}
                    </span>
                    <span className="text-sm text-slate-500">
                      {result.throughput_docs_per_sec.toFixed(1)} docs/sec
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-[10px]">
                    <div>
                      <p className="text-slate-500">p50</p>
                      <p className="text-cyan-400 font-mono">
                        {result.ingest_latency_p50_ms.toFixed(1)}ms
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-500">p95</p>
                      <p className="text-amber-400 font-mono">
                        {result.ingest_latency_p95_ms.toFixed(1)}ms
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-500">p99</p>
                      <p className="text-red-400 font-mono">
                        {result.ingest_latency_p99_ms.toFixed(1)}ms
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === "alerts" && (
        <div className="space-y-4">
          {alerts.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle2 className="h-12 w-12 text-green-500 mx-auto mb-2" />
              <p className="text-slate-400">No alerts detected</p>
            </div>
          ) : (
            <div className="space-y-2">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`p-4 rounded-lg border ${
                    alert.severity === "critical"
                      ? "border-red-500/30 bg-red-500/10"
                      : alert.severity === "warning"
                        ? "border-amber-500/30 bg-amber-500/10"
                        : "border-blue-500/30 bg-blue-500/10"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p
                        className={`font-semibold ${
                          alert.severity === "critical"
                            ? "text-red-400"
                            : alert.severity === "warning"
                              ? "text-amber-400"
                              : "text-blue-400"
                        }`}
                      >
                        {alert.title}
                      </p>
                      <p className="text-[11px] text-slate-400 mt-1">
                        {alert.message}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "export" && report && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-6">
            <h3 className="text-sm font-bold text-white mb-4">Export Report</h3>
            <div className="space-y-2 text-[11px] font-mono text-slate-400">
              <div>
                <span className="text-slate-500">Report Hash:</span>{" "}
                {report.report_hash}
              </div>
              <div>
                <span className="text-slate-500">Exported:</span>{" "}
                {report.export_timestamp}
              </div>
              <div>
                <span className="text-slate-500">Graph:</span> {report.graph_id}
              </div>
            </div>
            <Button onClick={handleExport} className="mt-4" disabled={loading}>
              <Download className="h-4 w-4 mr-2" />
              Download JSON Report
            </Button>
          </div>
        </div>
      )}

      {/* ── Persistent Memory Validation ─────────────────────────── */}
      {activeTab === "track-b" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-5">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-bold text-white mb-1">
                  Persistent Memory Validation
                </h3>
                <p className="text-[12px] text-slate-400">
                  Synthetic scenario test. Useful for regression checks, but not
                  a public performance claim. Measures Recall@k, nDCG, update
                  accuracy, deletion completeness, hallucination rate, citation
                  accuracy, and answer consistency.
                </p>
              </div>
              <Button
                onClick={runTrackB}
                disabled={trackLoading === "B"}
                size="sm"
              >
                {trackLoading === "B" ? "Running…" : "Run Memory Validation"}
              </Button>
            </div>
            {trackBResult && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    {
                      label: "Retention Recall@5",
                      value: trackBResult.retention?.["recall@5"],
                    },
                    {
                      label: "Retention nDCG@10",
                      value: trackBResult.retention?.["ndcg@10"],
                    },
                    { label: "MRR", value: trackBResult.retention?.["mrr"] },
                    {
                      label: "Update Accuracy",
                      value: trackBResult.update_accuracy,
                    },
                    {
                      label: "Deletion Complete",
                      value: trackBResult.deletion_completeness,
                    },
                    {
                      label: "Hallucination Rate↓",
                      value: trackBResult.hallucination_rate,
                    },
                    {
                      label: "Answer Consistency",
                      value: trackBResult.answer_consistency,
                    },
                    {
                      label: "Citation Accuracy",
                      value: trackBResult.citation_accuracy,
                    },
                  ].map(({ label, value }) => (
                    <div
                      key={label}
                      className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-3"
                    >
                      <p className="text-[9px] text-slate-500 uppercase tracking-wider mb-1">
                        {label}
                      </p>
                      <p
                        className={`text-xl font-bold font-mono ${value !== undefined ? "text-cyan-300" : "text-slate-600"}`}
                      >
                        {value !== undefined ? Number(value).toFixed(3) : "—"}
                      </p>
                    </div>
                  ))}
                </div>
                <p className="text-[10px] text-slate-600">
                  Run in {trackBResult.duration_sec?.toFixed(1)}s · synthetic
                  validation only
                </p>
              </div>
            )}
            {!trackBResult && trackLoading !== "B" && (
              <p className="text-[12px] text-slate-500 mt-2">
                Click Run Memory Validation to measure retrieval quality on the
                internal memory scenario suite.
              </p>
            )}
          </div>
        </div>
      )}

      {/* ── Continuity Validation ────────────────────────────────── */}
      {activeTab === "track-c" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-5">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-bold text-white mb-1">
                  Continuity Validation
                </h3>
                <p className="text-[12px] text-slate-400">
                  Synthetic scenario test. Useful for continuity regressions,
                  but not a public performance claim. Measures per-session
                  retention, cross-session multi-hop recall, update accuracy,
                  stale suppression, long-horizon recall, and hallucination
                  rate.
                </p>
              </div>
              <Button
                onClick={runTrackC}
                disabled={trackLoading === "C"}
                size="sm"
              >
                {trackLoading === "C"
                  ? "Running…"
                  : "Run Continuity Validation"}
              </Button>
            </div>
            {trackCResult && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    {
                      label: "Continuity Score",
                      value: trackCResult.continuity_score,
                      color: "text-emerald-300",
                    },
                    {
                      label: "Long-Horizon Recall",
                      value: trackCResult.long_horizon_recall,
                      color: "text-cyan-300",
                    },
                    {
                      label: "Cross-Session Recall",
                      value: trackCResult.cross_session_recall,
                      color: "text-cyan-300",
                    },
                    {
                      label: "Update Accuracy",
                      value: trackCResult.update_accuracy,
                      color: "text-cyan-300",
                    },
                    {
                      label: "Stale Suppression",
                      value: trackCResult.stale_suppression,
                      color: "text-cyan-300",
                    },
                    {
                      label: "Multi-Hop Accuracy",
                      value: trackCResult.multihop_accuracy,
                      color: "text-cyan-300",
                    },
                    {
                      label: "Hallucination Rate ↓",
                      value: trackCResult.hallucination_rate,
                      color: "text-amber-300",
                    },
                  ].map(({ label, value, color }) => (
                    <div
                      key={label}
                      className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-3"
                    >
                      <p className="text-[9px] text-slate-500 uppercase tracking-wider mb-1">
                        {label}
                      </p>
                      <p className={`text-xl font-bold font-mono ${color}`}>
                        {Number(value).toFixed(3)}
                      </p>
                    </div>
                  ))}
                </div>
                <div className="rounded-lg border border-slate-700/50 bg-slate-800/20 overflow-hidden">
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-4 pt-3 pb-2">
                    Per-Session Retention
                  </p>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-700/50">
                        <th className="text-left py-2 px-4 text-[10px] text-slate-500">
                          Session
                        </th>
                        <th className="text-left py-2 px-3 text-[10px] text-slate-500">
                          Label
                        </th>
                        <th className="text-center py-2 px-3 text-[10px] text-cyan-500">
                          Recall@5
                        </th>
                        <th className="text-center py-2 px-3 text-[10px] text-cyan-500">
                          nDCG@10
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {trackCResult.session_retention?.map((s: any) => (
                        <tr
                          key={s.session_id}
                          className="border-b border-slate-800/30"
                        >
                          <td className="py-2 px-4 font-mono text-slate-400 text-[11px]">
                            S{s.session_id}
                          </td>
                          <td className="py-2 px-3 text-slate-300 text-[11px]">
                            {s.label}
                          </td>
                          <td className="py-2 px-3 text-center font-mono text-cyan-300 font-bold text-[12px]">
                            {Number(s["recall@5"]).toFixed(3)}
                          </td>
                          <td className="py-2 px-3 text-center font-mono text-cyan-300 font-bold text-[12px]">
                            {Number(s["ndcg@10"]).toFixed(3)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="text-[10px] text-slate-600">
                  Run in {trackCResult.duration_sec?.toFixed(1)}s · synthetic
                  validation only
                </p>
              </div>
            )}
            {!trackCResult && trackLoading !== "C" && (
              <p className="text-[12px] text-slate-500 mt-2">
                Click Run Continuity Validation to measure long-horizon memory
                continuity on the internal scenario suite.
              </p>
            )}
          </div>
        </div>
      )}

      {/* ── Efficiency Telemetry ────────────────────────────────── */}
      {activeTab === "track-d" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-5">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-bold text-white mb-1">
                  Efficiency Telemetry
                </h3>
                <p className="text-[12px] text-slate-400">
                  Real telemetry only: ingest p50/p95/p99 from event log,
                  retrieval latency from LatencyCollector, storage size from
                  Postgres, compression ratio from graph state.
                </p>
              </div>
              <Button
                onClick={runTrackD}
                disabled={trackLoading === "D"}
                size="sm"
              >
                {trackLoading === "D"
                  ? "Measuring…"
                  : "Run Efficiency Telemetry"}
              </Button>
            </div>
            {trackDResult && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {[
                    {
                      label: "Ingest p50 (ms) ↓",
                      value: trackDResult.ingest_latency_ms?.p50,
                      color: "text-orange-300",
                    },
                    {
                      label: "Ingest p95 (ms) ↓",
                      value: trackDResult.ingest_latency_ms?.p95,
                      color: "text-orange-300",
                    },
                    {
                      label: "Ingest p99 (ms) ↓",
                      value: trackDResult.ingest_latency_ms?.p99,
                      color: "text-orange-300",
                    },
                    {
                      label: "Retrieval p50 (ms) ↓",
                      value: trackDResult.retrieval_latency_ms?.p50,
                      color: "text-cyan-300",
                    },
                    {
                      label: "Retrieval p95 (ms) ↓",
                      value: trackDResult.retrieval_latency_ms?.p95,
                      color: "text-cyan-300",
                    },
                    {
                      label: "Retrieval p99 (ms) ↓",
                      value: trackDResult.retrieval_latency_ms?.p99,
                      color: "text-cyan-300",
                    },
                    {
                      label: "Compression Ratio ↑",
                      value: trackDResult.storage?.compression_ratio,
                      color: "text-emerald-300",
                      decimal: 4,
                    },
                    {
                      label: "Throughput (docs/s) ↑",
                      value: trackDResult.ingest_throughput_docs_per_sec,
                      color: "text-emerald-300",
                      decimal: 2,
                    },
                    {
                      label: "Node Count",
                      value: trackDResult.storage?.node_count,
                      color: "text-slate-300",
                      isInt: true,
                    },
                  ].map(({ label, value, color, decimal, isInt }) => (
                    <div
                      key={label}
                      className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-3"
                    >
                      <p className="text-[9px] text-slate-500 uppercase tracking-wider mb-1">
                        {label}
                      </p>
                      <p
                        className={`text-xl font-bold font-mono ${value ? color : "text-slate-600"}`}
                      >
                        {value != null
                          ? isInt
                            ? Number(value).toLocaleString()
                            : Number(value).toFixed(decimal ?? 1)
                          : "—"}
                      </p>
                    </div>
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg border border-slate-700/50 bg-slate-800/20 p-3">
                    <p className="text-[9px] text-slate-500 uppercase tracking-wider mb-1">
                      Storage
                    </p>
                    <p className="text-[12px] text-slate-300">
                      {trackDResult.storage?.node_count?.toLocaleString()} nodes
                      · {trackDResult.storage?.edge_count?.toLocaleString()}{" "}
                      edges
                    </p>
                    {trackDResult.storage?.bytes_per_node_estimate > 0 && (
                      <p className="text-[11px] text-slate-500">
                        {(
                          trackDResult.storage.bytes_per_node_estimate / 1024
                        ).toFixed(1)}{" "}
                        KB/node avg
                      </p>
                    )}
                  </div>
                  <div className="rounded-lg border border-slate-700/50 bg-slate-800/20 p-3">
                    <p className="text-[9px] text-slate-500 uppercase tracking-wider mb-1">
                      Quality / Storage
                    </p>
                    <p className="text-[12px] text-slate-300 font-mono">
                      {trackDResult.quality_per_gb?.toFixed(2)}
                    </p>
                    <p className="text-[11px] text-slate-500">
                      compression ratio per GB used
                    </p>
                  </div>
                </div>
                {trackDResult.notes?.length > 0 && (
                  <div className="text-[11px] text-slate-500 space-y-0.5">
                    {trackDResult.notes.map((n: string, i: number) => (
                      <p key={i}>· {n}</p>
                    ))}
                  </div>
                )}
                <p className="text-[10px] text-slate-600">
                  Measured in {trackDResult.duration_sec?.toFixed(2)}s · live
                  telemetry · claimable publicly
                </p>
              </div>
            )}
            {!trackDResult && trackLoading !== "D" && (
              <p className="text-[12px] text-slate-500 mt-2">
                Click Run Efficiency Telemetry to read live ingest/retrieval
                latency and storage metrics from your graph.
              </p>
            )}
          </div>
        </div>
      )}

      {/* ── BEIR Retrieval Benchmark ─────────────────────────────── */}
      {activeTab === "track-a" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-5">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-bold text-white mb-1">
                  BEIR Retrieval Benchmark
                </h3>
                <p className="text-[12px] text-slate-400">
                  Downloads SciFact, NQ, HotpotQA, FEVER, and MS MARCO from
                  HuggingFace, ingests the selected corpus slice into FAIM, and
                  evaluates Recall@k, nDCG@10, MRR, MAP against ground-truth
                  qrels. Runs in background.
                </p>
              </div>
              <Button
                onClick={startTrackA}
                disabled={
                  trackLoading === "A" || trackAJob?.status === "running"
                }
                size="sm"
              >
                {trackLoading === "A" || trackAJob?.status === "running"
                  ? "Running…"
                  : "Start BEIR Retrieval"}
              </Button>
            </div>
            {trackAJob?.status === "running" && (
              <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700/50 mb-4">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                  <span className="text-[11px] font-bold text-cyan-400">
                    Running in background — polling every 3s
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 font-mono">
                  {trackAJob.progress_message}
                </p>
              </div>
            )}
            {trackAJob?.status === "completed" &&
              trackAJob.datasets?.length > 0 && (
                <div className="space-y-3">
                  <div className="rounded-lg border border-slate-700/50 overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-700/60 bg-slate-800/30">
                          <th className="text-left py-2 px-4 text-[10px] text-slate-500 uppercase">
                            Dataset
                          </th>
                          <th className="text-center py-2 px-2 text-[10px] text-slate-500 uppercase">
                            Corpus
                          </th>
                          <th className="text-center py-2 px-2 text-[10px] text-cyan-500 uppercase">
                            Recall@5
                          </th>
                          <th className="text-center py-2 px-2 text-[10px] text-cyan-500 uppercase">
                            nDCG@10
                          </th>
                          <th className="text-center py-2 px-2 text-[10px] text-cyan-500 uppercase">
                            MRR
                          </th>
                          <th className="text-center py-2 px-2 text-[10px] text-slate-500 uppercase">
                            MAP
                          </th>
                          <th className="text-center py-2 px-2 text-[10px] text-slate-500 uppercase">
                            Ingest
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {trackAJob.datasets.map((ds: any) => (
                          <tr
                            key={ds.dataset}
                            className="border-b border-slate-800/30"
                          >
                            <td className="py-3 px-4 font-bold text-slate-200">
                              {ds.dataset}
                            </td>
                            <td className="py-3 px-2 text-center text-slate-500 text-[12px]">
                              {ds.corpus_size?.toLocaleString()}
                            </td>
                            <td className="py-3 px-2 text-center font-mono font-bold text-cyan-300">
                              {ds.metrics?.["recall@5"]?.toFixed(3) ?? "—"}
                            </td>
                            <td className="py-3 px-2 text-center font-mono font-bold text-cyan-300">
                              {ds.metrics?.["ndcg@10"]?.toFixed(3) ?? "—"}
                            </td>
                            <td className="py-3 px-2 text-center font-mono font-bold text-cyan-300">
                              {ds.metrics?.["mrr"]?.toFixed(3) ?? "—"}
                            </td>
                            <td className="py-3 px-2 text-center font-mono text-slate-400 text-[12px]">
                              {ds.metrics?.["map"]?.toFixed(3) ?? "—"}
                            </td>
                            <td className="py-3 px-2 text-center text-slate-500 text-[11px]">
                              {ds.ingest_duration_sec?.toFixed(0)}s
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="text-[10px] text-slate-600">
                    Completed in {trackAJob.total_duration_sec?.toFixed(0)}s ·
                    SciFact / NQ / HotpotQA / FEVER / MS MARCO · HuggingFace
                    BeIR/
                  </p>
                </div>
              )}
            {!trackAJob && (
              <p className="text-[12px] text-slate-500 mt-2">
                Click Start BEIR Retrieval. Runs in background — estimated 5–15
                min. You can switch tabs while it runs.
              </p>
            )}
          </div>
        </div>
      )}

      {benchmarkView === "global" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-5">
            <div className="mb-4 flex items-start justify-between">
              <div className="flex-1">
                <h3 className="mb-2 font-bold text-white">Publication Suite</h3>
                <p className="text-[12px] text-slate-400">
                  Public claimable results are BEIR Retrieval, Efficiency
                  Telemetry, and BM-1..BM-9. Internal scenario suites are shown
                  separately and are not claimable.
                </p>
              </div>
              <Button
                onClick={runPublication}
                disabled={
                  trackLoading === "publication" ||
                  publicationJob?.status === "running"
                }
                size="sm"
              >
                {trackLoading === "publication" ||
                publicationJob?.status === "running"
                  ? "Running…"
                  : "Run Suite"}
              </Button>
            </div>

            {publicationJob?.status === "running" && (
              <div className="mb-4 rounded-lg border border-cyan-500/30 bg-cyan-500/10 p-3">
                <div className="mb-1 flex items-center gap-2">
                  <div className="h-2 w-2 animate-pulse rounded-full bg-cyan-400" />
                  <span className="text-[11px] font-bold text-cyan-300">
                    Publication suite running in background
                  </span>
                </div>
                <p className="font-mono text-[11px] text-cyan-100/90">
                  {publicationJob.progress_message || "Working..."}
                </p>
              </div>
            )}

            {publicationJob?.status === "failed" && (
              <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3">
                <p className="text-[11px] font-semibold text-red-300">
                  Publication suite failed
                </p>
                <p className="font-mono text-[11px] text-red-100/90">
                  {publicationJob.progress_message || "Unknown error"}
                </p>
              </div>
            )}

            {publicationJob?.status === "completed" && (
              <div className="mb-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3">
                <p className="text-[11px] font-semibold text-emerald-300">
                  Publication suite completed
                </p>
                <p className="font-mono text-[11px] text-emerald-100/90">
                  Total duration: {publicationJob.total_duration_sec.toFixed(1)}
                  s
                </p>
              </div>
            )}

            {!publication && trackLoading !== "publication" && (
              <p className="mt-2 text-[12px] text-slate-500">
                No publication run yet. Click Run Suite.
              </p>
            )}
            {/* Global Benchmark View */}
            <div className="space-y-4 animate-in fade-in duration-300">
              <div className="space-y-4 animate-in fade-in duration-300">
                {/* Track Tabs */}
                <div className="flex gap-1 overflow-x-auto pb-2">
                  {[
                    {
                      id: "global-track-a",
                      label: "BEIR Retrieval",
                      color: "cyan",
                    },
                    {
                      id: "global-track-b",
                      label: "Persistent Memory",
                      color: "emerald",
                    },
                    {
                      id: "global-track-c",
                      label: "Continuity Regression",
                      color: "blue",
                    },
                    {
                      id: "global-track-d",
                      label: "Efficiency Telemetry",
                      color: "orange",
                    },
                    {
                      id: "global-track-e",
                      label: "Workflow Regression",
                      color: "indigo",
                    },
                    {
                      id: "global-track-f",
                      label: "Real-World Task Suite",
                      color: "purple",
                    },
                  ].map(({ id, label }) => (
                    <button
                      key={id}
                      onClick={() => setActiveTab(id as Tab)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-300 whitespace-nowrap border ${
                        activeTab === id
                          ? "border-cyan-500/40 bg-cyan-500/20 text-cyan-300"
                          : "border-slate-700/50 text-slate-400 hover:border-slate-600"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                {!publication && (
                  <div className="rounded-lg border border-slate-700/50 bg-slate-800/20 p-5">
                    <p className="text-[12px] text-slate-400">
                      Run the publication suite to unlock the measured results.
                      Internal scenario suites remain visible for validation but
                      are not public claims.
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* BEIR Retrieval */}
            {publication && activeTab === "global-track-a" && (
              <div className="space-y-3 animate-in fade-in duration-300">
                <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-4">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-3">
                    BEIR Retrieval Quality
                  </p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {[
                      {
                        label: "Recall@5",
                        value: ((publication as any).faim_track_a as any)
                          ?.metrics?.["recall@5"],
                      },
                      {
                        label: "nDCG@10",
                        value: ((publication as any).faim_track_a as any)
                          ?.metrics?.["ndcg@10"],
                      },
                      {
                        label: "MRR",
                        value: ((publication as any).faim_track_a as any)
                          ?.metrics?.mrr,
                      },
                      {
                        label: "MAP",
                        value: ((publication as any).faim_track_a as any)
                          ?.metrics?.map,
                      },
                    ].map((item) => (
                      <div
                        key={item.label}
                        className="rounded border border-slate-700/50 bg-slate-900/50 p-3 text-center"
                      >
                        <p className="text-[9px] text-slate-500 uppercase mb-1">
                          {item.label}
                        </p>
                        <p className="font-mono text-[14px] font-bold text-cyan-300">
                          {item.value !== undefined
                            ? Number(item.value).toFixed(4)
                            : "—"}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Persistent Memory */}
            {publication && activeTab === "global-track-b" && (
              <div className="space-y-3 animate-in fade-in duration-300">
                <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-4">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-3">
                    Persistent Memory
                  </p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {[
                      {
                        label: "Recall@5",
                        value: ((publication as any).faim_track_b as any)
                          ?.metrics?.["recall@5"],
                      },
                      {
                        label: "nDCG@10",
                        value: ((publication as any).faim_track_b as any)
                          ?.metrics?.["ndcg@10"],
                      },
                      {
                        label: "MRR",
                        value: ((publication as any).faim_track_b as any)
                          ?.metrics?.mrr,
                      },
                      {
                        label: "Citation Accuracy",
                        value: ((publication as any).faim_track_b as any)
                          ?.metrics?.citation_accuracy,
                      },
                    ].map((item) => (
                      <div
                        key={item.label}
                        className="rounded border border-slate-700/50 bg-slate-900/50 p-3 text-center"
                      >
                        <p className="text-[9px] text-slate-500 uppercase mb-1">
                          {item.label}
                        </p>
                        <p className="font-mono text-[14px] font-bold text-emerald-300">
                          {item.value !== undefined
                            ? Number(item.value).toFixed(4)
                            : "—"}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Continuity */}
            {publication && activeTab === "global-track-c" && (
              <div className="space-y-3 animate-in fade-in duration-300">
                <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-4">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-3">
                    Long-Horizon Continuity
                  </p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {[
                      {
                        label: "Continuity Score",
                        value: ((publication as any).faim_track_c as any)
                          ?.metrics?.continuity_score,
                      },
                      {
                        label: "Long-Horizon Recall",
                        value: ((publication as any).faim_track_c as any)
                          ?.metrics?.long_horizon_recall,
                      },
                      {
                        label: "Cross-Session Recall",
                        value: ((publication as any).faim_track_c as any)
                          ?.metrics?.cross_session_recall,
                      },
                      {
                        label: "Stale Suppression",
                        value: ((publication as any).faim_track_c as any)
                          ?.metrics?.stale_suppression,
                      },
                    ].map((item) => (
                      <div
                        key={item.label}
                        className="rounded border border-slate-700/50 bg-slate-900/50 p-3 text-center"
                      >
                        <p className="text-[9px] text-slate-500 uppercase mb-1">
                          {item.label}
                        </p>
                        <p className="font-mono text-[14px] font-bold text-blue-300">
                          {item.value !== undefined
                            ? Number(item.value).toFixed(4)
                            : "—"}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Efficiency */}
            {publication && activeTab === "global-track-d" && (
              <div className="space-y-3 animate-in fade-in duration-300">
                <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-4">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-3">
                    Efficiency
                  </p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {[
                      {
                        label: "Ingest p50 (ms)",
                        value: ((publication as any).faim_track_d as any)
                          ?.metrics?.ingest_latency_ms?.p50,
                      },
                      {
                        label: "Retrieval p50 (ms)",
                        value: ((publication as any).faim_track_d as any)
                          ?.metrics?.retrieval_latency_ms?.p50,
                      },
                      {
                        label: "Compression Ratio",
                        value: ((publication as any).faim_track_d as any)
                          ?.metrics?.compression_ratio,
                      },
                      {
                        label: "Throughput (docs/s)",
                        value: ((publication as any).faim_track_d as any)
                          ?.metrics?.throughput_docs_per_sec,
                      },
                    ].map((item) => (
                      <div
                        key={item.label}
                        className="rounded border border-slate-700/50 bg-slate-900/50 p-3 text-center"
                      >
                        <p className="text-[9px] text-slate-500 uppercase mb-1">
                          {item.label}
                        </p>
                        <p className="font-mono text-[14px] font-bold text-orange-300">
                          {item.value !== undefined
                            ? Number(item.value).toFixed(2)
                            : "—"}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Workflow */}
            {publication && activeTab === "global-track-e" && (
              <div className="space-y-3 animate-in fade-in duration-300">
                <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-4">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-3">
                    Agent & API Workflow
                  </p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {[
                      {
                        label: "API Key Memory",
                        value: (publication.track_e as any)?.metrics
                          ?.api_key_access_memory_accuracy,
                      },
                      {
                        label: "Task Completion",
                        value: (publication.track_e as any)?.metrics
                          ?.task_completion_rate,
                      },
                      {
                        label: "Tool-Call Recall",
                        value: (publication.track_e as any)?.metrics
                          ?.tool_call_memory_recall_accuracy,
                      },
                      {
                        label: "Multi-Agent Isolation",
                        value: (publication.track_e as any)?.metrics
                          ?.multi_agent_isolation_correctness,
                      },
                    ].map((item) => (
                      <div
                        key={item.label}
                        className="rounded border border-slate-700/50 bg-slate-900/50 p-3 text-center"
                      >
                        <p className="text-[9px] text-slate-500 uppercase mb-1">
                          {item.label}
                        </p>
                        <p className="font-mono text-[14px] font-bold text-indigo-300">
                          {item.value !== undefined
                            ? Number(item.value).toFixed(4)
                            : "—"}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Real-World Tasks */}
            {publication && activeTab === "global-track-f" && (
              <div className="space-y-3 animate-in fade-in duration-300">
                <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-4">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-3">
                    Real-World Tasks
                  </p>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {[
                      {
                        label: "Multi-Doc QA",
                        value: (publication.track_f as any)?.metrics
                          ?.multi_doc_qa_accuracy,
                      },
                      {
                        label: "Writing Continuity",
                        value: (publication.track_f as any)?.metrics
                          ?.writing_continuity_score,
                      },
                      {
                        label: "Assistant Continuity",
                        value: (publication.track_f as any)?.metrics
                          ?.personal_assistant_continuity,
                      },
                      {
                        label: "Code Context",
                        value: (publication.track_f as any)?.metrics
                          ?.code_project_context_retention,
                      },
                      {
                        label: "Citation Accuracy",
                        value: (publication.track_f as any)?.metrics
                          ?.citation_accuracy,
                      },
                      {
                        label: "Stale Suppression",
                        value: (publication.track_f as any)?.metrics
                          ?.stale_fact_suppression,
                      },
                    ].map((item) => (
                      <div
                        key={item.label}
                        className="rounded border border-slate-700/50 bg-slate-900/50 p-3 text-center"
                      >
                        <p className="text-[9px] text-slate-500 uppercase mb-1">
                          {item.label}
                        </p>
                        <p className="font-mono text-[14px] font-bold text-purple-300">
                          {item.value !== undefined
                            ? Number(item.value).toFixed(4)
                            : "—"}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
