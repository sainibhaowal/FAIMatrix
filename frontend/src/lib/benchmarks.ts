import { apiGet, apiPost, resolveGraphId } from "@/lib/api-client";
import type {
  BenchmarkSeriesPoint,
  BenchmarkSuiteRun,
  GoldenSignal,
  BenchmarkAlert,
  StressTestResult,
  BenchmarkReport,
  PublicationRun,
  PublicationLeaderboardRow,
  PublicationJobStatus,
} from "@/types/benchmarks";

const PUBLICATION_API_SUPPORT_KEY = "faim.publication_api_supported";

function isPublicationApiSupported(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(PUBLICATION_API_SUPPORT_KEY) !== "0";
}

function setPublicationApiSupported(supported: boolean): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(
    PUBLICATION_API_SUPPORT_KEY,
    supported ? "1" : "0",
  );
}

function is404Error(err: unknown): boolean {
  return err instanceof Error && /API Error 404:/i.test(err.message);
}

function normalizeRunAllToPublicationRun(
  graphId: string,
  runAll: any,
): PublicationRun {
  const nowIso = new Date().toISOString();
  return {
    run_id: `fallback-${Date.now()}`,
    graph_id: graphId,
    started_at: nowIso,
    total_duration_sec: 0,
    datasets: ["fallback-run-all"],
    faim_track_a: {},
    track_e: runAll?.track_e ?? {},
    track_f: runAll?.track_f ?? {},
    baselines: {},
    mteb: {},
    workflow_checks: {},
    system_comparison: Array.isArray(runAll?.system_comparison)
      ? runAll.system_comparison
      : [],
    leaderboard: [],
    results_report: {},
    reproducibility_kit: {},
    benchmark_spec: {
      source: "run-all-fallback",
      note: "Publication endpoints unavailable in API; using FAIM bench summary fallback",
    },
  };
}

export async function fetchLatestBenchmark(
  graphId?: string,
): Promise<BenchmarkSuiteRun | null> {
  const gid = resolveGraphId(graphId);
  if (!gid) return null;

  return apiGet<BenchmarkSuiteRun | null>(
    `/benchmarks/${encodeURIComponent(gid)}/latest`,
  ).catch(() => null);
}

export async function runBenchmarkSuite(
  graphId?: string,
): Promise<BenchmarkSuiteRun | null> {
  const gid = resolveGraphId(graphId);
  if (!gid) return null;

  return apiPost<BenchmarkSuiteRun>(
    `/benchmarks/${encodeURIComponent(gid)}/run`,
  ).catch(() => null);
}

export async function fetchBenchmarkSeries(
  graphId?: string,
  limit = 200,
): Promise<BenchmarkSeriesPoint[]> {
  const gid = resolveGraphId(graphId);
  if (!gid) return [];

  return apiGet<BenchmarkSeriesPoint[] | { points?: BenchmarkSeriesPoint[] }>(
    `/benchmarks/${encodeURIComponent(gid)}/series?limit=${limit}`,
  )
    .then((response) => {
      if (Array.isArray(response)) return response;
      if (response && Array.isArray(response.points)) return response.points;
      return [];
    })
    .catch(() => []);
}

export async function fetchBenchmarkRuns(
  graphId?: string,
  limit = 50,
): Promise<BenchmarkSuiteRun[]> {
  const gid = resolveGraphId(graphId);
  if (!gid) return [];

  return apiGet<BenchmarkSuiteRun[] | { runs?: BenchmarkSuiteRun[] }>(
    `/benchmarks/${encodeURIComponent(gid)}/runs?limit=${limit}`,
  )
    .then((response) => {
      if (Array.isArray(response)) return response;
      if (response && Array.isArray(response.runs)) return response.runs;
      return [];
    })
    .catch(() => []);
}

export async function fetchBenchmarkRunById(
  graphId: string | undefined,
  runId: string,
): Promise<BenchmarkSuiteRun | null> {
  const gid = resolveGraphId(graphId);
  if (!gid || !runId.trim()) return null;

  return apiGet<BenchmarkSuiteRun>(
    `/benchmarks/${encodeURIComponent(gid)}/runs/${encodeURIComponent(runId)}`,
  ).catch(() => null);
}

// Phase 4: Golden Signals
export async function fetchGoldenSignals(
  graphId?: string,
): Promise<GoldenSignal | null> {
  const gid = resolveGraphId(graphId);
  if (!gid) return null;

  return apiGet<GoldenSignal>(
    `/benchmarks/${encodeURIComponent(gid)}/golden-signals`,
  ).catch(() => null);
}

// Phase 6: Stress Testing
export async function runStressTest(
  graphId?: string,
  config?: {
    maxConcurrency?: number;
    documentCount?: number;
    testDocSize?: string;
  },
): Promise<{ results?: StressTestResult[] } | null> {
  const gid = resolveGraphId(graphId);
  if (!gid) return null;

  return apiPost<{ results?: StressTestResult[] }>(
    `/benchmarks/${encodeURIComponent(gid)}/stress`,
    {
      max_concurrency: config?.maxConcurrency || 10,
      document_count: config?.documentCount || 100,
      test_doc_size: config?.testDocSize || "small",
    },
  ).catch(() => null);
}

// Phase 8: Alerts
export async function fetchAlerts(graphId?: string): Promise<{
  alerts?: BenchmarkAlert[];
  critical_count?: number;
  warning_count?: number;
} | null> {
  const gid = resolveGraphId(graphId);
  if (!gid) return null;

  return apiGet<{
    alerts?: BenchmarkAlert[];
    critical_count?: number;
    warning_count?: number;
  }>(`/benchmarks/${encodeURIComponent(gid)}/alerts`).catch(() => null);
}

// Phase 8: Export
export async function exportBenchmarkReport(
  graphId?: string,
): Promise<BenchmarkReport | null> {
  const gid = resolveGraphId(graphId);
  if (!gid) return null;

  return apiPost<BenchmarkReport>(
    `/benchmarks/${encodeURIComponent(gid)}/export`,
  ).catch(() => null);
}

export async function runPublicationSuite(
  graphId?: string,
  config?: { datasetNames?: string[]; maxCorpus?: number; maxQueries?: number },
): Promise<PublicationRun | null> {
  const gid = resolveGraphId(graphId);
  if (!gid) return null;

  if (isPublicationApiSupported()) {
    try {
      const result = await apiPost<PublicationRun>(
        `/faim-bench/${encodeURIComponent(gid)}/publication/run`,
        {
          dataset_names: config?.datasetNames ?? [
            "scifact",
            "nq",
            "hotpotqa",
            "fever",
            "msmarco",
          ],
          max_corpus: config?.maxCorpus,
          max_queries: config?.maxQueries,
        },
      );
      setPublicationApiSupported(true);
      return result;
    } catch (err) {
      if (is404Error(err)) setPublicationApiSupported(false);
    }
  }

  // Backward-compatible fallback for deployments without publication endpoints.
  const fallback = await apiPost<any>(
    `/faim-bench/${encodeURIComponent(gid)}/run-all`,
  ).catch(() => null);
  if (!fallback) return null;
  return normalizeRunAllToPublicationRun(gid, fallback);
}

export async function startPublicationSuite(
  graphId?: string,
  config?: { datasetNames?: string[]; maxCorpus?: number; maxQueries?: number },
): Promise<PublicationJobStatus | null> {
  const gid = resolveGraphId(graphId);
  if (!gid) return null;

  if (!isPublicationApiSupported()) return null;
  return apiPost<PublicationJobStatus>(
    `/faim-bench/${encodeURIComponent(gid)}/publication/start`,
    {
      dataset_names: config?.datasetNames ?? [
        "scifact",
        "nq",
        "hotpotqa",
        "fever",
        "msmarco",
      ],
      max_corpus: config?.maxCorpus,
      max_queries: config?.maxQueries,
    },
  )
    .then((result) => {
      setPublicationApiSupported(true);
      return result;
    })
    .catch((err) => {
      if (is404Error(err)) setPublicationApiSupported(false);
      return null;
    });
}

export async function fetchPublicationStatus(
  graphId: string | undefined,
  runId: string,
): Promise<PublicationJobStatus | null> {
  const gid = resolveGraphId(graphId);
  if (!gid || !runId.trim()) return null;

  if (!isPublicationApiSupported()) return null;
  return apiGet<PublicationJobStatus>(
    `/faim-bench/${encodeURIComponent(gid)}/publication/status/${encodeURIComponent(runId)}`,
  )
    .then((result) => {
      setPublicationApiSupported(true);
      return result;
    })
    .catch((err) => {
      if (is404Error(err)) setPublicationApiSupported(false);
      return null;
    });
}

export async function fetchPublicationLatest(
  graphId?: string,
): Promise<PublicationRun | null> {
  const gid = resolveGraphId(graphId);
  if (!gid) return null;

  if (!isPublicationApiSupported()) return null;
  return apiGet<PublicationRun | null>(
    `/faim-bench/${encodeURIComponent(gid)}/publication/latest`,
  )
    .then((result) => {
      setPublicationApiSupported(true);
      return result;
    })
    .catch((err) => {
      if (is404Error(err)) setPublicationApiSupported(false);
      return null;
    });
}

export async function fetchPublicationLeaderboard(
  graphId?: string,
): Promise<PublicationLeaderboardRow[]> {
  const gid = resolveGraphId(graphId);
  if (!gid) return [];

  return apiGet<{ leaderboard?: PublicationLeaderboardRow[] }>(
    `/faim-bench/${encodeURIComponent(gid)}/publication/leaderboard`,
  )
    .then((response) =>
      Array.isArray(response?.leaderboard) ? response.leaderboard : [],
    )
    .catch(() => []);
}
