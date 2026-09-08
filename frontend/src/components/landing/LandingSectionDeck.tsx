"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import {
  BrainCircuit,
  Gauge,
  Network,
  ScanSearch,
  TerminalSquare,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";

import {
  Architecture,
  AdvancedADIPipeline,
  DeveloperAPI,
  DocsOperations,
  EnterprisePillars,
  EvolutionShowcase,
  FAQ,
  FigViewShowcase,
  GraphDemo,
  HowItWorks,
  HybridRecall,
  IngestionPipeline,
  IntegrationMap,
  LandingOutcomes,
  LandingProductHighlights,
  Manifesto,
  MathProof,
  MaximumIntelligence,
  QuickStart,
  QueryExplain,
  RAGComparison,
  Roadmap,
  SecurityKeys,
  SevenPowers,
  TechSpecs,
  TechStack,
  UseCases,
  CTA,
} from "@/components";

type TabItem = {
  key: string;
  label: string;
  summary: string;
  node: ReactNode;
};

type DeckGroup = {
  id: string;
  number: string;
  icon: LucideIcon;
  accent: string;
  eyebrow: string;
  title: string;
  summary: string;
  tabs: TabItem[];
};

function BenchmarksShowcase() {
  return (
    <section className="py-20 px-4 bg-gradient-to-b from-slate-950 to-slate-900/50">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold text-white mb-4">
            Engine Benchmarks - Prove Your Performance
          </h2>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto">
            FAIM includes a state-of-the-art, real-time benchmarking system. No
            synthetic metrics. No hardcoded numbers. Every measurement is live
            from your graph, infrastructure, and actual stress tests.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {[
            {
              title: "Golden Signals",
              desc: "Google SRE's Four Golden Signals: latency (p50/p95/p99), traffic (req/sec), errors, saturation (CPU/memory/DB).",
              icon: "📊",
            },
            {
              title: "Stress Testing",
              desc: "Progressive load testing from 1 to 10 concurrent streams. Measures throughput, latency, and saturation point.",
              icon: "⚡",
            },
            {
              title: "Anomaly Alerts",
              desc: "9 rule-based alert conditions: latency spikes, memory pressure, error rates, invariant violations.",
              icon: "🚨",
            },
            {
              title: "Series Trending",
              desc: "Historical benchmark runs stored and compared. Detect performance regressions before production impact.",
              icon: "📈",
            },
            {
              title: "Live Metrics",
              desc: "Real infrastructure data: Docker cgroup limits, PostgreSQL connections, Redis hit rates, graph invariants.",
              icon: "🔍",
            },
            {
              title: "Exportable Reports",
              desc: "Download complete JSON reports with SHA-256 integrity hashes for audits and compliance.",
              icon: "📋",
            },
          ].map((item) => (
            <div
              key={item.title}
              className="rounded-2xl border border-slate-700/50 bg-slate-900/40 p-6 hover:border-slate-600/50 transition-all hover:bg-slate-900/60"
            >
              <div className="text-3xl mb-3">{item.icon}</div>
              <h3 className="text-lg font-semibold text-white mb-2">
                {item.title}
              </h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                {item.desc}
              </p>
            </div>
          ))}
        </div>

        <div className="rounded-2xl border border-slate-700/50 bg-slate-900/30 p-8">
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <h3 className="text-xl font-semibold text-white mb-4">
                Why Benchmarks Matter
              </h3>
              <ul className="space-y-3 text-slate-400">
                {[
                  "Verify performance claims with real data, not estimates",
                  "Detect regressions early before they reach production",
                  "Monitor graph health continuously across 9 dimensions",
                  "Prove deterministic, stable performance for compliance",
                  "Export audit trails with cryptographic integrity",
                ].map((item) => (
                  <li key={item} className="flex gap-3">
                    <span className="text-cyan-400 shrink-0">✓</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-xl font-semibold text-white mb-4">
                Access Benchmarks
              </h3>
              <ol className="space-y-3 text-slate-400 text-sm mb-6">
                {[
                  "Sign in to your FAIM dashboard",
                  "Navigate to Benchmarks tab",
                  "Click 'Run Benchmark' to measure BM-1–BM-9 suite",
                  "Click 'Stress Test' for progressive load testing",
                  "View Golden Signals, Alerts, and historical trends",
                  "Export complete reports with one click",
                ].map((step, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="text-slate-500 font-mono text-xs shrink-0 w-6">
                      {i + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
              <Link
                href="/benchmarks"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20 transition-all font-medium"
              >
                Learn More →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function FutureMassiveScaling() {
  return (
    <section className="py-24 px-4 bg-slate-950 border-t border-slate-900 relative overflow-hidden">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[500px] h-[500px] bg-cyan-500/10 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/3 w-[600px] h-[600px] bg-purple-500/5 blur-[150px] rounded-full pointer-events-none" />

      <div className="max-w-7xl mx-auto relative z-10">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-cyan-500/30 bg-cyan-500/5 text-cyan-300 text-xs font-semibold uppercase tracking-wider mb-4 animate-pulse">
            Future Architecture Roadmap
          </div>
          <h2 className="text-4xl md:text-5xl font-black text-white tracking-tight mb-6 bg-gradient-to-r from-white via-cyan-200 to-purple-300 bg-clip-text text-transparent">
            FAIM at Massive Scale: The GPU-Accelerated Cognitive Core
          </h2>
          <p className="text-lg text-slate-400 max-w-3xl mx-auto leading-relaxed">
            By offloading FAIM's deterministic relational algebra and graph
            structures to parallel GPU clusters, we bypass the massive computing
            bottlenecks of deep learning models, delivering enterprise-grade
            search speed and fact integrity at a fraction of the cost.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
          {[
            {
              title: "CUDA-Accelerated Vectors",
              desc: "Offload dense 256-d vector recall to thousands of parallel CUDA cores using GPU-accelerated FAISS/cUML. Search across 100M+ nodes in <1ms.",
            },
            {
              title: "Sparse Matrix Graph TCT",
              desc: "Represent the knowledge graph as a sparse adjacency matrix in VRAM. Run 2-hop Transitive Contradiction Traversal in parallel with zero database delays.",
            },
            {
              title: "Parallel Blending Formula",
              desc: "Blend multi-channel sparse sidecars (skip-grams, exact words, document structure) dynamically on the GPU. Constant-time score synthesis without CPU overhead.",
            },
            {
              title: "Zero-Trust Local Clusters",
              desc: "Run 100% locally and securely on affordable GPU clusters (e.g. NVIDIA L4). Perfect data isolation with zero cloud vendor dependencies.",
            },
          ].map((item) => (
            <div
              key={item.title}
              className="group rounded-2xl border border-slate-800/80 bg-slate-900/20 p-6 hover:border-slate-700 transition-all duration-300 hover:bg-slate-900/40 hover:-translate-y-1"
            >
              <h3 className="text-lg font-bold text-white mb-2 tracking-tight group-hover:text-cyan-300 transition-colors">
                {item.title}
              </h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                {item.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

const GROUPS: DeckGroup[] = [
  {
    id: "core",
    number: "01",
    icon: BrainCircuit,
    accent: "#22d3ee",
    eyebrow: "Core Story",
    title: "Compact product story",
    summary:
      "The fastest read on what FAIM is, how it thinks, and why the memory stack is different.",
    tabs: [
      {
        key: "stack",
        label: "Tech Stack",
        summary: "What FAIM is built on.",
        node: <TechStack />,
      },
      {
        key: "highlights",
        label: "Highlights",
        summary: "Main shipped capabilities.",
        node: <LandingProductHighlights />,
      },
      {
        key: "maximum",
        label: "Maximum Intelligence",
        summary: "High-level positioning.",
        node: <MaximumIntelligence />,
      },
      {
        key: "outcomes",
        label: "Outcomes",
        summary: "Why teams adopt it.",
        node: <LandingOutcomes />,
      },
    ],
  },
  {
    id: "platform",
    number: "02",
    icon: Network,
    accent: "#a78bfa",
    eyebrow: "Platform Shape",
    title: "How the engine is organized",
    summary:
      "Architecture, recall, retrieval comparison, and core power surfaces stay visible but no longer stretch the whole page.",
    tabs: [
      {
        key: "architecture",
        label: "Architecture",
        summary: "Engine versus app layer.",
        node: <Architecture />,
      },
      {
        key: "recall",
        label: "Hybrid Recall",
        summary: "Dense plus graph-aware recall.",
        node: <HybridRecall />,
      },
      {
        key: "comparison",
        label: "Systems Comparison",
        summary: "Source-backed capability matrix across memory and retrieval systems.",
        node: <RAGComparison />,
      },
      {
        key: "adi",
        label: "ADI Pipeline",
        summary: "Deterministic end-to-end pipeline.",
        node: <AdvancedADIPipeline />,
      },
      {
        key: "pillars",
        label: "Pillars",
        summary: "Enterprise pillars and guarantees.",
        node: <EnterprisePillars />,
      },
      {
        key: "engine",
        label: "7 Powers",
        summary: "Core engine powers.",
        node: <SevenPowers />,
      },
    ],
  },
  {
    id: "proof",
    number: "03",
    icon: ScanSearch,
    accent: "#f472b6",
    eyebrow: "Proof Layer",
    title: "Retrieval, reasoning, and FIG proof",
    summary:
      "This block contains the visual proof surfaces and the reasoning path that users can inspect.",
    tabs: [
      {
        key: "graph",
        label: "Graph Demo",
        summary: "Interactive knowledge graph.",
        node: <GraphDemo />,
      },
      {
        key: "integration",
        label: "Integration",
        summary: "How query and graph state connect.",
        node: <IntegrationMap />,
      },
      {
        key: "ingestion",
        label: "Ingestion",
        summary: "File-to-graph flow.",
        node: <IngestionPipeline />,
      },
      {
        key: "quickstart",
        label: "Quick Start",
        summary: "Get running fast.",
        node: <QuickStart />,
      },
      {
        key: "math",
        label: "Math Proof",
        summary: "8 invariants and proof layer.",
        node: <MathProof />,
      },
      {
        key: "query",
        label: "Query Explain",
        summary: "Deterministic score breakdown.",
        node: <QueryExplain />,
      },
      {
        key: "evolution",
        label: "Evolution",
        summary: "Self-invent and evolve walkthrough.",
        node: <EvolutionShowcase />,
      },
      {
        key: "fig",
        label: "FIG View",
        summary: "3D proof and pulse visualization.",
        node: <FigViewShowcase />,
      },
      {
        key: "manifesto",
        label: "Manifesto",
        summary: "Platform principles.",
        node: <Manifesto />,
      },
      {
        key: "benchmarks",
        label: "Benchmarks",
        summary: "What the engine measures.",
        node: <BenchmarksShowcase />,
      },
    ],
  },
  {
    id: "ops",
    number: "04",
    icon: TerminalSquare,
    accent: "#34d399",
    eyebrow: "Operations",
    title: "Docs, APIs, and operator surfaces",
    summary:
      "A single place for how to operate, integrate, and support the product without adding page length.",
    tabs: [
      {
        key: "how",
        label: "How it Works",
        summary: "One compact pipeline view.",
        node: <HowItWorks />,
      },
      {
        key: "docs",
        label: "Docs & Ops",
        summary: "Operational docs and runbooks.",
        node: <DocsOperations />,
      },
      {
        key: "api",
        label: "Developer API",
        summary: "Integration surface.",
        node: <DeveloperAPI />,
      },
      {
        key: "security",
        label: "Security",
        summary: "API keys and scopes.",
        node: <SecurityKeys />,
      },
      {
        key: "use-cases",
        label: "Use Cases",
        summary: "Industries and workflows.",
        node: <UseCases />,
      },
    ],
  },
  {
    id: "scale",
    number: "05",
    icon: Gauge,
    accent: "#fbbf24",
    eyebrow: "Scale & Finish",
    title: "The long tail and final call to action",
    summary:
      "Roadmap, specs, the heavy-scale vision, FAQ, and CTA stay available but tucked behind compact toggles.",
    tabs: [
      {
        key: "roadmap",
        label: "Roadmap",
        summary: "What’s next.",
        node: <Roadmap />,
      },
      {
        key: "specs",
        label: "Tech Specs",
        summary: "Real numbers and runtime facts.",
        node: <TechSpecs />,
      },
      {
        key: "future",
        label: "Future Scale",
        summary: "GPU-accelerated roadmap.",
        node: <FutureMassiveScaling />,
      },
      { key: "faq", label: "FAQ", summary: "Common questions.", node: <FAQ /> },
      {
        key: "cta",
        label: "CTA",
        summary: "Final call to action.",
        node: <CTA />,
      },
    ],
  },
];

export default function LandingSectionDeck() {
  const [activeGroupId, setActiveGroupId] = useState(GROUPS[0].id);
  const [activeTabs, setActiveTabs] = useState<Record<string, string>>(() =>
    Object.fromEntries(GROUPS.map((group) => [group.id, group.tabs[0].key])),
  );

  useEffect(() => {
    const syncFromHash = () => {
      const [requested, requestedTab] = window.location.hash.slice(1).split("/");
      if (GROUPS.some((group) => group.id === requested)) {
        setActiveGroupId(requested);
        const group = GROUPS.find((candidate) => candidate.id === requested);
        if (group && requestedTab && group.tabs.some((tab) => tab.key === requestedTab)) {
          setActiveTabs((current) => ({ ...current, [requested]: requestedTab }));
        }
      }
    };

    syncFromHash();
    window.addEventListener("hashchange", syncFromHash);
    return () => window.removeEventListener("hashchange", syncFromHash);
  }, []);

  const activeGroup = useMemo(
    () => GROUPS.find((group) => group.id === activeGroupId) ?? GROUPS[0],
    [activeGroupId],
  );
  const activeTab = useMemo(() => {
    const key = activeTabs[activeGroup.id];
    return (
      activeGroup.tabs.find((tab) => tab.key === key) ?? activeGroup.tabs[0]
    );
  }, [activeGroup, activeTabs]);

  const selectGroup = (groupId: string) => {
    setActiveGroupId(groupId);
    window.history.replaceState(null, "", `#${groupId}`);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  };

  return (
    <section
      id="atlas"
      className="faim-atlas-deck relative flex h-[calc(100svh-2rem)] min-h-[620px] scroll-mt-6 flex-col overflow-hidden px-2 pb-2 pt-3 sm:px-3 sm:pb-3 sm:pt-3"
    >
      {GROUPS.map((group) => (
        <span
          key={group.id}
          id={group.id}
          className="pointer-events-none absolute left-0 top-0 scroll-mt-20"
          aria-hidden="true"
        />
      ))}

      <div className="relative mx-auto flex min-h-0 w-full max-w-[1440px] flex-1 flex-col">
        <div className="min-h-0 flex-1 overflow-hidden">
          <div className="h-full min-h-0 flex flex-col">
            <div className="flex h-full min-h-0 min-w-0 flex-col">
                  <div className="faim-atlas-preview-scroll relative min-h-0 flex-1 overflow-y-auto overscroll-contain">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={`${activeGroup.id}-${activeTab.key}`}
                    initial={{ opacity: 0, y: 14, filter: "blur(4px)" }}
                    animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                    exit={{ opacity: 0, y: -8, filter: "blur(3px)" }}
                    transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
                    className="faim-atlas-preview overflow-hidden"
                  >
                    {activeTab.node}
                  </motion.div>
                </AnimatePresence>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
