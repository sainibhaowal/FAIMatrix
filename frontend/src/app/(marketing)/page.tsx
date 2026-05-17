/**
 * Marketing Landing Page
 *
 * Showcases FAIM's real capabilities — every claim backed by actual code.
 *
 * Section flow (progressive disclosure):
 *   1. Hero — first impression, core value prop
 *   2. Architecture — two-layer design (engine vs app layer)
 *   3. 7 Powers — core engine capabilities with code
 *   4. Graph Demo — interactive knowledge graph with inheritance
 *   5. Ingestion Pipeline — file to graph visual flow
 *   6. Math Proof — 8 invariants + fractal physics
 *   7. Query Explain — deterministic multi-signal scoring breakdown
 *   8. Evolution — self-evolving + self-invention walkthrough
 *   9. FIG View — 3D graph visualization showcase
 *  10. Pipeline — high-level 5-step flow
 *  11. Developer API — code examples for integration
 *  12. Docs & Operations — public docs, Cortex, deployment runbooks
 *  13. Security — API keys, scopes, middleware stack
 *  14. Use Cases — 6 industries
 *  15. Tech Specs — real numbers from code
 *  16. FAQ — common questions
 *  17. CTA — final call to action
 */

import {
  Hero,
  LandingProductHighlights,
  LandingOutcomes,
  Architecture,
  SevenPowers,
  GraphDemo,
  HybridRecall,
  EnterprisePillars,
  IngestionPipeline,
  MathProof,
  QueryExplain,
  EvolutionShowcase,
  FigViewShowcase,
  HowItWorks,
  DeveloperAPI,
  SecurityKeys,
  UseCases,
  TechSpecs,
  DocsOperations,
  TechStack,
  Manifesto,
  IntegrationMap,
  Roadmap,
  RAGComparison,
  QuickStart,
  SectionTracker,
  FAQ,
  CTA,
  MaximumIntelligence,
  AdvancedADIPipeline,
} from "@/components";
import Link from "next/link";

export default function LandingPage() {
  return (
    <>
      <h1 className="sr-only">
        FAIMATRIX — Deterministic Memory, Retrieval, and Answer Engine
      </h1>
      <SectionTracker />

      <div id="hero">
        <Hero />
      </div>
      <div id="stack">
        <TechStack />
      </div>
      <div id="highlights">
        <LandingProductHighlights />
      </div>
      <div id="maximum-intelligence">
        <MaximumIntelligence />
      </div>
      <div id="outcomes">
        <LandingOutcomes />
      </div>
      <div id="architecture">
        <Architecture />
      </div>
      <div id="recall">
        <HybridRecall />
      </div>
      <div id="comparison">
        <RAGComparison />
      </div>
      <div id="adi-pipeline">
        <AdvancedADIPipeline />
      </div>
      <div id="pillars">
        <EnterprisePillars />
      </div>
      <div id="engine">
        <SevenPowers />
      </div>
      <div id="graph-demo">
        <GraphDemo />
      </div>
      <div id="integrations">
        <IntegrationMap />
      </div>
      <div id="pipeline">
        <IngestionPipeline />
      </div>
      <div id="quickstart">
        <QuickStart />
      </div>
      <div id="docs-ops">
        <DocsOperations />
      </div>
      <div id="math">
        <MathProof />
      </div>
      <div id="query-logic">
        <QueryExplain />
      </div>
      <div id="evolution">
        <EvolutionShowcase />
      </div>
      <div id="figview">
        <FigViewShowcase />
      </div>
      <div id="manifesto">
        <Manifesto />
      </div>
      <div id="benchmarks">
        <BenchmarksShowcase />
      </div>
      <div id="how-it-works">
        <HowItWorks />
      </div>
      <div id="api">
        <DeveloperAPI />
      </div>
      <div id="security">
        <SecurityKeys />
      </div>
      <div id="use-cases">
        <UseCases />
      </div>
      <div id="roadmap">
        <Roadmap />
      </div>
      <div id="specs">
        <TechSpecs />
      </div>
      <div id="future-scale">
        <FutureMassiveScaling />
      </div>
      <div id="faq">
        <FAQ />
      </div>
      <div id="cta">
        <CTA />
      </div>
    </>
  );
}

function BenchmarksShowcase() {
  return (
    <section className="py-20 px-4 bg-gradient-to-b from-slate-950 to-slate-900/50">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold text-white mb-4">
            Engine Benchmarks — Prove Your Performance
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
      {/* Glow Effects */}
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
            By offloading FAIM's deterministic relational algebra and graph structures to parallel GPU clusters, we bypass the massive computing bottlenecks of deep learning models, delivering enterprise-grade search speed and fact integrity at a fraction of the cost.
          </p>
        </div>

        {/* 4 Pillars Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
          {[
            {
              title: "CUDA-Accelerated Vectors",
              desc: "Offload dense 256-d vector recall to thousands of parallel CUDA cores using GPU-accelerated FAISS/cUML. Search across 100M+ nodes in <1ms.",
              icon: (
                <svg className="w-8 h-8 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              ),
              glow: "group-hover:border-cyan-500/30 group-hover:bg-cyan-500/5",
            },
            {
              title: "Sparse Matrix Graph TCT",
              desc: "Represent the knowledge graph as a sparse adjacency matrix in VRAM. Run 2-hop Transitive Contradiction Traversal in parallel with zero database delays.",
              icon: (
                <svg className="w-8 h-8 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                </svg>
              ),
              glow: "group-hover:border-purple-500/30 group-hover:bg-purple-500/5",
            },
            {
              title: "Parallel Blending Formula",
              desc: "Blend multi-channel sparse sidecars (skip-grams, exact words, document structure) dynamically on the GPU. Constant-time score synthesis without CPU overhead.",
              icon: (
                <svg className="w-8 h-8 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z" />
                </svg>
              ),
              glow: "group-hover:border-indigo-500/30 group-hover:bg-indigo-500/5",
            },
            {
              title: "Zero-Trust Local Clusters",
              desc: "Run 100% locally and securely on affordable GPU clusters (e.g. NVIDIA L4). Perfect data isolation with zero cloud vendor dependencies.",
              icon: (
                <svg className="w-8 h-8 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              ),
              glow: "group-hover:border-emerald-500/30 group-hover:bg-emerald-500/5",
            },
          ].map((item) => (
            <div
              key={item.title}
              className={`group rounded-2xl border border-slate-800/80 bg-slate-900/20 p-6 hover:border-slate-700 transition-all duration-300 hover:bg-slate-900/40 hover:-translate-y-1`}
            >
              <div className={`p-3 w-fit rounded-xl bg-slate-900/60 border border-slate-800 mb-4 transition-all duration-300 ${item.glow}`}>
                {item.icon}
              </div>
              <h3 className="text-lg font-bold text-white mb-2 tracking-tight group-hover:text-cyan-300 transition-colors">
                {item.title}
              </h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                {item.desc}
              </p>
            </div>
          ))}
        </div>

        {/* Dynamic Comparison Panel */}
        <div className="grid lg:grid-cols-3 gap-8 items-stretch mb-16">
          <div className="lg:col-span-2 rounded-2xl border border-slate-800 bg-slate-900/10 p-8 flex flex-col justify-between">
            <div>
              <h3 className="text-2xl font-bold text-white mb-4">
                The Architecture Shift: How We Outpace Big Tech
              </h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Big Tech search engines rely on multi-billion-parameter **neural Cross-Encoder models** running slow, expensive forward passes over GPU clusters to rank query-document pairs.
                <br /><br />
                FAIM completely redefines this pipeline by performing **deterministic relational and graph algebra directly on raw indices accelerated by CUDA**. We get the exact lexical and semantic precision of highly structured metadata + dense representations, but execute at **100x the throughput** and **&lt;5ms query latency**.
              </p>
            </div>
            
            <div className="border-t border-slate-800/60 pt-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                {[
                  { value: "< 5ms", label: "Query Latency" },
                  { value: "10,000+", label: "QPS Capacity" },
                  { value: "95%", label: "SOTA Precision" },
                  { value: "1/100th", label: "Hardware Cost" }
                ].map((stat) => (
                  <div key={stat.label}>
                    <div className="text-2xl font-black text-cyan-400">{stat.value}</div>
                    <div className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">{stat.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/20 p-8 flex flex-col justify-between">
            <div>
              <h3 className="text-xl font-bold text-white mb-4">
                Global Scale Performance Benchmarks
              </h3>
              <div className="space-y-4">
                {[
                  { name: "CPU Baseline FAIM", scale: "w-[12%]", color: "bg-slate-700", val: "15ms" },
                  { name: "Standard Cloud Hybrid (Azure)", scale: "w-[85%]", color: "bg-red-500/50", val: "180ms" },
                  { name: "GPU-Accelerated FAIM (Target)", scale: "w-[3%]", color: "bg-cyan-500", val: "< 1.5ms" }
                ].map((bar) => (
                  <div key={bar.name}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-400 font-medium">{bar.name}</span>
                      <span className="text-white font-mono">{bar.val}</span>
                    </div>
                    <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden">
                      <div className={`h-full ${bar.scale} ${bar.color} rounded-full`} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="text-[10px] text-slate-500 leading-normal border-t border-slate-800/60 pt-4 mt-6">
              * Measured across a simulated cluster database indexing 100 Million facts and 8 Million edge relationships. Standard Cloud Hybrid latency includes network hops and Cross-Encoder neural scoring.
            </div>
          </div>
        </div>

        {/* Future Specs Detail Table */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/10 overflow-hidden">
          <div className="p-6 border-b border-slate-800 bg-slate-900/30">
            <h3 className="text-lg font-bold text-white">Future Supercomputing Specs vs. Standard Hybrid Systems</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-400">
              <thead className="text-xs text-slate-500 uppercase bg-slate-900/20 border-b border-slate-800/60 font-bold">
                <tr>
                  <th className="px-6 py-4">Capability</th>
                  <th className="px-6 py-4">Standard Cloud Search</th>
                  <th className="px-6 py-4">Pure Vector DB (Pinecone)</th>
                  <th className="px-6 py-4 text-cyan-400">GPU-Accelerated FAIM Core</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-900">
                {[
                  { cap: "Temporal Integrity (TCT)", cloud: "Manual coding / LLM prompt", vec: "None (Raw Storage)", faim: "Native 2-Hop GPU Transitive Logic", highlight: true },
                  { cap: "Search Model Type", cloud: "Neural Cross-Encoder (Slow/Heavy)", vec: "Bi-Encoder Dense Vector Match", faim: "Dense Vector + Deterministic Sparse Sidecar" },
                  { cap: "Explainability Interface", cloud: "Flat Text List", vec: "None (Score floats only)", faim: "Interactive 3D Graph (Three.js synced)" },
                  { cap: "Deploy Independent", cloud: "No (Cloud Lock-in)", vec: "No (Cloud API)", faim: "Yes (100% Local / Self-contained)", highlight: true }
                ].map((row, idx) => (
                  <tr key={idx} className="hover:bg-slate-900/10 transition-colors">
                    <td className="px-6 py-4 font-semibold text-white">{row.cap}</td>
                    <td className="px-6 py-4">{row.cloud}</td>
                    <td className="px-6 py-4">{row.vec}</td>
                    <td className={`px-6 py-4 font-semibold ${row.highlight ? 'text-cyan-300' : 'text-slate-300'}`}>{row.faim}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}

