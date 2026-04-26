"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";

/* ── API helpers ─────────────────────────────────────────────────────────── */

async function apiFetch<T>(
  path: string,
  opts?: RequestInit,
): Promise<T | null> {
  try {
    const res = await fetch(path, opts);
    if (!res.ok) return null;
    return res.json() as Promise<T>;
  } catch {
    return null;
  }
}

/* ── Types ──────────────────────────────────────────────────────────────── */

interface DatasetMetrics {
  dataset: string;
  corpus_size: number;
  query_count: number;
  metrics: Record<string, number>;
  ingest_duration_sec: number;
  eval_duration_sec: number;
  error?: string;
}

interface TrackAJob {
  run_id: string;
  graph_id: string;
  status: "running" | "completed" | "failed";
  progress_message: string;
  total_duration_sec: number;
  datasets: DatasetMetrics[];
}

interface SessionRetention {
  session_id: number;
  label: string;
  docs_ingested: number;
  "recall@5": number;
  "ndcg@10": number;
}

interface TrackCResult {
  run_id: string;
  duration_sec: number;
  session_retention: SessionRetention[];
  cross_session_recall: number;
  update_accuracy: number;
  stale_suppression: number;
  multihop_accuracy: number;
  hallucination_rate: number;
  long_horizon_recall: number;
  continuity_score: number;
  notes: string[];
  errors: string[];
}

interface TrackBResult {
  run_id: string;
  duration_sec: number;
  retention: Record<string, number>;
  update_accuracy: number;
  deletion_completeness: number;
  hallucination_rate: number;
  answer_consistency: number;
  citation_accuracy: number;
  notes: string[];
  errors: string[];
}

/* ── Static baseline descriptions ────────────────────────────────────────── */

const BM_SYSTEM = [
  {
    id: "BM-1",
    name: "Determinism Proof",
    what: "Graph hash is stable across identical state",
  },
  {
    id: "BM-2",
    name: "Cryptographic Integrity",
    what: "Current hash matches stored diagnostics snapshot",
  },
  {
    id: "BM-3",
    name: "Mathematical Invariants",
    what: "Inheritance sums, weight bounds, event consistency",
  },
  {
    id: "BM-4",
    name: "Zero-LLM Operation",
    what: "Core engine runs without any cloud API keys",
  },
  {
    id: "BM-5",
    name: "Deduplication Effectiveness",
    what: "% of re-ingested content correctly collapsed",
  },
  {
    id: "BM-6",
    name: "Self-Evolution",
    what: "Lambda pressure + merge/prune/invention activity",
  },
  {
    id: "BM-7",
    name: "Pipeline Performance",
    what: "Ingest latency vs STRICT budget (25ms p95 target)",
  },
  {
    id: "BM-8",
    name: "Query Fidelity",
    what: "Same query run twice produces identical ranked list",
  },
  {
    id: "BM-9",
    name: "Multi-Tenant Isolation",
    what: "All rows scoped to correct tenant_id",
  },
];

/* ── Sub-components ──────────────────────────────────────────────────────── */

function MetricCell({
  value,
  highlight,
}: {
  value: number | null | undefined;
  highlight?: boolean;
}) {
  if (value === null || value === undefined)
    return (
      <td className="py-2 px-3 text-center text-slate-600 font-mono text-[12px]">
        —
      </td>
    );
  return (
    <td
      className={`py-2 px-3 text-center font-mono font-bold text-[12px] ${highlight ? "text-cyan-300" : "text-slate-400"}`}
    >
      {value.toFixed(3)}
    </td>
  );
}

function StatusChip({ ok }: { ok: boolean | null }) {
  if (ok === null)
    return (
      <span className="text-[9px] px-1.5 py-0.5 rounded border bg-slate-800 text-slate-500 border-slate-700">
        —
      </span>
    );
  return ok ? (
    <span className="text-[9px] px-1.5 py-0.5 rounded border bg-green-500/10 text-green-400 border-green-500/30">
      PASS
    </span>
  ) : (
    <span className="text-[9px] px-1.5 py-0.5 rounded border bg-amber-500/10 text-amber-400 border-amber-500/30">
      WARN
    </span>
  );
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-xl font-bold text-white mb-2 mt-10">{children}</h2>
  );
}

function TrackAPanel({ graphId }: { graphId: string | null }) {
  const [job, setJob] = useState<TrackAJob | null>(null);
  const [starting, setStarting] = useState(false);

  const startJob = useCallback(async () => {
    if (!graphId) return;
    setStarting(true);
    const result = await apiFetch<TrackAJob>(
      `/api/v1/faim-bench/${encodeURIComponent(graphId)}/track-a/start`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset_names: ["scifact", "nfcorpus"],
          max_corpus: null,
          max_queries: null,
        }),
      },
    );
    if (result) setJob(result);
    setStarting(false);
  }, [graphId]);

  // Poll while running
  useEffect(() => {
    if (!job || job.status !== "running" || !graphId) return;
    const interval = setInterval(async () => {
      const updated = await apiFetch<TrackAJob>(
        `/api/v1/faim-bench/${encodeURIComponent(graphId)}/track-a/status/${job.run_id}`,
      );
      if (updated) {
        setJob(updated);
        if (updated.status !== "running") clearInterval(interval);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [job, graphId]);

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-5">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[9px] font-bold px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
              {job?.status === "running"
                ? "RUNNING"
                : job?.status === "completed"
                  ? "LIVE"
                  : "READY"}
            </span>
            <h3 className="text-base font-bold text-white">
              Track A — BEIR Retrieval Quality
            </h3>
          </div>
          <p className="text-[12px] text-slate-400">
            Downloads SciFact + NFCorpus from HuggingFace, ingests into FAIM,
            evaluates Recall@k, nDCG@10, MRR against ground-truth qrels.
          </p>
        </div>
        {!job && (
          <button
            onClick={startJob}
            disabled={starting || !graphId}
            className="shrink-0 ml-4 px-4 py-2 text-[12px] font-bold rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white disabled:opacity-40 transition-colors"
          >
            {starting ? "Starting…" : "Run Now"}
          </button>
        )}
      </div>

      {job?.status === "running" && (
        <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-[11px] font-bold text-cyan-400">
              Running in background…
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-mono">
            {job.progress_message}
          </p>
        </div>
      )}

      {job?.status === "completed" && job.datasets.length > 0 && (
        <div className="overflow-x-auto mt-3">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700/60">
                <th className="text-left py-2 pr-3 text-[10px] font-bold text-slate-500 uppercase">
                  Dataset
                </th>
                <th className="text-center py-2 px-2 text-[10px] font-bold text-slate-500 uppercase">
                  Corpus
                </th>
                <th className="text-center py-2 px-2 text-[10px] font-bold text-cyan-500 uppercase">
                  Recall@5
                </th>
                <th className="text-center py-2 px-2 text-[10px] font-bold text-cyan-500 uppercase">
                  nDCG@10
                </th>
                <th className="text-center py-2 px-2 text-[10px] font-bold text-cyan-500 uppercase">
                  MRR
                </th>
                <th className="text-center py-2 px-2 text-[10px] font-bold text-slate-500 uppercase">
                  Ingest
                </th>
              </tr>
            </thead>
            <tbody>
              {job.datasets.map((ds) => (
                <tr key={ds.dataset} className="border-b border-slate-800/40">
                  <td className="py-2 pr-3 font-bold text-slate-200 text-[12px]">
                    {ds.dataset}
                  </td>
                  <td className="py-2 px-2 text-center text-slate-500 text-[12px]">
                    {ds.corpus_size.toLocaleString()}
                  </td>
                  <MetricCell value={ds.metrics["recall@5"]} highlight />
                  <MetricCell value={ds.metrics["ndcg@10"]} highlight />
                  <MetricCell value={ds.metrics["mrr"]} highlight />
                  <td className="py-2 px-2 text-center text-slate-500 text-[11px]">
                    {ds.ingest_duration_sec.toFixed(0)}s
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-[10px] text-slate-600 mt-2">
            Run {new Date().toLocaleDateString()} · FAIM-Native v1 · scifact +
            nfcorpus BEIR splits · HuggingFace BeIR/
          </p>
        </div>
      )}

      {!job && (
        <div className="text-[11px] text-slate-500 mt-2">
          {graphId
            ? "Click Run Now to start. Downloads ~8MB of BEIR datasets from HuggingFace, runs evaluation in background."
            : "Log in and open a graph to run this evaluation."}
        </div>
      )}
    </div>
  );
}

function TrackCPanel({ result }: { result: TrackCResult | null }) {
  if (!result) {
    return (
      <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-5">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[9px] font-bold px-2 py-0.5 rounded bg-slate-700/40 text-slate-400 border border-slate-600/30">
            READY
          </span>
          <h3 className="text-base font-bold text-white">
            Track C — Long-Horizon Continuity
          </h3>
        </div>
        <p className="text-[12px] text-slate-400">
          8 simulated sessions, 40 documents. Measures fact retention per
          session, cross-session multi-hop recall, update accuracy, stale
          suppression, hallucination rate.
        </p>
        <p className="text-[11px] text-slate-500 mt-2">
          Run via the dashboard: POST
          /api/v1/faim-bench/&#123;graph_id&#125;/track-c
        </p>
      </div>
    );
  }
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-5">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[9px] font-bold px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
          LIVE
        </span>
        <h3 className="text-base font-bold text-white">
          Track C — Long-Horizon Continuity
        </h3>
        <span className="text-[10px] text-slate-500 ml-auto">
          {result.duration_sec.toFixed(1)}s
        </span>
      </div>

      {/* Composite score */}
      <div className="grid grid-cols-4 gap-3 mb-4">
        {[
          {
            label: "Continuity Score",
            value: result.continuity_score,
            highlight: true,
          },
          {
            label: "Long-Horizon Recall",
            value: result.long_horizon_recall,
            highlight: false,
          },
          {
            label: "Cross-Session Recall",
            value: result.cross_session_recall,
            highlight: false,
          },
          {
            label: "Hallucination Rate ↓",
            value: result.hallucination_rate,
            highlight: false,
          },
        ].map(({ label, value, highlight }) => (
          <div
            key={label}
            className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-3 text-center"
          >
            <p className="text-[9px] text-slate-500 uppercase tracking-wider mb-1">
              {label}
            </p>
            <p
              className={`text-xl font-bold font-mono ${highlight ? "text-cyan-300" : "text-slate-300"}`}
            >
              {value.toFixed(3)}
            </p>
          </div>
        ))}
      </div>

      {/* Per-session retention */}
      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">
        Per-Session Retention
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700/50">
              <th className="text-left py-1.5 pr-3 text-[10px] text-slate-500">
                Session
              </th>
              <th className="text-left py-1.5 pr-3 text-[10px] text-slate-500">
                Label
              </th>
              <th className="text-center py-1.5 px-2 text-[10px] text-cyan-500">
                Recall@5
              </th>
              <th className="text-center py-1.5 px-2 text-[10px] text-cyan-500">
                nDCG@10
              </th>
            </tr>
          </thead>
          <tbody>
            {result.session_retention.map((s) => (
              <tr key={s.session_id} className="border-b border-slate-800/30">
                <td className="py-1.5 pr-3 text-slate-400 font-mono text-[11px]">
                  S{s.session_id}
                </td>
                <td className="py-1.5 pr-3 text-slate-300 text-[11px]">
                  {s.label}
                </td>
                <td className="py-1.5 px-2 text-center font-mono text-[12px] text-cyan-300 font-bold">
                  {s["recall@5"].toFixed(3)}
                </td>
                <td className="py-1.5 px-2 text-center font-mono text-[12px] text-cyan-300 font-bold">
                  {s["ndcg@10"].toFixed(3)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Other metrics */}
      <div className="grid grid-cols-3 gap-2 mt-3">
        {[
          { label: "Update Accuracy", value: result.update_accuracy },
          { label: "Stale Suppression", value: result.stale_suppression },
          { label: "Multi-Hop Accuracy", value: result.multihop_accuracy },
        ].map(({ label, value }) => (
          <div key={label} className="rounded p-2 bg-slate-800/30 text-center">
            <p className="text-[9px] text-slate-500 uppercase">{label}</p>
            <p className="text-base font-bold font-mono text-slate-300">
              {value.toFixed(3)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Page ───────────────────────────────────────────────────────────────── */

export default function BenchmarksPublicPage() {
  const [trackC, setTrackC] = useState<TrackCResult | null>(null);
  const [graphId, setGraphId] = useState<string | null>(null);

  // Try to read graph_id from session storage (set by the app when user logs in)
  useEffect(() => {
    try {
      const stored =
        sessionStorage.getItem("faim_graph_id") ||
        localStorage.getItem("faim_graph_id");
      if (stored) setGraphId(stored);
    } catch {}
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="max-w-5xl mx-auto px-6 py-16">
        {/* Header */}
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-[10px] font-bold tracking-widest text-cyan-500 uppercase">
              FAIM-Bench v1
            </span>
            <span className="text-[10px] text-slate-600">
              FAIM-Native v1 · {new Date().getFullYear()}
            </span>
          </div>
          <h1 className="text-4xl font-bold text-white mb-4">
            Benchmark Transparency
          </h1>
          <p className="text-slate-400 text-lg max-w-3xl">
            Claimable public results are Track A, Track D, and BM-1..BM-9. Track
            B, Track C, Track E, and Track F are internal synthetic validation
            suites and are not public performance claims.
          </p>
          <div className="flex gap-3 mt-5 flex-wrap">
            <Link
              href="/dashboard/benchmarks"
              className="text-[11px] px-3 py-1.5 rounded border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10 transition-colors"
            >
              Live Dashboard →
            </Link>
            <Link
              href="/docs#faim-bench-v1"
              className="text-[11px] px-3 py-1.5 rounded border border-slate-600 text-slate-400 hover:bg-slate-800 transition-colors"
            >
              Benchmark Spec
            </Link>
          </div>
        </div>

        {/* Honesty notice */}
        <div className="mb-8 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-[12px] text-slate-300">
          <span className="font-bold text-amber-400">Evaluation status: </span>
          Track A downloads and evaluates against real BEIR ground-truth
          relevance judgments (scifact + nfcorpus). Track D reads live
          telemetry. Tracks B, C, E, and F are synthetic validation only. All
          "—" cells are genuinely not yet run — we do not fill estimates.
          Baseline columns are reference values, not our own measured results.
        </div>

        {/* Track A */}
        <SectionHeader>Track A — Retrieval Quality (BEIR)</SectionHeader>
        <p className="text-[12px] text-slate-400 mb-4">
          Standard IR evaluation: FAIM ingests the full BEIR corpus, retrieves
          for each test query, metrics computed against qrels. Comparable to
          published RAG and dense retrieval systems.
        </p>
        <TrackAPanel graphId={graphId} />

        {/* BEIR published baselines */}
        <div className="mt-4 rounded-xl border border-slate-700/50 bg-slate-900/30 p-4 overflow-x-auto">
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">
            Published Baseline Reference (nDCG@10) — from BEIR leaderboard
          </p>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700/50">
                <th className="text-left py-2 pr-4 text-[10px] text-slate-500">
                  System
                </th>
                <th className="text-center py-2 px-3 text-[10px] text-slate-500">
                  SciFact
                </th>
                <th className="text-center py-2 px-3 text-[10px] text-slate-500">
                  NFCorpus
                </th>
                <th className="text-center py-2 px-3 text-[10px] text-slate-500">
                  FiQA
                </th>
                <th className="text-left py-2 pl-3 text-[10px] text-slate-500">
                  Source
                </th>
              </tr>
            </thead>
            <tbody className="text-[12px]">
              {[
                [
                  "BM25 (Chunk-RAG baseline)",
                  "0.665",
                  "0.325",
                  "0.236",
                  "BEIR paper (2021)",
                ],
                ["DPR (Dense)", "0.318", "0.189", "0.295", "BEIR paper (2021)"],
                [
                  "SPLADE-v2 (Sparse learned)",
                  "0.719",
                  "0.336",
                  "0.336",
                  "SPLADE (2022)",
                ],
                [
                  "ColBERTv2 (Late interaction)",
                  "0.716",
                  "0.337",
                  "0.356",
                  "BEIR leaderboard",
                ],
                ["FAIM-Native v1", "—", "—", "—", "run Track A above"],
              ].map(([system, scifact, nf, fiqa, src]) => (
                <tr
                  key={system as string}
                  className="border-b border-slate-800/30 hover:bg-slate-800/20"
                >
                  <td
                    className={`py-2 pr-4 font-medium ${(system as string).includes("FAIM") ? "text-cyan-300" : "text-slate-300"}`}
                  >
                    {system}
                  </td>
                  <td className="py-2 px-3 text-center font-mono text-slate-400">
                    {scifact}
                  </td>
                  <td className="py-2 px-3 text-center font-mono text-slate-400">
                    {nf}
                  </td>
                  <td className="py-2 px-3 text-center font-mono text-slate-400">
                    {fiqa}
                  </td>
                  <td className="py-2 pl-3 text-slate-600 text-[10px]">
                    {src}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Track B */}
        <SectionHeader>Track B — Persistent Memory</SectionHeader>
        <p className="text-[12px] text-slate-400 mb-4">
          Internal synthetic validation only. Measures Recall@k, update
          accuracy, deletion completeness, hallucination rate, citation
          accuracy, and answer consistency. Not a public claim.
        </p>
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[9px] font-bold px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
              LIVE
            </span>
            <h3 className="text-base font-bold text-white">
              Track B — Persistent Memory
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/60">
                  <th className="text-left py-2 pr-4 text-[10px] text-slate-500 uppercase w-[200px]">
                    Metric
                  </th>
                  <th className="text-center py-2 px-3 text-[10px] text-cyan-500 uppercase">
                    FAIM-Native
                  </th>
                  <th className="text-center py-2 px-3 text-[10px] text-slate-500 uppercase">
                    Chunk-RAG
                  </th>
                  <th className="text-center py-2 px-3 text-[10px] text-slate-500 uppercase">
                    Summary Mem
                  </th>
                  <th className="text-left py-2 pl-3 text-[10px] text-slate-500 uppercase">
                    Notes
                  </th>
                </tr>
              </thead>
              <tbody className="text-[12px]">
                {[
                  [
                    "Retention Recall@5",
                    null,
                    "~0.70",
                    "~0.25",
                    "Run Track B to populate FAIM column",
                  ],
                  ["Retention nDCG@10", null, "~0.58", "~0.18", ""],
                  ["MRR", null, "~0.64", "~0.31", ""],
                  [
                    "Update Accuracy",
                    null,
                    "N/A",
                    "~0.40",
                    "Chunk-RAG has no update model",
                  ],
                  ["Deletion Completeness", null, "~0.70", "~0.60", ""],
                  [
                    "Hallucination Rate ↓",
                    null,
                    "~0.18",
                    "~0.32",
                    "Lower is better",
                  ],
                  ["Answer Consistency", null, "~0.80", "~0.55", ""],
                  ["Citation Accuracy", null, "~0.68", "~0.30", ""],
                ].map(([metric, faim, chunk, summary, note]) => (
                  <tr
                    key={metric as string}
                    className="border-b border-slate-800/30"
                  >
                    <td className="py-2 pr-4 text-slate-300">{metric}</td>
                    <td className="py-2 px-3 text-center font-mono font-bold text-slate-600">
                      {faim ?? "—"}
                    </td>
                    <td className="py-2 px-3 text-center font-mono text-slate-500">
                      {chunk}
                    </td>
                    <td className="py-2 px-3 text-center font-mono text-slate-500">
                      {summary}
                    </td>
                    <td className="py-2 pl-3 text-slate-600 text-[10px]">
                      {note}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[10px] text-slate-600 mt-2">
            Chunk-RAG / Summary Memory columns are reference examples only. Do
            not cite them as our measured results.
          </p>
        </div>

        {/* Track C */}
        <SectionHeader>Track C — Long-Horizon Continuity</SectionHeader>
        <p className="text-[12px] text-slate-400 mb-4">
          Internal synthetic validation only. Tests fact retention per session,
          cross-session multi-hop queries, stale fact suppression, and
          long-horizon recall. Not a public claim.
        </p>
        <TrackCPanel result={trackC} />

        {/* Track D */}
        <SectionHeader>Track D — Efficiency</SectionHeader>
        <p className="text-[12px] text-slate-400 mb-4">
          Real telemetry only. Safe to cite publicly if you reproduce the run
          under the same graph and environment.
        </p>
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[9px] font-bold px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
              LIVE
            </span>
            <h3 className="text-base font-bold text-white">
              Track D — Efficiency
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/60">
                  <th className="text-left py-2 pr-4 text-[10px] text-slate-500 uppercase w-[220px]">
                    Metric
                  </th>
                  <th className="text-center py-2 px-3 text-[10px] text-cyan-500 uppercase">
                    FAIM-Native
                  </th>
                  <th className="text-center py-2 px-3 text-[10px] text-slate-500 uppercase">
                    BM25 Chunk-RAG
                  </th>
                  <th className="text-left py-2 pl-3 text-[10px] text-slate-500 uppercase">
                    Notes
                  </th>
                </tr>
              </thead>
              <tbody className="text-[12px]">
                {[
                  [
                    "Ingest Latency p50 (ms) ↓",
                    null,
                    "~12",
                    "From live event log",
                  ],
                  [
                    "Ingest Latency p95 (ms) ↓",
                    null,
                    "~28",
                    "STRICT budget target: 25ms",
                  ],
                  [
                    "Retrieval Latency p95 (ms) ↓",
                    null,
                    "~22",
                    "From LatencyCollector",
                  ],
                  [
                    "Compression Ratio ↑",
                    null,
                    "1.0×",
                    "Higher = more efficient dedup",
                  ],
                  [
                    "Ingest Throughput (docs/s) ↑",
                    null,
                    "~85",
                    "From global_throughput tracker",
                  ],
                ].map(([metric, faim, baseline, note]) => (
                  <tr
                    key={metric as string}
                    className="border-b border-slate-800/30"
                  >
                    <td className="py-2 pr-4 text-slate-300">{metric}</td>
                    <td className="py-2 px-3 text-center font-mono font-bold text-slate-600">
                      {faim ?? "—"}
                    </td>
                    <td className="py-2 px-3 text-center font-mono text-slate-500">
                      {baseline}
                    </td>
                    <td className="py-2 pl-3 text-slate-600 text-[10px]">
                      {note}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* BM-1 to BM-9 */}
        <SectionHeader>BM-1 to BM-9 — System Property Checks</SectionHeader>
        <p className="text-[12px] text-slate-400 mb-4">
          Not retrieval quality benchmarks. These verify correctness properties
          of the FAIM engine running continuously against your live graph.
        </p>
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700/60">
                <th className="text-left py-3 px-5 text-[10px] text-slate-500 uppercase">
                  ID
                </th>
                <th className="text-left py-3 px-4 text-[10px] text-slate-500 uppercase">
                  Name
                </th>
                <th className="text-left py-3 px-4 text-[10px] text-slate-500 uppercase">
                  What it measures
                </th>
              </tr>
            </thead>
            <tbody>
              {BM_SYSTEM.map((bm) => (
                <tr
                  key={bm.id}
                  className="border-b border-slate-800/40 hover:bg-slate-800/20"
                >
                  <td className="py-3 px-5 font-mono text-[11px] text-cyan-400">
                    {bm.id}
                  </td>
                  <td className="py-3 px-4 text-slate-200 text-[12px] font-medium">
                    {bm.name}
                  </td>
                  <td className="py-3 px-4 text-slate-400 text-[12px]">
                    {bm.what}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Claims */}
        <div className="grid grid-cols-2 gap-6 mt-10 mb-10">
          <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-5">
            <p className="text-[10px] font-bold text-green-400 uppercase tracking-wider mb-3">
              Verifiable claims
            </p>
            <ul className="space-y-1.5 text-[12px] text-slate-300">
              <li>
                ✓ Ingest is deterministic — same content → same graph hash
              </li>
              <li>✓ Engine operates without cloud LLM API keys</li>
              <li>✓ Re-ingested content is correctly deduplicated</li>
              <li>✓ All stored rows are tenant-scoped</li>
              <li>
                ✓ Graph invariants (inheritance, weight bounds) are enforced
              </li>
            </ul>
          </div>
          <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-5">
            <p className="text-[10px] font-bold text-red-400 uppercase tracking-wider mb-3">
              Claims we do NOT make
            </p>
            <ul className="space-y-1.5 text-[12px] text-slate-400">
              <li>✗ "Beats OpenAI / Google memory" — not benchmarked</li>
              <li>✗ "Best retrieval on BEIR" — Track A results pending</li>
              <li>✗ "Zero hallucination" — measured, not zero</li>
              <li>✗ Any number not measured by us</li>
            </ul>
          </div>
        </div>

        <div className="text-center text-[11px] text-slate-600">
          FAIM-Bench v1 · FAIM-Native v1 · {new Date().getFullYear()}
          <span className="mx-2">·</span>
          <Link href="/docs" className="hover:text-slate-400 transition-colors">
            Documentation
          </Link>
          <span className="mx-2">·</span>
          <Link
            href="/dashboard/benchmarks"
            className="hover:text-slate-400 transition-colors"
          >
            Live Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
