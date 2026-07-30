export type BenchmarkSeriesPoint = {
  timestamp?: string;
  nodes: number;
  cr: number;
  redundancy: number;
  drift: number;
  latency: {
    store_p50_ms: number;
    retrieve_p50_ms: number;
    retrieve_p95_ms: number;
  };
};

export type BenchmarkEvidence = Record<string, unknown>;

export type BenchmarkItem = {
  benchmark_id: string;
  name: string;
  passed: boolean;
  score: number;
  status: string;
  evidence_hash: string;
  evidence: BenchmarkEvidence;
  notes: string[];
};

export type BenchmarkSuiteRun = {
  run_id: string;
  tenant_id: string;
  graph_id: string;
  graph_version: number;
  graph_hash: string;
  diagnostics_hash: string;
  computed_at: string;
  duration_ms: number;
  node_count: number;
  edge_count: number;
  atom_count: number;
  macro_count: number;
  compression_ratio: number;
  throughput_synapses_per_sec: number;
  budget_profile: string;
  benchmark_count: number;
  passed_count: number;
  failed_count: number;
  overall_score: number;
  summary: Record<string, unknown>;
  benchmarks: BenchmarkItem[];
};

export type GoldenSignal = {
  latency: Record<string, number>;
  traffic: Record<string, number>;
  errors: Record<string, number>;
  saturation: Record<string, number>;
};

export type BenchmarkAlert = {
  id: string;
  severity: "info" | "warning" | "critical";
  title: string;
  message: string;
  metric: string;
  current_value: number;
  threshold: number;
  triggered_at: string;
};

export type StressTestResult = {
  concurrency: number;
  document_count: number;
  total_docs_ingested: number;
  ingest_latency_p50_ms: number;
  ingest_latency_p95_ms: number;
  ingest_latency_p99_ms: number;
  throughput_docs_per_sec: number;
  total_duration_sec: number;
  invariants_passed: boolean;
  error_count: number;
};

export type BenchmarkReport = {
  graph_id: string;
  export_timestamp: string;
  report_hash: string;
  snapshot: BenchmarkSuiteRun;
  alerts: BenchmarkAlert[];
  infrastructure: Record<string, unknown>;
};

export type PublicationLeaderboardRow = {
  system: string;
  "recall@5": number;
  "ndcg@10": number;
  mrr: number;
  map: number;
  task_completion_rate: number;
};

export type PublicationRun = {
  run_id: string;
  graph_id: string;
  started_at: string;
  total_duration_sec: number;
  datasets: string[];
  faim_track_a: Record<string, unknown>;
  track_e: Record<string, unknown>;
  track_f: Record<string, unknown>;
  baselines: Record<string, Array<Record<string, unknown>>>;
  mteb: Record<string, unknown>;
  workflow_checks: Record<string, unknown>;
  system_comparison: Array<Record<string, unknown>>;
  leaderboard: PublicationLeaderboardRow[];
  results_report: Record<string, unknown>;
  reproducibility_kit: Record<string, unknown>;
  benchmark_spec: Record<string, unknown>;
};

export type PublicationJobStatus = {
  run_id: string;
  graph_id: string;
  status: "running" | "completed" | "failed";
  progress_message: string;
  total_duration_sec: number;
  result: PublicationRun | null;
};
