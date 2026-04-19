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
