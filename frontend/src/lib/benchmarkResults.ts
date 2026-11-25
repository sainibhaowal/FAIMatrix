/**
 * Verified FAIM benchmark results from signed 2026-11-24 evaluation artifacts.
 *
 * Source of truth:
 * - faim-benchmarks/results/COMPARISON.md
 * - faim-benchmarks/results/RESULTS.md
 * - faim_native/Docs/13-benchmarks/03-multi-scenario-benchmark-results-2026-11-24.md
 */

export type ScenarioId =
  | "3-gpu-granite"
  | "1-cpu-pure-faim"
  | "2-gpu-pure-faim"
  | "4-hybrid-hw-pure-faim"
  | "5-hybrid-faim-plus-embedding"
  | "bm25-baseline";

export interface BenchmarkDatasetRow {
  dataset: "scifact" | "nfcorpus" | "arguana" | "locomo";
  label: string;
  task: string;
  primaryMetricName: string;
  primaryMetricValue: string;
  secondaryMetrics: string;
  p50Ms: string;
  p95Ms: string;
  gate: "READY" | "BASELINE" | "STOPPED";
}

export interface BenchmarkScenario {
  id: ScenarioId;
  badge: string;
  name: string;
  shortLabel: string;
  mode: string;
  hardware: string;
  highlight: string;
  rows: BenchmarkDatasetRow[];
}

export interface CrossSystemComparisonRow {
  dataset: string;
  graniteGpu: string;
  pureCpuDocker: string;
  pureCpuCi: string;
  bm25Baseline: string;
  balancedGranite: string;
}

export const BENCHMARK_REPORT_DATE = "2026-11-24";

export const BENCHMARK_HIGHLIGHTS = [
  {
    value: "0.6900",
    unit: "nDCG@10",
    label: "BeIR / SciFact · FAIM + Granite 97M",
    detail: "Recall@5 = 0.7704 · vs BM25 0.6644",
    accent: "cyan",
  },
  {
    value: "0.6871",
    unit: "nDCG@10",
    label: "BeIR / SciFact · Pure FAIM Zero-ML CPU",
    detail: "86.31 ms CPU CI · 100.22 ms Docker P50",
    accent: "emerald",
  },
  {
    value: "0.3314",
    unit: "nDCG@10",
    label: "BeIR / NFCorpus · FAIM + Granite 97M",
    detail: "101.62 ms P50 · vs BM25 0.3110",
    accent: "purple",
  },
  {
    value: "0.7266",
    unit: "Recall@10",
    label: "BeIR / ArguAna · FAIM + Granite 97M",
    detail: "304.55 ms P50 · vs BM25 567.83 ms",
    accent: "amber",
  },
] as const;

export const CROSS_SYSTEM_ROWS: CrossSystemComparisonRow[] = [
  {
    dataset: "BeIR / SciFact",
    graniteGpu: "0.6900 (R@5 0.7704 · 140.17 ms)",
    pureCpuDocker: "0.6871 (R@5 0.7554 · 100.22 ms)",
    pureCpuCi: "0.6871 (R@5 0.7554 · 86.31 ms)",
    bm25Baseline: "0.6644 (R@5 0.7193 · 45.76 ms)",
    balancedGranite: "0.6560 (R@5 0.7412 · 2487.46 ms)",
  },
  {
    dataset: "BeIR / NFCorpus",
    graniteGpu: "0.3314 (R@5 0.1297 · 101.62 ms)",
    pureCpuDocker: "0.3267 (R@5 0.1289 · 66.48 ms)",
    pureCpuCi: "0.3267 (R@5 0.1289 · 49.91 ms)",
    bm25Baseline: "0.3110 (R@5 0.1205 · 3.32 ms)",
    balancedGranite: "0.3176 (R@5 0.1264 · 1941.70 ms)",
  },
  {
    dataset: "BeIR / ArguAna",
    graniteGpu: "0.3387 (R@10 0.7266 · 304.55 ms)",
    pureCpuDocker: "0.3149 (R@10 0.6781 · 250.98 ms)",
    pureCpuCi: "0.3149 (R@5 0.4604 · 167.74 ms)",
    bm25Baseline: "0.3451 (R@10 0.7216 · 567.83 ms)",
    balancedGranite: "Stopped early",
  },
  {
    dataset: "LoCoMo (Memory QA)",
    graniteGpu: "0.0710 Fact Recall (234.56 ms · 11.9 tok)",
    pureCpuDocker: "Failed at 18 workers (RAM SIGKILL)",
    pureCpuCi: "Failed (pre-autoscaler)",
    bm25Baseline: "0.2049 Fact Recall (16.02 ms · 92.3 tok)",
    balancedGranite: "Not run",
  },
];

export const BENCHMARK_SCENARIOS: BenchmarkScenario[] = [
  {
    id: "3-gpu-granite",
    badge: "Flagship · 100% Complete",
    name: "Scenario 3: FAIM FAST + Granite 97M GPU",
    shortLabel: "FAIM + Granite GPU",
    mode: "FAIM_PROFILE=fast · FAIM_FAST_ML_EMBEDDING=true · Granite 97M Multilingual R2",
    hardware:
      "2 API + 4 Ingest workers · CUDA GPU · batch=256 · 512 MiB VRAM guard",
    highlight:
      "Highest accuracy across SciFact, NFCorpus, and ArguAna Recall@10, completing all 4 suites with ~18x lower latency than balanced.",
    rows: [
      {
        dataset: "scifact",
        label: "BeIR / SciFact",
        task: "Scientific claim verification",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.6900",
        secondaryMetrics: "Recall@5 = 0.7704 · MRR = 0.6590 · MAP = 0.6483",
        p50Ms: "140.17 ms",
        p95Ms: "208.22 ms",
        gate: "READY",
      },
      {
        dataset: "nfcorpus",
        label: "BeIR / NFCorpus",
        task: "Biomedical nutrition retrieval",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3314",
        secondaryMetrics: "Recall@5 = 0.1297 · MRR = 0.5290 · MAP = 0.1367",
        p50Ms: "101.62 ms",
        p95Ms: "158.14 ms",
        gate: "READY",
      },
      {
        dataset: "arguana",
        label: "BeIR / ArguAna",
        task: "Counter-argument passage matching",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3387",
        secondaryMetrics:
          "Recall@5 = 0.5096 · Recall@10 = 0.7266 · MRR = 0.2279",
        p50Ms: "304.55 ms",
        p95Ms: "485.21 ms",
        gate: "READY",
      },
      {
        dataset: "locomo",
        label: "LoCoMo",
        task: "Long-horizon conversational memory QA",
        primaryMetricName: "Fact Recall",
        primaryMetricValue: "0.0710",
        secondaryMetrics: "Token F1 = 0.0582 · EM = 0.0000 · Avg 11.9 tok",
        p50Ms: "234.56 ms",
        p95Ms: "446.77 ms",
        gate: "READY",
      },
    ],
  },
  {
    id: "1-cpu-pure-faim",
    badge: "CPU / VPS Verified",
    name: "Scenario 1: Pure FAIM Zero-ML (CPU Only)",
    shortLabel: "Pure FAIM CPU",
    mode: "FAIM_PROFILE=fast · FAIM_FAST_ML_EMBEDDING=false · Zero-ML Representation V2",
    hardware:
      "CPU-only execution · FAIM_EMBEDDING_DEVICE=cpu · FAIM_USE_GPU_BACKEND=false",
    highlight:
      "Beats BM25-Baseline on BeIR/SciFact (0.6871 vs 0.6644) and BeIR/NFCorpus (0.3267 vs 0.3110) with zero GPU or ML inference.",
    rows: [
      {
        dataset: "scifact",
        label: "BeIR / SciFact",
        task: "Scientific claim verification",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.6871",
        secondaryMetrics:
          "Recall@5 = 0.7554 · MRR = 0.6564 · CPU CI P50 86.31 ms",
        p50Ms: "100.22 ms",
        p95Ms: "154.94 ms",
        gate: "READY",
      },
      {
        dataset: "nfcorpus",
        label: "BeIR / NFCorpus",
        task: "Biomedical nutrition retrieval",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3267",
        secondaryMetrics:
          "Recall@5 = 0.1289 · MRR = 0.5259 · CPU CI P50 49.91 ms",
        p50Ms: "66.48 ms",
        p95Ms: "142.57 ms",
        gate: "READY",
      },
      {
        dataset: "arguana",
        label: "BeIR / ArguAna",
        task: "Counter-argument passage matching",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3149",
        secondaryMetrics:
          "Recall@5 = 0.4604 · Recall@10 = 0.6781 · MRR = 0.2121",
        p50Ms: "250.98 ms",
        p95Ms: "411.32 ms",
        gate: "READY",
      },
      {
        dataset: "locomo",
        label: "LoCoMo",
        task: "Long-horizon conversational memory QA",
        primaryMetricName: "Status",
        primaryMetricValue: "Failed",
        secondaryMetrics:
          "1 write failed (18-worker RAM SIGKILL before autoscaler cap)",
        p50Ms: "—",
        p95Ms: "—",
        gate: "STOPPED",
      },
    ],
  },
  {
    id: "4-hybrid-hw-pure-faim",
    badge: "Auto Hardware · LoCoMo Complete",
    name: "Scenario 4: Pure FAIM Auto CPU/GPU Hybrid",
    shortLabel: "Hybrid HW Pure",
    mode: "FAIM_PROFILE=fast · FAIM_FAST_ML_EMBEDDING=false · device=auto",
    hardware:
      "Auto hardware detection with bounded workers and CUDA matrix acceleration",
    highlight:
      "Matches deterministic Pure FAIM accuracy while completing LoCoMo at 188.50 ms median latency (0.0715 Fact Recall).",
    rows: [
      {
        dataset: "scifact",
        label: "BeIR / SciFact",
        task: "Scientific claim verification",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.6871",
        secondaryMetrics: "Recall@5 = 0.7554 · MRR = 0.6564 · MAP = 0.6459",
        p50Ms: "102.92 ms",
        p95Ms: "152.59 ms",
        gate: "READY",
      },
      {
        dataset: "nfcorpus",
        label: "BeIR / NFCorpus",
        task: "Biomedical nutrition retrieval",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3267",
        secondaryMetrics: "Recall@5 = 0.1289 · MRR = 0.5259 · MAP = 0.1340",
        p50Ms: "68.98 ms",
        p95Ms: "151.33 ms",
        gate: "READY",
      },
      {
        dataset: "arguana",
        label: "BeIR / ArguAna",
        task: "Counter-argument passage matching",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3149",
        secondaryMetrics: "Recall@5 = 0.4604 · MRR = 0.2121 · MAP = 0.2121",
        p50Ms: "275.16 ms",
        p95Ms: "475.57 ms",
        gate: "READY",
      },
      {
        dataset: "locomo",
        label: "LoCoMo",
        task: "Long-horizon conversational memory QA",
        primaryMetricName: "Fact Recall",
        primaryMetricValue: "0.0715",
        secondaryMetrics: "Token F1 = 0.0584 · EM = 0.0000 · Avg 11.9 tok",
        p50Ms: "188.50 ms",
        p95Ms: "485.03 ms",
        gate: "READY",
      },
    ],
  },
  {
    id: "2-gpu-pure-faim",
    badge: "CUDA Pure Baseline",
    name: "Scenario 2: Pure FAIM Zero-ML (CUDA Matrix Backend)",
    shortLabel: "Pure FAIM GPU",
    mode: "FAIM_PROFILE=fast · FAIM_FAST_ML_EMBEDDING=false · CUDA native backend",
    hardware: "GPU matrix kernels enabled without ML embedding inference",
    highlight:
      "Confirms bit-for-bit ranking parity with CPU Pure FAIM (0.6871 / 0.3267 / 0.3149) with slightly lower tail latency on NFCorpus.",
    rows: [
      {
        dataset: "scifact",
        label: "BeIR / SciFact",
        task: "Scientific claim verification",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.6871",
        secondaryMetrics: "Recall@5 = 0.7554 · MRR = 0.6564 · MAP = 0.6459",
        p50Ms: "100.00 ms",
        p95Ms: "149.72 ms",
        gate: "READY",
      },
      {
        dataset: "nfcorpus",
        label: "BeIR / NFCorpus",
        task: "Biomedical nutrition retrieval",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3267",
        secondaryMetrics: "Recall@5 = 0.1289 · MRR = 0.5259 · MAP = 0.1340",
        p50Ms: "63.34 ms",
        p95Ms: "133.01 ms",
        gate: "READY",
      },
      {
        dataset: "arguana",
        label: "BeIR / ArguAna",
        task: "Counter-argument passage matching",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3149",
        secondaryMetrics:
          "Recall@5 = 0.4604 · Recall@10 = 0.6781 · MRR = 0.2121",
        p50Ms: "250.73 ms",
        p95Ms: "422.23 ms",
        gate: "READY",
      },
      {
        dataset: "locomo",
        label: "LoCoMo",
        task: "Long-horizon conversational memory QA",
        primaryMetricName: "Status",
        primaryMetricValue: "Failed",
        secondaryMetrics:
          "1 write failed (18-worker RAM SIGKILL before autoscaler cap)",
        p50Ms: "—",
        p95Ms: "—",
        gate: "STOPPED",
      },
    ],
  },
  {
    id: "5-hybrid-faim-plus-embedding",
    badge: "Balanced Profile Comparison",
    name: "Scenario 5: FAIM BALANCED + Granite 97M",
    shortLabel: "Balanced + Granite",
    mode: "FAIM_PROFILE=balanced · FAIM_FAST_ML_EMBEDDING=true",
    hardware:
      "Full balanced graph traversal + Granite 97M embedding on every request",
    highlight:
      "Empirical ablation proving FAST + Granite beats BALANCED by +0.034 nDCG@10 on SciFact and runs ~18x faster (140 ms vs 2487 ms).",
    rows: [
      {
        dataset: "scifact",
        label: "BeIR / SciFact",
        task: "Scientific claim verification",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.6560",
        secondaryMetrics: "Recall@5 = 0.7412 · MRR = 0.6227 · MAP = 0.6108",
        p50Ms: "2487.46 ms",
        p95Ms: "8507.69 ms",
        gate: "READY",
      },
      {
        dataset: "nfcorpus",
        label: "BeIR / NFCorpus",
        task: "Biomedical nutrition retrieval",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3176",
        secondaryMetrics: "Recall@5 = 0.1264 · MRR = 0.5178 · MAP = 0.1303",
        p50Ms: "1941.70 ms",
        p95Ms: "6710.75 ms",
        gate: "READY",
      },
      {
        dataset: "arguana",
        label: "BeIR / ArguAna",
        task: "Counter-argument passage matching",
        primaryMetricName: "Status",
        primaryMetricValue: "Stopped early",
        secondaryMetrics:
          "Superseded after FAST ablation showed 18x speedup & higher accuracy",
        p50Ms: "—",
        p95Ms: "—",
        gate: "STOPPED",
      },
    ],
  },
  {
    id: "bm25-baseline",
    badge: "Reference Baseline",
    name: "BM25-Baseline (In-Process CPU Reference)",
    shortLabel: "BM25 Baseline",
    mode: "Standard in-process lexical BM25 reference harness",
    hardware: "CPU CI harness reference baseline",
    highlight:
      "FAIM outperforms BM25 on SciFact (+0.0256 nDCG@10) and NFCorpus (+0.0204), while BM25 leads on extractive LoCoMo token span coverage.",
    rows: [
      {
        dataset: "scifact",
        label: "BeIR / SciFact",
        task: "Scientific claim verification",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.6644",
        secondaryMetrics: "Recall@5 = 0.7193 · MRR = 0.6366 · MAP = 0.6242",
        p50Ms: "45.76 ms",
        p95Ms: "79.50 ms",
        gate: "BASELINE",
      },
      {
        dataset: "nfcorpus",
        label: "BeIR / NFCorpus",
        task: "Biomedical nutrition retrieval",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3110",
        secondaryMetrics: "Recall@5 = 0.1205 · MRR = 0.5211 · MAP = 0.1294",
        p50Ms: "3.32 ms",
        p95Ms: "15.03 ms",
        gate: "BASELINE",
      },
      {
        dataset: "arguana",
        label: "BeIR / ArguAna",
        task: "Counter-argument passage matching",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3451",
        secondaryMetrics:
          "Recall@5 = 0.5275 · Recall@10 = 0.7216 · MRR = 0.2349",
        p50Ms: "567.83 ms",
        p95Ms: "1043.33 ms",
        gate: "BASELINE",
      },
      {
        dataset: "locomo",
        label: "LoCoMo",
        task: "Long-horizon conversational memory QA",
        primaryMetricName: "Fact Recall",
        primaryMetricValue: "0.2049",
        secondaryMetrics: "Token F1 = 0.0383 · Avg 92.3 context tokens",
        p50Ms: "16.02 ms",
        p95Ms: "28.31 ms",
        gate: "BASELINE",
      },
    ],
  },
];

export const LOCOMO_CATEGORY_BREAKDOWN = [
  {
    category: "single_hop",
    count: 841,
    factRecall: "0.1011",
    tokenF1: "0.0712",
  },
  {
    category: "adversarial",
    count: 446,
    factRecall: "0.1009",
    tokenF1: "0.0643",
  },
  { category: "temporal", count: 321, factRecall: "0.0218", tokenF1: "0.0470" },
  {
    category: "open_domain",
    count: 96,
    factRecall: "0.0208",
    tokenF1: "0.0342",
  },
  {
    category: "multi_hop",
    count: 282,
    factRecall: "0.0071",
    tokenF1: "0.0307",
  },
] as const;
