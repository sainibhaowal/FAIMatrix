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
 *  12. Security — API keys, scopes, middleware stack
 *  13. Use Cases — 6 industries
 *  14. Tech Specs — real numbers from code
 *  15. FAQ — common questions
 *  16. CTA — final call to action
 */

import {
  Hero,
  Architecture,
  SevenPowers,
  GraphDemo,
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
  FAQ,
  CTA,
} from "@/components";

export default function LandingPage() {
  return (
    <>
      <h1 className="sr-only">
        FAIMATRIX — Deterministic Memory, Retrieval, and Answer Engine
      </h1>
      <Hero />
      <Architecture />
      <SevenPowers />
      <GraphDemo />
      <IngestionPipeline />
      <MathProof />
      <QueryExplain />
      <EvolutionShowcase />
      <FigViewShowcase />
      <HowItWorks />
      <DeveloperAPI />
      <SecurityKeys />
      <UseCases />
      <TechSpecs />
      <FAQ />
      <CTA />
    </>
  );
}
