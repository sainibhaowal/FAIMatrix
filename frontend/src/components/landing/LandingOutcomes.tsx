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
];

export default function LandingOutcomes() {
  return (
    <section className="py-24 px-4 bg-slate-950">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <span className="text-emerald-400 text-sm font-medium tracking-wider uppercase">
            Why Teams Adopt FAIM
          </span>
          <h2 className="mt-3 text-3xl md:text-4xl font-bold text-white">
            Real outcomes for production knowledge work
          </h2>
          <p className="mt-4 text-slate-400 max-w-3xl mx-auto">
            FAIM is built to support the workflows companies actually need:
            upload, inspect, rebuild, query, explain, and operate with confidence.
          </p>
        </motion.div>

        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {OUTCOMES.map((item, index) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-30px" }}
              transition={{ duration: 0.45, delay: index * 0.06 }}
              className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6"
            >
              <h3 className="text-lg font-semibold text-white">{item.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-slate-400">{item.text}</p>
            </motion.div>
          ))}
        </div>

        <div className="grid lg:grid-cols-2 gap-6 mt-8">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-30px" }}
            transition={{ duration: 0.45 }}
            className="rounded-2xl border border-cyan-500/15 bg-cyan-500/[0.04] p-6"
          >
            <p className="text-[10px] font-medium uppercase tracking-[0.28em] text-cyan-300/80">
              Typical Workflow
            </p>
            <div className="mt-4 space-y-3">
              {WORKFLOWS.map((step, index) => (
                <div key={step} className="flex items-start gap-3 text-sm text-slate-300">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-cyan-500/30 bg-cyan-500/10 text-[10px] font-semibold text-cyan-300">
                    {index + 1}
                  </span>
                  <span>{step}</span>
                </div>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-30px" }}
            transition={{ duration: 0.45, delay: 0.06 }}
            className="rounded-2xl border border-purple-500/15 bg-purple-500/[0.04] p-6"
          >
            <p className="text-[10px] font-medium uppercase tracking-[0.28em] text-purple-300/80">
              Built For
            </p>
            <div className="mt-4 grid gap-4 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
              {AUDIENCE.map((item) => (
                <div key={item.label} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <h3 className="text-sm font-semibold text-white">{item.label}</h3>
                  <p className="mt-2 text-sm text-slate-400 leading-relaxed">{item.text}</p>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
