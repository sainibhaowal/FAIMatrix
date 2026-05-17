"use client";

import { motion } from "framer-motion";
import { useState } from "react";

interface PipelineStage {
  id: string;
  title: string;
  subtitle: string;
  desc: string;
  math: string;
  specs: { label: string; value: string }[];
  accentColor: string;
  glow: string;
}

const STAGES: PipelineStage[] = [
  {
    id: "stage-1",
    title: "Stage 1: Sparse shortlist",
    subtitle: "Inverted Posting Lists & WAND Pruning",
    desc: "The query splits into Porter-stemmed and skip-gram tokens. Using a highly optimized inverted index, FAIM runs Block-Max WAND to compute dynamic score upper bounds, pruning non-matching node ranges in microseconds before vector execution.",
    math: "S_{sparse} = \\sum_{t \\in Q} \\text{WAND}(t, d)",
    specs: [
      { label: "Complexity", value: "Sublinear O(log N)" },
      { label: "Data Path", value: "PostgreSQL inverted_index" },
      { label: "Memory Cache", value: "Redis postings shortlist" },
      { label: "Pruning Rate", value: "> 92% candidates skipped" }
    ],
    accentColor: "text-cyan-400",
    glow: "border-cyan-500/20 bg-cyan-500/[0.03]"
  },
  {
    id: "stage-2",
    title: "Stage 2: Dense shortlist",
    subtitle: "Deterministic Vector HNSW & VP-Tree Scans",
    desc: "In parallel, the query's 256-dimensional native vector is checked against a deterministic HNSW index. Traditional HNSW entry levels are stochastic, but FAIM locks in absolute determinism using a stable hash value to map levels.",
    math: "\\text{Level}(D) = \\text{Hash}(\\text{node\\_id}) \\pmod{\\text{Max\\_Level}}",
    specs: [
      { label: "Index Type", value: "Stable-Hash Level HNSW" },
      { label: "Dimensions", value: "256-dim v_native" },
      { label: "Search Metric", value: "Cosine Distance (No-ML)" },
      { label: "Latency p95", value: "< 0.8ms" }
    ],
    accentColor: "text-purple-400",
    glow: "border-purple-500/20 bg-purple-500/[0.03]"
  },
  {
    id: "stage-3",
    title: "Stage 3: Graph diffusion",
    subtitle: "Decaying Path & PageRank Walks",
    desc: "Shortlisted candidates are expanded via adjacent graph edges (opposition, inheritance, KB citations). The engine walks up to 24 hops, distributing score multipliers that decay dynamically to prioritize localized neighborhood coherence.",
    math: "S_{graph} = \\sum_{p \\in \\text{Paths}} \\gamma^{\\text{length}} \\cdot \\prod_{e \\in p} W(e)",
    specs: [
      { label: "Traversal Depth", value: "Up to 24 hops" },
      { label: "Decay Factor", value: "0.85 per hop" },
      { label: "Expansion Limit", value: "24 neighbors max" },
      { label: "Score Synthesis", value: "Neighborhood Coherence" }
    ],
    accentColor: "text-indigo-400",
    glow: "border-indigo-500/20 bg-indigo-500/[0.03]"
  },
  {
    id: "stage-4",
    title: "Stage 4: Reranker V2",
    subtitle: "Fused Multi-Signal & Chronological Dominance",
    desc: "Combines sparse, dense, and graph components into a single multi-signal score. Reranker V2 evaluates Jaccard overlaps, proposition triplet checks, and resolves temporal values by suppressing older conflicting nodes pairwise.",
    math: "S_{rerank} = S_{lex} + S_{graph} + S_{entity} + S_{time} + S_{prop} - S_{contradiction}",
    specs: [
      { label: "Blended Signals", value: "7 distinct channels" },
      { label: "Conflict Resolver", value: "Pairwise Dominance" },
      { label: "Chronological filter", value: "Created_at timestamp" },
      { label: "Execution Mode", value: "100% Deterministic" }
    ],
    accentColor: "text-emerald-400",
    glow: "border-emerald-500/20 bg-emerald-500/[0.03]"
  }
];

export default function AdvancedADIPipeline() {
  const [activeStage, setActiveStage] = useState("stage-1");
  const stage = STAGES.find((s) => s.id === activeStage) || STAGES[0];

  return (
    <section className="py-24 px-4 bg-slate-950 border-t border-slate-900 relative overflow-hidden">
      {/* Background glow grids */}
      <div className="absolute top-1/3 right-1/4 w-[400px] h-[400px] bg-cyan-500/5 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-1/3 left-1/4 w-[500px] h-[500px] bg-purple-500/5 blur-[150px] rounded-full pointer-events-none" />

      <div className="max-w-7xl mx-auto relative z-10">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-purple-500/30 bg-purple-500/5 text-purple-300 text-xs font-semibold uppercase tracking-wider mb-4">
            Advanced ADI Architecture
          </div>
          <h2 className="text-4xl md:text-5xl font-black text-white tracking-tight mb-6 bg-gradient-to-r from-white via-cyan-100 to-indigo-300 bg-clip-text text-transparent">
            The 4-Stage Progressive ADI Retrieval Pipeline
          </h2>
          <p className="text-lg text-slate-400 max-w-3xl mx-auto leading-relaxed">
            By executing deterministic relational algebra, sparse pruning, stable HNSW graphs, and multi-hop diffusion in sequence, FAIM achieves extreme search recall and zero-hallucination accuracy in microseconds.
          </p>
        </div>

        {/* Dynamic Pipeline Interactive Section */}
        <div className="grid lg:grid-cols-12 gap-8 items-start mb-16">
          {/* Stage Selector Buttons */}
          <div className="lg:col-span-4 space-y-3">
            {STAGES.map((s) => (
              <button
                key={s.id}
                onClick={() => setActiveStage(s.id)}
                className={`w-full text-left p-5 rounded-2xl border transition-all duration-300 flex items-center justify-between ${
                  activeStage === s.id
                    ? `${s.glow} border-slate-700`
                    : "border-slate-900 bg-slate-950/20 hover:border-slate-800 hover:bg-slate-900/10 text-slate-500"
                }`}
              >
                <div>
                  <p className={`text-[10px] font-mono font-bold uppercase tracking-wider mb-1 ${activeStage === s.id ? s.accentColor : "text-slate-600"}`}>
                    {s.title.split(":")[0]}
                  </p>
                  <p className={`text-base font-bold tracking-tight ${activeStage === s.id ? "text-white" : "text-slate-400"}`}>
                    {s.title.split(":")[1].trim()}
                  </p>
                </div>
                <div className={`w-8 h-8 rounded-xl border flex items-center justify-center font-mono text-xs ${activeStage === s.id ? `${s.accentColor} border-slate-700 bg-slate-900/40` : "border-slate-900 text-slate-700"}`}>
                  {s.id.split("-")[1]}
                </div>
              </button>
            ))}
          </div>

          {/* Active Stage Detail Panel */}
          <div className={`lg:col-span-8 rounded-3xl border p-8 md:p-10 transition-all duration-500 ${stage.glow}`}>
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6 mb-6">
              <div>
                <span className={`text-xs font-mono font-bold uppercase tracking-wider ${stage.accentColor}`}>
                  {stage.title}
                </span>
                <h3 className="text-2xl font-black text-white tracking-tight mt-1">
                  {stage.subtitle}
                </h3>
              </div>
              <div className="rounded-xl bg-slate-950 border border-slate-900 px-4 py-2 font-mono text-[11px] text-cyan-300 shadow-inner">
                {stage.math}
              </div>
            </div>

            <p className="text-slate-400 text-sm leading-relaxed mb-8">
              {stage.desc}
            </p>

            {/* Spec Attributes Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {stage.specs.map((spec) => (
                <div key={spec.label} className="p-4 rounded-2xl border border-slate-900 bg-slate-950/40">
                  <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider mb-1">
                    {spec.label}
                  </p>
                  <p className="text-xs font-bold text-white font-mono">
                    {spec.value}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Fused Modality & Adaptation Row */}
        <div className="grid md:grid-cols-2 gap-6 mb-12">
          {/* Multilingual / Multimodal Panel */}
          <div className="rounded-3xl border border-slate-800 bg-slate-900/10 p-8 flex flex-col justify-between">
            <div>
              <span className="text-cyan-400 text-xs font-mono font-bold uppercase tracking-wider">
                Cross-Lingual & Multimodal (No-ML)
              </span>
              <h3 className="text-2xl font-black text-white tracking-tight mt-2 mb-4">
                Bilingual Concept Bridges & Layout Linearization
              </h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                FAIM maps English and German terms directly onto language-agnostic conceptual nodes. During query times, unstructured tabular data is linearized into normalized semiclon grids, allowing layout coordinates and perceptual hashes to boost results with zero transformer dependencies.
              </p>
            </div>
            <div className="border-t border-slate-800/80 pt-6 space-y-3">
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 font-medium">Bilingual Mapping</span>
                <span className="text-white font-mono">umsatz (DE) → revenue ← sales (EN)</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 font-medium">Table linearizer</span>
                <span className="text-white font-mono">| Q1 | $5M | → "Q1 ; $5M"</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 font-medium">Image pHash</span>
                <span className="text-white font-mono">16-char stable proxy fingerprint</span>
              </div>
            </div>
          </div>

          {/* Long-Tail Domain Ingestion Panel */}
          <div className="rounded-3xl border border-slate-800 bg-slate-900/10 p-8 flex flex-col justify-between">
            <div>
              <span className="text-purple-400 text-xs font-mono font-bold uppercase tracking-wider">
                Extractive Answer Synthesis
              </span>
              <h3 className="text-2xl font-black text-white tracking-tight mt-2 mb-4">
                Confidence Intervals & Contradiction Resolution
              </h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Instead of generating conversational text stochastically, FAIM extracts exact sentence spans directly from source nodes. It evaluates contradiction warning notes and scores a mathematically complete confidence interval, ensuring 100% auditable answers.
              </p>
            </div>
            <div className="border-t border-slate-800/80 pt-6">
              <div className="rounded-2xl bg-slate-950 border border-slate-900 p-4 font-mono text-[10px] text-purple-300">
                S_confidence = clamp( 0.45*S_avg + 0.30*S_breadth + 0.25*S_active - S_penalty )
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
