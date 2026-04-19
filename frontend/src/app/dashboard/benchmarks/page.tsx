"use client";

import React, { useEffect, useState, useCallback } from "react";
import { AlertCircle, CheckCircle2, Download, Zap } from "lucide-react";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { resolveGraphId } from "@/lib/api-client";
import {
  fetchLatestBenchmark,
  runBenchmarkSuite,
  fetchGoldenSignals,
  fetchAlerts,
  runStressTest,
  exportBenchmarkReport,
} from "@/lib/benchmarks";
import type { BenchmarkSuiteRun, GoldenSignal, BenchmarkAlert, StressTestResult, BenchmarkReport } from "@/types/benchmarks";

type Tab = "overview" | "golden-signals" | "stress" | "alerts" | "export";

export default function BenchmarksPage() {
  const graphId = resolveGraphId();

  const [benchmark, setBenchmark] = useState<BenchmarkSuiteRun | null>(null);
  const [signals, setSignals] = useState<GoldenSignal | null>(null);
  const [alerts, setAlerts] = useState<BenchmarkAlert[]>([]);
  const [stressResults, setStressResults] = useState<StressTestResult[] | null>(null);
  const [report, setReport] = useState<BenchmarkReport | null>(null);

  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  // Load benchmarks on mount
  useEffect(() => {
    if (!graphId) return;

    const loadData = async () => {
      const [bm, sig, al] = await Promise.all([
        fetchLatestBenchmark(graphId),
        fetchGoldenSignals(graphId),
        fetchAlerts(graphId),
      ]);

      if (bm) setBenchmark(bm);
      if (sig) setSignals(sig);
      if (al?.alerts) setAlerts(al.alerts);
    };

    loadData();
  }, [graphId]);

  const handleRunBenchmark = useCallback(async () => {
    if (!graphId) return;
    setLoading(true);
    try {
      const result = await runBenchmarkSuite(graphId);
      if (result) setBenchmark(result);
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
        // Download as JSON
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

  const criticalAlerts = alerts.filter((a) => a.severity === "critical");
  const warningAlerts = alerts.filter((a) => a.severity === "warning");

  return (
    <div className="space-y-6">
      {/* Alerts Banner */}
      {criticalAlerts.length > 0 && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4">
          <div className="flex items-center gap-3 text-red-400">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <div>
              <p className="font-semibold">{criticalAlerts.length} Critical Alert(s)</p>
              <p className="text-sm text-red-300/80">{criticalAlerts[0]?.message}</p>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <GlassHeader
        title="Engine Benchmarks"
        subtitle="Live FAIM-Native Performance & System Health"
        buttons={[
          <Button key="run" onClick={handleRunBenchmark} disabled={loading}>
            {loading ? "Running..." : "Run Benchmark"}
          </Button>,
          <Button key="stress" onClick={handleRunStressTest} disabled={loading} variant="secondary">
            Stress Test
          </Button>,
          <Button key="export" onClick={handleExport} disabled={loading} variant="secondary">
            <Download className="h-4 w-4 mr-2" />
            Export Report
          </Button>,
        ]}
      />

      {/* Golden Signals Strip */}
      {signals && (
        <div className="grid grid-cols-4 gap-4">
          {/* Latency */}
          <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-4">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Latency</p>
            <p className="text-2xl font-bold text-cyan-400">
              {signals.latency.p95_ms ? `${signals.latency.p95_ms.toFixed(0)}ms` : "—"}
            </p>
            <p className="text-[10px] text-slate-500 mt-1">p95 latency</p>
          </div>

          {/* Traffic */}
          <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-4">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Traffic</p>
            <p className="text-2xl font-bold text-purple-400">
              {signals.traffic.requests_per_sec ? `${signals.traffic.requests_per_sec.toFixed(1)}/s` : "—"}
            </p>
            <p className="text-[10px] text-slate-500 mt-1">requests/sec</p>
          </div>

          {/* Errors */}
          <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-4">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Errors</p>
            <p className="text-2xl font-bold text-amber-400">
              {signals.errors.error_rate ? `${(signals.errors.error_rate * 100).toFixed(1)}%` : "0%"}
            </p>
            <p className="text-[10px] text-slate-500 mt-1">error rate</p>
          </div>

          {/* Saturation */}
          <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-4">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Saturation</p>
            <p className="text-2xl font-bold text-orange-400">
              {signals.saturation.memory_percent ? `${signals.saturation.memory_percent.toFixed(0)}%` : "—"}
            </p>
            <p className="text-[10px] text-slate-500 mt-1">memory usage</p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-800">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "overview" ? "border-b-2 border-cyan-500 text-cyan-400" : "text-slate-400"
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab("golden-signals")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "golden-signals" ? "border-b-2 border-cyan-500 text-cyan-400" : "text-slate-400"
          }`}
        >
          Golden Signals
        </button>
        <button
          onClick={() => setActiveTab("stress")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "stress" ? "border-b-2 border-cyan-500 text-cyan-400" : "text-slate-400"
          }`}
        >
          Stress Test
        </button>
        <button
          onClick={() => setActiveTab("alerts")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "alerts" ? "border-b-2 border-cyan-500 text-cyan-400" : "text-slate-400"
          }`}
        >
          Alerts ({alerts.length})
        </button>
        <button
          onClick={() => setActiveTab("export")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "export" ? "border-b-2 border-cyan-500 text-cyan-400" : "text-slate-400"
          }`}
        >
          Report
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === "overview" && benchmark && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase">Score</p>
              <p className="text-3xl font-bold text-green-400 mt-2">{benchmark.overall_score.toFixed(0)}</p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase">Nodes</p>
              <p className="text-3xl font-bold text-blue-400 mt-2">{benchmark.node_count}</p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase">Edges</p>
              <p className="text-3xl font-bold text-purple-400 mt-2">{benchmark.edge_count}</p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase">Duration</p>
              <p className="text-3xl font-bold text-amber-400 mt-2">{(benchmark.duration_ms / 1000).toFixed(1)}s</p>
            </div>
          </div>

          {/* Benchmarks Results */}
          <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-6">
            <h3 className="text-sm font-bold text-white mb-4">Benchmark Results</h3>
            <div className="space-y-2">
              {benchmark.benchmarks.map((bm) => (
                <div key={bm.benchmark_id} className="flex items-center justify-between p-3 bg-slate-800/30 rounded-lg">
                  <div>
                    <p className="font-medium text-slate-200">{bm.name}</p>
                    <p className="text-[10px] text-slate-500">{bm.status}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-bold text-slate-300">{(bm.score * 100).toFixed(0)}</span>
                    {bm.passed ? (
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                    ) : (
                      <AlertCircle className="h-5 w-5 text-red-500" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === "golden-signals" && signals && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(signals.saturation).map(([key, value]) => (
              <div key={key} className="rounded-xl border border-slate-700 bg-slate-900/30 p-4">
                <p className="text-[10px] font-bold text-slate-500 uppercase mb-2">{key}</p>
                <div className="w-full bg-slate-800 rounded-full h-2 mt-3">
                  <div className="bg-gradient-to-r from-green-500 to-red-500 h-2 rounded-full" style={{ width: `${Math.min(100, value || 0)}%` }} />
                </div>
                <p className="text-lg font-bold text-slate-300 mt-2">{(value || 0).toFixed(1)}%</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === "stress" && stressResults && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-700 bg-slate-900/30 p-6">
            <h3 className="text-sm font-bold text-white mb-4">Load Test Results</h3>
            <div className="space-y-3">
              {stressResults.map((result) => (
                <div key={result.concurrency} className="p-4 bg-slate-800/30 rounded-lg">
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
                      <p className="text-cyan-400 font-mono">{result.ingest_latency_p50_ms.toFixed(1)}ms</p>
                    </div>
                    <div>
                      <p className="text-slate-500">p95</p>
                      <p className="text-amber-400 font-mono">{result.ingest_latency_p95_ms.toFixed(1)}ms</p>
                    </div>
                    <div>
                      <p className="text-slate-500">p99</p>
                      <p className="text-red-400 font-mono">{result.ingest_latency_p99_ms.toFixed(1)}ms</p>
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
                      <p className={`font-semibold ${
                        alert.severity === "critical"
                          ? "text-red-400"
                          : alert.severity === "warning"
                            ? "text-amber-400"
                            : "text-blue-400"
                      }`}>
                        {alert.title}
                      </p>
                      <p className="text-[11px] text-slate-400 mt-1">{alert.message}</p>
                    </div>
                    <Badge variant={alert.severity}>{alert.severity}</Badge>
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
                <span className="text-slate-500">Report Hash:</span> {report.report_hash}
              </div>
              <div>
                <span className="text-slate-500">Exported:</span> {report.export_timestamp}
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
    </div>
  );
}
