"use client";

import { motion } from "framer-motion";

const HIGHLIGHTS = [
  {
    title: "Deterministic Semantic Routing",
    tag: "Scale-Ready",
    text: "Deterministic classification through a seeded alias map. Zero-latency, zero-ML overhead, and 100% predictable.",
  },
  {
    title: "Deterministic Intel",
    tag: "Pure Math Core",
    text: "No neural network black-boxes. Core retrieval and reasoning powered by 256-dim deterministic invariants.",
  },
  {
    title: "Bounded Graph Reasoning",
    tag: "Deep Inference",
    text: "Trace evidence chains with bounded hop budgets. Follow path logic with confidence decay tracking.",
  },
  {
    title: "Guarded Writebacks",
    tag: "Safety Protocol",
    text: "Memory writes still require approval, but approved Cortex writebacks now execute through a durable backend path and show receipts in the 3D FIG graph.",
  },
  {
    title: "Explainability",
    tag: "Why This Result",
    text: "Every answer can show why it ranked, with the signals behind the result exposed in plain language.",
  },
  {
    title: "Domain + Multilingual",
    tag: "EN / DE + Memory",
    text: "Work across English and German while FAIM automatically builds graph-local domain memory from what you upload.",
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
  {
    title: "Deep Reasoning",
    tag: "Multi-hop Inference",
    text: "Follows chains of evidence across your knowledge graph to answer complex 'why' questions. Traces connections with bounded hop budgets and confidence decay tracking.",
  },
  {
    title: "Intelligent Planning",
    tag: "Query Optimization",
    text: "Automatically decomposes complex questions into executable sub-queries. Handles comparisons, trend analysis, and exploratory searches.",
  },
  {
    title: "Knowledge Synthesis",
    tag: "Cross-document",
    text: "Finds correlations, contradictions, and trends across multiple documents. Weaves scattered information into unified insights.",
  },
  {
    title: "Continuous Learning",
    tag: "Adaptive",
    text: "Improves from user feedback and ratings. Tracks reasoning pattern success and adjusts confidence thresholds automatically.",
  },
  {
    title: "Temporal Analysis",
    tag: "Time-aware",
    text: "Understands sequences, timelines, and temporal relationships. Analyzes 'before', 'after', and 'during' for trend and deadline insights.",
  },
  {
    title: "Quality Intelligence",
    tag: "Monitoring",
    text: "Built-in quality dashboard tracks user satisfaction, confidence distribution, and system health. Provides actionable improvement recommendations.",
  },
];

export default function LandingProductHighlights() {
  return (
    <section className="py-12 sm:py-28 px-4 bg-gradient-to-b from-[#070a18] to-slate-950 relative overflow-hidden">
      {/* Background Ornaments */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/5 blur-[120px] rounded-full" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/5 blur-[120px] rounded-full" />

      <div className="max-w-6xl mx-auto relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="text-center mb-10 sm:mb-16"
        >
          <motion.span
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            className="inline-block px-4 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-[10px] font-bold tracking-widest uppercase mb-4"
          >
            Built for Production
          </motion.span>
          <h2 className="text-3xl md:text-5xl font-bold text-white tracking-tight leading-tight">
            Real product surfaces for teams <br className="hidden md:block" />
            that need{" "}
            <span className="bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
              memory
            </span>
            , not just chat
          </h2>
          <p className="mt-4 sm:mt-6 text-slate-400 max-w-3xl mx-auto text-base sm:text-lg leading-relaxed">
            FAIM Cortex, Storage, FIG View, and deterministic answers all live
            in the product now. Every claim is backed by the core engine.
          </p>
        </motion.div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {HIGHLIGHTS.map((item, index) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.5, delay: index * 0.05 }}
              whileHover={{ y: -8, transition: { duration: 0.2 } }}
              className="group relative rounded-3xl border border-slate-800 bg-slate-900/40 p-5 sm:p-8 hover:border-cyan-500/30 hover:bg-slate-900/60 transition-all duration-300 overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/[0.03] to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-400/60 group-hover:text-cyan-400 transition-colors">
                {item.tag}
              </p>
              <h3 className="mt-4 text-xl font-bold text-white group-hover:translate-x-1 transition-transform">
                {item.title}
              </h3>
              <p className="mt-4 text-sm leading-relaxed text-slate-500 group-hover:text-slate-400 transition-colors">
                {item.text}
              </p>

              {/* Decorative corner accent */}
              <div className="absolute -bottom-2 -right-2 w-12 h-12 bg-cyan-500/5 blur-xl group-hover:bg-cyan-500/10 transition-all" />
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1, delay: 0.4 }}
          className="mt-8 sm:mt-12 grid gap-3 sm:gap-4 md:grid-cols-3"
        >
          {[
            "Self-hostable and tenant-isolated",
            "Deterministic and explainable",
            "Offline-friendly and API-first",
            "EN/DE + autonomous domain memory",
            "History-aware and graph-native",
            "Built for storage, query, and audit workflows",
          ].map((line, i) => (
            <motion.div
              key={line}
              whileHover={{ scale: 1.02 }}
              className="flex items-center gap-3 rounded-2xl border border-slate-800/60 bg-slate-900/20 px-5 py-4 text-[11px] font-bold uppercase tracking-widest text-slate-500 hover:text-slate-300 hover:border-slate-700 transition-all cursor-default"
            >
              <div className="w-1.5 h-1.5 rounded-full bg-cyan-500/40" />
              {line}
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
