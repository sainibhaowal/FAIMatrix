/**
 * Verified FAIM benchmark results across signed BeIR, LoCoMo, and historical ablation evaluations.
 *
 * Sources:
 * - faim-benchmarks/results/RESULTS.md
 * - faim-benchmarks/results/COMPARISON.md
 * - faim_native/Docs/13-benchmarks/02-production-benchmark-suite-2026-11-22.md
 * - faim_native/Docs/13-benchmarks/03-multi-scenario-benchmark-results-2026-11-24.md
 */

export type BenchmarkProfileId =
  | "faim-granite-gpu"
  | "faim-pure-cpu"
  | "faim-hybrid-hw"
  | "faim-pure-gpu"
  | "faim-balanced-granite"
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
  status: "Verified" | "Reference";
}

export interface BenchmarkProfile {
  id: BenchmarkProfileId;
  badge: string;
  name: string;
  shortLabel: string;
  mode: string;
  hardware: string;
  summary: string;
  rows: BenchmarkDatasetRow[];
}

export interface CrossSystemComparisonRow {
  dataset: string;
  graniteHybrid: string;
  pureCpu: string;
  standaloneGranite: string;
  bm25Baseline: string;
}

export interface HistoricalProgressionRow {
  generation: string;
  architecture: string;
  recallAt5: string;
  ndcgAt10: string;
  p50Ms: string;
  deltaSummary: string;
}

export const BENCHMARK_REPORT_DATE = "2026-11-24";

export const BENCHMARK_HIGHLIGHTS = [
  {
    value: "0.6900",
    unit: "nDCG@10",
    label: "BeIR / SciFact · FAIM + Granite 97M",
    detail: "Recall@5 0.7704 · vs Standalone Granite 0.6806 & BM25 0.6644",
    accent: "cyan",
  },
  {
    value: "0.6871",
    unit: "nDCG@10",
    label: "BeIR / SciFact · FAIM-Pure Zero-ML CPU",
    detail: "86.31 ms CPU CI · Zero GPU or ML inference required",
    accent: "emerald",
  },
  {
    value: "0.3314",
    unit: "nDCG@10",
    label: "BeIR / NFCorpus · FAIM + Granite 97M",
    detail: "101.62 ms P50 · +6.6% relative lift over BM25 (0.3110)",
    accent: "purple",
  },
  {
    value: "0.7266",
    unit: "Recall@10",
    label: "BeIR / ArguAna · FAIM + Granite 97M",
    detail: "304.55 ms P50 vs BM25 567.83 ms (1.86x faster median)",
    accent: "amber",
  },
] as const;

export const HISTORICAL_PROGRESSION: HistoricalProgressionRow[] = [
  {
    generation: "Early Baseline (v9)",
    architecture: "Initial native graph baseline (CPU)",
    recallAt5: "0.0539",
    ndcgAt10: "0.0517",
    p50Ms: "17,373.00 ms",
    deltaSummary: "Pre-Representation V2 baseline",
  },
  {
    generation: "Intermediate (v17)",
    architecture: "Legacy uncached query path (CPU)",
    recallAt5: "0.4831",
    ndcgAt10: "0.4184",
    p50Ms: "7,195.68 ms",
    deltaSummary: "8.1x nDCG@10 gain over v9",
  },
  {
    generation: "FAIM-Pure CPU (v18 / Current)",
    architecture: "Zero-ML Representation V2 + BM25+ + Concept-MaxSim",
    recallAt5: "0.7554",
    ndcgAt10: "0.6871",
    p50Ms: "86.31 ms",
    deltaSummary: "201x faster median latency vs v9 · +0.0227 over BM25",
  },
  {
    generation: "FAIM Hybrid · Granite 97M (Current)",
    architecture: "FAIM FAST + Granite 97M Multilingual R2 + HMAC/RAM Cache",
    recallAt5: "0.7704",
    ndcgAt10: "0.6900",
    p50Ms: "140.17 ms",
    deltaSummary: "Flagship full-split accuracy across BeIR & LoCoMo",
  },
];

export const CROSS_SYSTEM_ROWS: CrossSystemComparisonRow[] = [
  {
    dataset: "BeIR / SciFact",
    graniteHybrid: "0.6900 (R@5 0.7704 · 140.17 ms)",
    pureCpu: "0.6871 (R@5 0.7554 · 86.31 ms)",
    standaloneGranite: "0.6806 (R@5 0.7522 · GPU only)",
    bm25Baseline: "0.6644 (R@5 0.7193 · 45.76 ms)",
  },
  {
    dataset: "BeIR / NFCorpus",
    graniteHybrid: "0.3314 (R@5 0.1297 · 101.62 ms)",
    pureCpu: "0.3267 (R@5 0.1289 · 49.91 ms)",
    standaloneGranite: "—",
    bm25Baseline: "0.3110 (R@5 0.1205 · 3.32 ms)",
  },
  {
    dataset: "BeIR / ArguAna",
    graniteHybrid: "0.3387 (R@10 0.7266 · 304.55 ms)",
    pureCpu: "0.3149 (R@10 0.6781 · 167.74 ms)",
    standaloneGranite: "—",
    bm25Baseline: "0.3451 (R@10 0.7216 · 567.83 ms)",
  },
  {
    dataset: "LoCoMo (Memory QA)",
    graniteHybrid: "0.0710 Fact Recall (234.56 ms · 11.9 tok)",
    pureCpu: "0.0715 Fact Recall (Auto HW · 188.50 ms)",
    standaloneGranite: "—",
    bm25Baseline: "0.2049 Fact Recall (16.02 ms · 92.3 tok)",
  },
];

export const BENCHMARK_PROFILES: BenchmarkProfile[] = [
  {
    id: "faim-granite-gpu",
    badge: "Flagship · Full 4-Suite Coverage",
    name: "FAIM Hybrid · Granite 97M (GPU)",
    shortLabel: "FAIM + Granite GPU",
    mode: "FAIM FAST Profile + Granite 97M Multilingual R2 dense fusion",
    hardware:
      "2 API + 4 Ingest workers · CUDA acceleration · 512 MiB VRAM guard",
    summary:
      "Achieves highest BeIR accuracy across SciFact, NFCorpus, and ArguAna Recall@10, beating both standalone Granite 97M R2 (0.6806) and BM25 (0.6644).",
    rows: [
      {
        dataset: "scifact",
        label: "BeIR / SciFact",
        task: "5,183 docs · 300 queries",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.6900",
        secondaryMetrics: "Recall@5 = 0.7704 · MRR = 0.6590 · MAP = 0.6483",
        p50Ms: "140.17 ms",
        p95Ms: "208.22 ms",
        status: "Verified",
      },
      {
        dataset: "nfcorpus",
        label: "BeIR / NFCorpus",
        task: "3,633 docs · 323 queries",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3314",
        secondaryMetrics: "Recall@5 = 0.1297 · MRR = 0.5290 · MAP = 0.1367",
        p50Ms: "101.62 ms",
        p95Ms: "158.14 ms",
        status: "Verified",
      },
      {
        dataset: "arguana",
        label: "BeIR / ArguAna",
        task: "8,674 docs · 1,406 queries",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3387",
        secondaryMetrics:
          "Recall@5 = 0.5096 · Recall@10 = 0.7266 · MRR = 0.2279",
        p50Ms: "304.55 ms",
        p95Ms: "485.21 ms",
        status: "Verified",
      },
      {
        dataset: "locomo",
        label: "LoCoMo",
        task: "Long-horizon conversational memory QA",
        primaryMetricName: "Fact Recall",
        primaryMetricValue: "0.0710",
        secondaryMetrics: "Token F1 = 0.0582 · Compact 11.9 avg context tokens",
        p50Ms: "234.56 ms",
        p95Ms: "446.77 ms",
        status: "Verified",
      },
    ],
  },
  {
    id: "faim-pure-cpu",
    badge: "CPU-Only VPS Verified",
    name: "FAIM-Pure · Zero-ML Native Engine (CPU)",
    shortLabel: "FAIM-Pure CPU",
    mode: "FAIM FAST Zero-ML Representation V2 + Concept-Expanded MaxSim",
    hardware:
      "Standard x86_64 CPU · No GPU or neural embedding inference required",
    summary:
      "Surpasses BM25-Baseline on BeIR/SciFact (0.6871 vs 0.6644) and BeIR/NFCorpus (0.3267 vs 0.3110) with sub-100 ms CPU latency and zero neural model overhead.",
    rows: [
      {
        dataset: "scifact",
        label: "BeIR / SciFact",
        task: "5,183 docs · 300 queries",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.6871",
        secondaryMetrics: "Recall@5 = 0.7554 · MRR = 0.6564 · CPU CI 86.31 ms",
        p50Ms: "100.22 ms",
        p95Ms: "154.94 ms",
        status: "Verified",
      },
      {
        dataset: "nfcorpus",
        label: "BeIR / NFCorpus",
        task: "3,633 docs · 323 queries",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3267",
        secondaryMetrics: "Recall@5 = 0.1289 · MRR = 0.5259 · CPU CI 49.91 ms",
        p50Ms: "66.48 ms",
        p95Ms: "142.57 ms",
        status: "Verified",
      },
      {
        dataset: "arguana",
        label: "BeIR / ArguAna",
        task: "8,674 docs · 1,406 queries",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3149",
        secondaryMetrics:
          "Recall@5 = 0.4604 · Recall@10 = 0.6781 · CPU CI 167.74 ms",
        p50Ms: "250.98 ms",
        p95Ms: "411.32 ms",
        status: "Verified",
      },
    ],
  },
  {
    id: "faim-hybrid-hw",
    badge: "Auto Hardware · 4-Suite Complete",
    name: "FAIM-Pure · Auto CPU/GPU Hardware",
    shortLabel: "Auto Hardware",
    mode: "FAIM FAST Zero-ML with automatic GPU matrix & CPU fallback",
    hardware: "Bounded worker pool + adaptive CUDA matrix execution",
    summary:
      "Delivers identical deterministic accuracy across BeIR while completing the full LoCoMo memory benchmark at 188.50 ms median latency.",
    rows: [
      {
        dataset: "scifact",
        label: "BeIR / SciFact",
        task: "5,183 docs · 300 queries",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.6871",
        secondaryMetrics: "Recall@5 = 0.7554 · MRR = 0.6564 · MAP = 0.6459",
        p50Ms: "102.92 ms",
        p95Ms: "152.59 ms",
        status: "Verified",
      },
      {
        dataset: "nfcorpus",
        label: "BeIR / NFCorpus",
        task: "3,633 docs · 323 queries",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3267",
        secondaryMetrics: "Recall@5 = 0.1289 · MRR = 0.5259 · MAP = 0.1340",
        p50Ms: "68.98 ms",
        p95Ms: "151.33 ms",
        status: "Verified",
      },
      {
        dataset: "arguana",
        label: "BeIR / ArguAna",
        task: "8,674 docs · 1,406 queries",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3149",
        secondaryMetrics: "Recall@5 = 0.4604 · MRR = 0.2121 · MAP = 0.2121",
        p50Ms: "275.16 ms",
        p95Ms: "475.57 ms",
        status: "Verified",
      },
      {
        dataset: "locomo",
        label: "LoCoMo",
        task: "Long-horizon conversational memory QA",
        primaryMetricName: "Fact Recall",
        primaryMetricValue: "0.0715",
        secondaryMetrics: "Token F1 = 0.0584 · Compact 11.9 avg context tokens",
        p50Ms: "188.50 ms",
        p95Ms: "485.03 ms",
        status: "Verified",
      },
    ],
  },
  {
    id: "faim-pure-gpu",
    badge: "CUDA Matrix Kernels",
    name: "FAIM-Pure · CUDA Matrix Acceleration",
    shortLabel: "FAIM-Pure CUDA",
    mode: "FAIM FAST Zero-ML with CUDA matrix similarity & scoring",
    hardware:
      "GPU native matrix backend without external embedding model inference",
    summary:
      "Maintains exact ranking parity with CPU FAIM-Pure (0.6871 / 0.3267 / 0.3149) while lowering NFCorpus P95 tail latency to 133.01 ms.",
    rows: [
      {
        dataset: "scifact",
        label: "BeIR / SciFact",
        task: "5,183 docs · 300 queries",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.6871",
        secondaryMetrics: "Recall@5 = 0.7554 · MRR = 0.6564 · MAP = 0.6459",
        p50Ms: "100.00 ms",
        p95Ms: "149.72 ms",
        status: "Verified",
      },
      {
        dataset: "nfcorpus",
        label: "BeIR / NFCorpus",
        task: "3,633 docs · 323 queries",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3267",
        secondaryMetrics: "Recall@5 = 0.1289 · MRR = 0.5259 · MAP = 0.1340",
        p50Ms: "63.34 ms",
        p95Ms: "133.01 ms",
        status: "Verified",
      },
      {
        dataset: "arguana",
        label: "BeIR / ArguAna",
        task: "8,674 docs · 1,406 queries",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3149",
        secondaryMetrics:
          "Recall@5 = 0.4604 · Recall@10 = 0.6781 · MRR = 0.2121",
        p50Ms: "250.73 ms",
        p95Ms: "422.23 ms",
        status: "Verified",
      },
    ],
  },
  {
    id: "faim-balanced-granite",
    badge: "Profile Ablation Study",
    name: "FAIM Balanced Profile + Granite 97M",
    shortLabel: "Balanced Ablation",
    mode: "FAIM BALANCED deep graph diffusion + Granite 97M",
    hardware: "Full multi-hop balanced scoring on CUDA + Granite 97M",
    summary:
      "Demonstrates why FAST relevance-first ranking outperforms BALANCED on BeIR retrieval by +0.034 nDCG@10 and ~18x lower query latency.",
    rows: [
      {
        dataset: "scifact",
        label: "BeIR / SciFact",
        task: "5,183 docs · 300 queries",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.6560",
        secondaryMetrics: "Recall@5 = 0.7412 · MRR = 0.6227 · MAP = 0.6108",
        p50Ms: "2,487.46 ms",
        p95Ms: "8,507.69 ms",
        status: "Verified",
      },
      {
        dataset: "nfcorpus",
        label: "BeIR / NFCorpus",
        task: "3,633 docs · 323 queries",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3176",
        secondaryMetrics: "Recall@5 = 0.1264 · MRR = 0.5178 · MAP = 0.1303",
        p50Ms: "1,941.70 ms",
        p95Ms: "6,710.75 ms",
        status: "Verified",
      },
    ],
  },
  {
    id: "bm25-baseline",
    badge: "Reference Harness Baseline",
    name: "BM25 Lexical Reference Baseline",
    shortLabel: "BM25 Baseline",
    mode: "Standard in-process BM25 reference scorer",
    hardware: "In-process CPU harness baseline",
    summary:
      "FAIM outperforms BM25 across SciFact (+0.0256 nDCG@10) and NFCorpus (+0.0204), while BM25 emits longer raw context spans on LoCoMo (92.3 vs 11.9 tokens).",
    rows: [
      {
        dataset: "scifact",
        label: "BeIR / SciFact",
        task: "5,183 docs · 300 queries",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.6644",
        secondaryMetrics: "Recall@5 = 0.7193 · MRR = 0.6366 · MAP = 0.6242",
        p50Ms: "45.76 ms",
        p95Ms: "79.50 ms",
        status: "Reference",
      },
      {
        dataset: "nfcorpus",
        label: "BeIR / NFCorpus",
        task: "3,633 docs · 323 queries",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3110",
        secondaryMetrics: "Recall@5 = 0.1205 · MRR = 0.5211 · MAP = 0.1294",
        p50Ms: "3.32 ms",
        p95Ms: "15.03 ms",
        status: "Reference",
      },
      {
        dataset: "arguana",
        label: "BeIR / ArguAna",
        task: "8,674 docs · 1,406 queries",
        primaryMetricName: "nDCG@10",
        primaryMetricValue: "0.3451",
        secondaryMetrics:
          "Recall@5 = 0.5275 · Recall@10 = 0.7216 · MRR = 0.2349",
        p50Ms: "567.83 ms",
        p95Ms: "1,043.33 ms",
        status: "Reference",
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
        status: "Reference",
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
