"use client";

import { motion } from "framer-motion";

const SPEC_GROUPS = [
  {
    title: "Vector Engine",
    color: "cyan",
    borderColor: "border-cyan-500/20",
    specs: [
      { label: "Vector Dimension", value: "256", unit: "fixed" },
      { label: "Encoding", value: "Deterministic", unit: "native" },
      { label: "Hash Algorithm", value: "SHA-256", unit: "" },
      { label: "Invariant Checks", value: "8", unit: "per write" },
    ],
  },
  {
    title: "Retrieval Stack",
    color: "purple",
    borderColor: "border-purple-500/20",
    specs: [
      { label: "Representation V2", value: "Dense + Sparse", unit: "" },
      { label: "Canonical Semantics", value: "PMI + Rules", unit: "" },
      { label: "Graph Expansion", value: "K-hop", unit: "bounded" },
      { label: "Reranker V2", value: "Deterministic", unit: "proposition-aware" },
    ],
  },
  {
    title: "Knowledge Layers",
    color: "blue",
    borderColor: "border-blue-500/20",
    specs: [
      { label: "Multilingual", value: "EN + DE", unit: "concept-linked" },
      { label: "Multimodal", value: "OCR / Table / Layout / pHash", unit: "" },
      { label: "Domain Knowledge", value: "Offline KB", unit: "graph-scoped" },
      { label: "Answer Mode", value: "Extractive", unit: "citation-first" },
    ],
  },
  {
    title: "Infrastructure",
    color: "emerald",
    borderColor: "border-emerald-500/20",
    specs: [
      { label: "Tenant Isolation", value: "Built-in", unit: "" },
      { label: "LLM Required", value: "No", unit: "" },
      { label: "Cloud Required", value: "No", unit: "" },
      { label: "Scale Path", value: "Inverted Index + ANN", unit: "" },
    ],
  },
];

const STACK_PROFILES = [
  { name: "Lexical", focus: "Representation V2", detail: "word / phrase / entity / time / layout sidecars", source: "representation_v2.py", color: "text-cyan-400" },
  { name: "Graph", focus: "Graph Semantics", detail: "bounded diffusion, semantic paths, contradiction-aware traversal", source: "diffusion.py", color: "text-purple-400" },
  { name: "Scale", focus: "Scale Path", detail: "inverted index, WAND shortlist, deterministic ANN", source: "inverted_index.py", color: "text-emerald-400" },
  { name: "Answer", focus: "Answer Layer", detail: "span selection, confidence, citations, contradiction notes", source: "answer_synthesis.py", color: "text-amber-400" },
];

const colorMap: Record<string, string> = {
  cyan: "text-cyan-400",
  purple: "text-purple-400",
  blue: "text-blue-400",
  emerald: "text-emerald-400",
};

const bgMap: Record<string, string> = {
  cyan: "bg-cyan-500/10",
  purple: "bg-purple-500/10",
  blue: "bg-blue-500/10",
  emerald: "bg-emerald-500/10",
};

export default function TechSpecs() {
  return (
    <section id="specs" className="py-28 px-4 bg-gradient-to-b from-slate-950 to-[#070a18]">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <span className="text-amber-400 text-sm font-medium tracking-wider uppercase">
            Specifications
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            Real Architecture.{" "}
            <span className="bg-gradient-to-r from-amber-400 to-orange-400 bg-clip-text text-transparent">
              From Real Code.
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto">
            These are implementation facts from the current FAIM stack, not
            benchmark theater. The landing page now reflects what the current platform actually ships.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-5 mb-16">
          {SPEC_GROUPS.map((group, gi) => (
            <motion.div
              key={group.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: gi * 0.1 }}
              className={`p-6 rounded-2xl border ${group.borderColor} bg-slate-900/30`}
            >
              <div className="flex items-center gap-3 mb-5">
                <div className={`w-2 h-2 rounded-full ${bgMap[group.color]}`}>
                  <div className={`w-2 h-2 rounded-full ${colorMap[group.color]} animate-pulse`} style={{ opacity: 0.8 }} />
                </div>
                <h3 className={`text-sm font-bold tracking-wider uppercase ${colorMap[group.color]}`}>
                  {group.title}
                </h3>
              </div>

              <div className="space-y-3">
                {group.specs.map((spec) => (
                  <div key={spec.label} className="flex items-center justify-between py-2 border-b border-slate-800/50 last:border-0">
                    <span className="text-slate-500 text-sm">{spec.label}</span>
                    <span className="text-white font-mono text-sm font-medium">
                      {spec.value}
                      {spec.unit && (
                        <span className="text-slate-600 text-xs ml-1.5">{spec.unit}</span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h3 className="text-xl font-bold text-white text-center mb-8">
            Additive Retrieval Layers
            <span className="block text-sm font-normal text-slate-500 mt-1">
              major extensions added around the native FAIM core
            </span>
          </h3>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/30 overflow-hidden">
            <div className="grid grid-cols-5 gap-4 px-6 py-4 border-b border-slate-800 bg-slate-900/50">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Layer</span>
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Focus</span>
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">What It Added</span>
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Source</span>
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Mode</span>
            </div>

            {STACK_PROFILES.map((profile, i) => (
              <motion.div
                key={profile.name}
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.3, delay: i * 0.08 }}
                className="grid grid-cols-5 gap-4 px-6 py-4 border-b border-slate-800/50 last:border-0 hover:bg-slate-800/20 transition-colors"
              >
                <span className={`font-mono text-sm font-bold ${profile.color}`}>
                  {profile.name}
                </span>
                <span className="text-white font-mono text-sm">{profile.focus}</span>
                <span className="text-white text-sm">{profile.detail}</span>
                <span className="text-slate-400 font-mono text-sm">{profile.source}</span>
                <span className="font-mono text-sm text-slate-300">
                  additive
                </span>
              </motion.div>
            ))}
          </div>

          <p className="text-center text-slate-600 text-xs mt-4 font-mono">
            The native FAIM core remains the base layer beneath all of these additions.
          </p>
        </motion.div>
      </div>
    </section>
  );
}
