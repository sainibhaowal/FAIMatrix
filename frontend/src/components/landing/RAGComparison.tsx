"use client";

import { motion } from "framer-motion";

const COMPARISONS = [
  {
    feature: "Retrieval Logic",
    standard: "Approximate (ANN) Vector Search",
    faim: "Deterministic Physics-Based Graph Recall",
    faimBetter: true,
  },
  {
    feature: "Accuracy Mode",
    standard: "Semantic 'Vibes' & Similarity",
    faim: "Logical Inheritance & Fact-Checking",
    faimBetter: true,
  },
  {
    feature: "Context Depth",
    standard: "Lost in the middle (flat chunks)",
    faim: "Deep Graph Diffusion (K-hop aware)",
    faimBetter: true,
  },
  {
    feature: "Stability",
    standard: "Jittery results as index grows",
    faim: "100% Repeatable & Stable",
    faimBetter: true,
  },
  {
    feature: "Answer Style",
    standard: "Generative (risk of hallucination)",
    faim: "Extractive (citation-first truth)",
    faimBetter: true,
  },
  {
    feature: "LLM Dependency",
    standard: "Mandatory for every query",
    faim: "Optional (Engine is self-sufficient)",
    faimBetter: true,
  },
];

export default function RAGComparison() {
  return (
    <section className="py-28 px-4 bg-[#050814] relative overflow-hidden">
      <div className="absolute inset-0 faim-grid opacity-20" />

      <div className="max-w-4xl mx-auto relative">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            FAIM vs. <span className="text-slate-500">Standard RAG</span>
          </h2>
          <p className="text-slate-400">
            Why leading engineering teams are moving away from simple vector databases.
          </p>
        </motion.div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/20 overflow-hidden backdrop-blur-sm">
          <div className="grid grid-cols-3 gap-4 px-6 py-4 border-b border-slate-800 bg-slate-900/50">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Feature</span>
            <span className="text-xs font-bold text-slate-500 uppercase tracking-widest text-center">Standard RAG</span>
            <span className="text-xs font-bold text-cyan-400 uppercase tracking-widest text-center">FAIM-Native</span>
          </div>

          <div className="divide-y divide-slate-800/50">
            {COMPARISONS.map((row, i) => (
              <motion.div
                key={row.feature}
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className="grid grid-cols-3 gap-4 px-6 py-5 items-center hover:bg-slate-800/10 transition-colors"
              >
                <span className="text-sm font-medium text-slate-300">{row.feature}</span>
                <span className="text-xs text-slate-500 text-center">{row.standard}</span>
                <div className="flex flex-col items-center">
                  <span className="text-xs text-cyan-300 font-bold text-center">
                    {row.faim}
                  </span>
                  {row.faimBetter && (
                    <span className="mt-1 text-[10px] text-cyan-500 font-mono uppercase tracking-tighter">
                      Deterministic
                    </span>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="mt-8 text-center text-xs text-slate-600 italic"
        >
          * Standard RAG refers to vanilla vector search using HNSW indices and flat document chunking.
        </motion.p>
      </div>
    </section>
  );
}
