"use client";

import { motion } from "framer-motion";

const OUTCOMES = [
  {
    title: "Search turns into answers",
    text: "Users ask natural questions and get grounded, cited answers instead of a list of vaguely similar documents.",
  },
  {
    title: "Knowledge stays inspectable",
    text: "Teams can trace provenance, inspect the graph, and understand why a result was returned.",
  },
  {
    title: "The system stays operational",
    text: "Storage, rebuild, import, and extractor controls keep the knowledge layers fresh without rebuilding the product.",
  },
  {
    title: "Teams keep control",
    text: "Tenant isolation, scoped access, and self-hosting support production deployments in regulated environments.",
  },
  {
    title: "The engine adapts to the corpus",
    text: "Domain packs, multilingual links, and KB imports improve coverage for the actual data you run.",
  },
  {
    title: "It works without ML dependency",
    text: "The core memory and retrieval path remains deterministic, explainable, and offline-friendly.",
  },
];

const WORKFLOWS = [
  "Upload PDFs, DOCX, PPTX, XLSX, images, code, and text",
  "FAIM Native extractor — multi-column, tables, scanned OCR, zero ML",
  "Inspect provenance and download originals",
  "Rebuild canonical, multilingual, multimodal, or domain layers",
  "Ask Memory Query and get cited answers",
  "Use FIG View for lineage and graph tracing",
];

const AUDIENCE = [
  {
    label: "Knowledge Teams",
    text: "Find answers faster across docs, notes, and internal systems.",
  },
  {
    label: "Regulated Companies",
    text: "Keep audit trails, tenant isolation, and deterministic behavior.",
  },
  {
    label: "Platform Teams",
    text: "Integrate via API, control workflows, and keep the stack self-hostable.",
  },
];export default function LandingOutcomes() {
  return (
    <section className="py-28 px-4 bg-slate-950 relative overflow-hidden">
      {/* Background Structures */}
      <div className="absolute inset-0 faim-grid opacity-20" />
      <div className="absolute top-1/2 left-0 w-full h-px bg-gradient-to-r from-transparent via-emerald-500/10 to-transparent" />
      <div className="absolute top-1/4 -right-20 w-64 h-64 bg-emerald-500/5 blur-[100px] rounded-full" />

      <div className="max-w-6xl mx-auto relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="text-center mb-16"
        >
          <motion.span 
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            className="inline-block px-4 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-bold tracking-widest uppercase mb-4"
          >
            Why Teams Adopt FAIM
          </motion.span>
          <h2 className="text-3xl md:text-5xl font-bold text-white tracking-tight leading-tight">
            Real outcomes for <br className="hidden md:block" />
            <span className="bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">production knowledge</span> work
          </h2>
          <p className="mt-6 text-slate-400 max-w-3xl mx-auto text-lg leading-relaxed">
            FAIM is built to support the workflows companies actually need:
            upload, inspect, rebuild, query, explain, and operate with confidence.
          </p>
        </motion.div>

        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {OUTCOMES.map((item, index) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.5, delay: index * 0.05 }}
              whileHover={{ y: -5, transition: { duration: 0.2 } }}
              className="group relative rounded-3xl border border-slate-800 bg-slate-900/30 p-8 hover:border-emerald-500/30 hover:bg-slate-900/50 transition-all duration-300"
            >
              <div className="absolute top-0 right-0 w-16 h-16 bg-emerald-500/5 blur-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
              <h3 className="text-lg font-bold text-white group-hover:text-emerald-400 transition-colors">{item.title}</h3>
              <p className="mt-4 text-sm leading-relaxed text-slate-500 group-hover:text-slate-400 transition-colors">
                {item.text}
              </p>
            </motion.div>
          ))}
        </div>

        <div className="grid lg:grid-cols-2 gap-8 mt-12">
          {/* Typical Workflow */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="group rounded-3xl border border-emerald-500/10 bg-emerald-500/[0.02] p-8 hover:border-emerald-500/20 transition-all"
          >
            <div className="flex items-center gap-3 mb-8">
              <div className="w-8 h-px bg-emerald-500/40" />
              <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-emerald-400/80">
                Typical Workflow
              </p>
            </div>
            <div className="space-y-4">
              {WORKFLOWS.map((step, index) => (
                <motion.div
                  key={step}
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 * index }}
                  className="flex items-start gap-4 group/step"
                >
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg border border-emerald-500/20 bg-emerald-500/10 text-[10px] font-bold text-emerald-400 group-hover/step:bg-emerald-500 group-hover/step:text-slate-950 transition-all">
                    {index + 1}
                  </span>
                  <span className="text-sm text-slate-400 group-hover/step:text-slate-200 transition-colors leading-snug">
                    {step}
                  </span>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Built For */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="group rounded-3xl border border-purple-500/10 bg-purple-500/[0.02] p-8 hover:border-purple-500/20 transition-all"
          >
            <div className="flex items-center gap-3 mb-8">
              <div className="w-8 h-px bg-purple-500/40" />
              <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-purple-400/80">
                Built For
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-1">
              {AUDIENCE.map((item, i) => (
                <motion.div
                  key={item.label}
                  whileHover={{ x: 5 }}
                  className="rounded-2xl border border-slate-800 bg-slate-950/40 p-5 hover:border-purple-500/30 transition-all"
                >
                  <h3 className="text-sm font-bold text-white mb-2 flex items-center gap-2">
                    <div className="w-1 h-1 rounded-full bg-purple-500" />
                    {item.label}
                  </h3>
                  <p className="text-xs text-slate-500 leading-relaxed group-hover:text-slate-400 transition-colors">
                    {item.text}
                  </p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
