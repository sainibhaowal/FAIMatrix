"use client";

import { motion } from "framer-motion";
import { useRef } from "react";

const LAYERS = [
  {
    id: "layer-a",
    title: "Layer A: Multi-Channel Recall",
    subtitle: "Hybrid Dense & Sparse Shortlisting",
    color: "cyan",
    items: [
      {
        name: "Dense (VP-Tree)",
        desc: "Uses a Vantage Point Tree for sublinear semantic similarity search.",
        tech: "deterministic_ann.py",
      },
      {
        name: "Sparse (WAND)",
        desc: "Weak AND (WAND) algorithm for exact keyword and entity precision.",
        tech: "wand.py",
      },
      {
        name: "Canonicalization",
        desc: "Rewrites queries into the graph's native lexicon before search.",
        tech: "lexical_repo.py",
      },
    ],
  },
  {
    id: "layer-b",
    title: "Layer B: Graph-Aware Expansion",
    subtitle: "Inheritance & Semantic Diffusion",
    color: "purple",
    items: [
      {
        name: "Inheritance Expansion",
        desc: "Pulling parents and children from the graph hierarchy into recall.",
        tech: "query_engine.py",
      },
      {
        name: "Semantic Diffusion",
        desc: "Spreading scores through synonyms, hypernyms, and related edges.",
        tech: "diffusion.py",
      },
      {
        name: "Contradiction Notes",
        desc: "Identifying 'opposition' signatures during graph traversal.",
        tech: "graph_semantics.py",
      },
    ],
  },
  {
    id: "layer-c",
    title: "Layer C: Physics-Based Rerank",
    subtitle: "Multi-Signal Score Finalization",
    color: "rose",
    items: [
      {
        name: "Fractal Dynamics",
        desc: "Weighing results by novelty, recency, usage, and level depth.",
        tech: "reranker_v2.py",
      },
      {
        name: "Energy Bounding",
        desc: "Ensuring stable, deterministic scores via physics-based invariants.",
        tech: "fractal_physics.py",
      },
      {
        name: "Answer Synthesis",
        desc: "Extractive summarization grounded in high-confidence citations.",
        tech: "answer_synthesis.py",
      },
    ],
  },
];

export default function HybridRecall() {
  return (
    <section className="py-28 px-4 bg-slate-950 relative overflow-hidden">
      <div className="absolute inset-0 faim-grid opacity-40" />

      <div className="max-w-6xl mx-auto relative">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-24"
        >
          <span className="text-cyan-400 text-sm font-medium tracking-wider uppercase">
            Proprietary Engine
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            Hybrid Physics-Based{" "}
            <span className="bg-gradient-to-r from-cyan-400 via-purple-400 to-rose-400 bg-clip-text text-transparent">
              Graph Recall.
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto text-lg">
            Standard RAG is a best-guess. FAIM is a calculation. Our three-layer
            retrieval pipeline moves beyond simple similarity to provide logical
            precision and deterministic stability.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-8">
          {LAYERS.map((layer, idx) => (
            <motion.div
              key={layer.id}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: idx * 0.15 }}
              className="relative p-8 rounded-3xl border border-slate-800 bg-slate-900/20 group hover:border-slate-700 transition-all duration-500"
            >
              <div className="mb-6">
                <h3 className="text-xl font-bold text-white mb-1">
                  {layer.title}
                </h3>
                <p className={`text-sm font-medium text-${layer.color}-400/80`}>
                  {layer.subtitle}
                </p>
              </div>

              <div className="space-y-8">
                {layer.items.map((item, i) => (
                  <div key={item.name} className="relative">
                    <div className="flex items-center gap-3 mb-1.5">
                      <div
                        className={`w-1.5 h-1.5 rounded-full bg-${layer.color}-500`}
                      />
                      <h4 className="text-sm font-bold text-slate-200">
                        {item.name}
                      </h4>
                    </div>
                    <p className="text-xs text-slate-500 leading-relaxed pl-4.5 mb-2">
                      {item.desc}
                    </p>
                    <div className="pl-4.5">
                      <span className="text-[10px] font-mono text-slate-700 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800/50">
                        {item.tech}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.6 }}
          className="mt-20 p-8 rounded-2xl border border-slate-800 bg-slate-900/40"
        >
          <div className="grid md:grid-cols-2 gap-10 items-center">
            <div>
              <h3 className="text-xl font-bold text-white mb-4">
                The Rationale: Precision over &ldquo;Vibes&rdquo;
              </h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                Vector search alone often returns results that sound similar but
                are factually wrong. By forcing a **Sparse/Lexical check (WAND)**,
                FAIM ensures that specific names, dates, and entities are
                respected.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                {[
                  "No Information Loops",
                  "Logic-Aware Recall",
                  "Deterministic Scaling",
                ].map((tag) => (
                  <span
                    key={tag}
                    className="px-3 py-1 rounded-full bg-slate-950 border border-slate-800 text-[10px] font-bold text-slate-500 uppercase tracking-widest"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
            <div className="space-y-4">
              <p className="text-slate-300 text-sm font-medium italic">
                &ldquo;FAIM treats knowledge as a dynamic physical system where
                nodes have gravity (usage), charge (opposition), and momentum
                (recency), rather than just being static points in a
                database.&rdquo;
              </p>
              <div className="h-px w-full bg-gradient-to-r from-cyan-500/50 to-transparent" />
              <p className="text-xs text-slate-500 leading-relaxed">
                This architecture solves the &ldquo;lost in the middle&rdquo; and
                context blindness problems inherent in standard vector databases
                by leveraging graph inheritance and physics-based scoring.
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
