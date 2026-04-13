"use client";

import { motion } from "framer-motion";

const HIGHLIGHTS = [
  {
    title: "Memory Query",
    tag: "Grounded Answers",
    text: "Ask questions against your own memory and get cited answers you can inspect, trust, and share.",
  },
  {
    title: "Storage Control",
    tag: "Extractor + Rebuild",
    text: "Upload once, choose the extractor, and keep derived knowledge layers fresh without reworking the whole system.",
  },
  {
    title: "Graph Intelligence",
    tag: "Deterministic Retrieval",
    text: "Dense retrieval, sparse signals, and graph structure work together without black-box embeddings.",
  },
  {
    title: "FIG View",
    tag: "Graph Trace",
    text: "Inspect lineage, contradictions, and evidence paths in a graph surface built for operators.",
  },
  {
    title: "Explainability",
    tag: "Why This Result",
    text: "Every answer can show why it ranked, with the signals behind the result exposed in plain language.",
  },
  {
    title: "Domain + Multilingual",
    tag: "EN / DE + KB",
    text: "Work across English and German, plus domain-specific knowledge packs, without changing the core engine.",
  },
  {
    title: "Security + API",
    tag: "Production Ready",
    text: "Scoped keys, tenant isolation, and audit trails keep the platform usable in real organizations.",
  },
  {
    title: "No ML / LLM Required",
    tag: "Pure FAIM",
    text: "Core memory, retrieval, and answers stay deterministic, explainable, and self-hostable.",
  },
];

export default function LandingProductHighlights() {
  return (
    <section className="py-20 px-4 bg-gradient-to-b from-[#070a18] to-slate-950">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-10"
        >
          <span className="text-cyan-400 text-sm font-medium tracking-wider uppercase">
            Built for Production
          </span>
          <h2 className="mt-3 text-3xl md:text-4xl font-bold text-white">
            Real product surfaces for teams that need memory, not just chat
          </h2>
          <p className="mt-4 text-slate-400 max-w-3xl mx-auto">
            Memory Query, Storage, FIG View, explainability, multilingual retrieval,
            domain knowledge, and deterministic answers all live in the product now.
          </p>
        </motion.div>

        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          {HIGHLIGHTS.map((item, index) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.45, delay: index * 0.08 }}
              className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 shadow-lg shadow-black/20"
            >
              <p className="text-[10px] font-medium uppercase tracking-[0.28em] text-cyan-300/80">
                {item.tag}
              </p>
              <h3 className="mt-3 text-xl font-semibold text-white">{item.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-slate-400">
                {item.text}
              </p>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ duration: 0.45, delay: 0.1 }}
          className="mt-8 grid gap-3 md:grid-cols-3"
        >
          {[
            "Self-hostable and tenant-isolated",
            "Deterministic and explainable",
            "Offline-friendly and API-first",
            "EN/DE + domain knowledge ready",
            "History-aware and graph-native",
            "Built for storage, query, and audit workflows",
          ].map((line) => (
            <div
              key={line}
              className="rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3 text-sm text-slate-400"
            >
              {line}
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
