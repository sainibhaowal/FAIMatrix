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
