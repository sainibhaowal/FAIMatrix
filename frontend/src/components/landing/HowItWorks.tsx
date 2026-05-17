"use client";

import { motion } from "framer-motion";

const PIPELINE_STEPS = [
  {
    number: "01",
    title: "Ingest",
    description:
      "Raw documents enter deterministic extraction. FAIM produces evidence blocks, native 256-dimensional vectors, and additive sidecars for lexical, structural, and multimodal features.",
    detail: "extract -> packetize -> encode -> sidecars",
    gradient: "from-cyan-500 to-blue-500",
    icon: (
      <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
      </svg>
    ),
  },
  {
    number: "02",
    title: "Classify",
    description:
      "Every query is mapped against the 1M+ Semantic Alias Registry. Intent is routed into 8 core cognitive tasks in <10ms, eliminating LLM classification latency.",
    detail: "1M concepts -> task routing -> deterministic intent",
    gradient: "from-blue-500 to-indigo-500",
    icon: (
      <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.53 16.122l9.37-5.622a.5.5 0 000-.856l-9.37-5.622a.5.5 0 00-.73.428v11.244a.5.5 0 00.73.428z" />
      </svg>
    ),
  },
  {
    number: "03",
    title: "Structure",
    description:
      "New memories are linked into the graph through inheritance, semantic edges, and canonical forms. The graph becomes the retrieval substrate, not just a storage container.",
    detail: "inheritance -> semantic edges -> graph version",
    gradient: "from-indigo-500 to-purple-500",
    icon: (
      <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
      </svg>
    ),
  },
  {
    number: "04",
    title: "Adapt",
    description:
      "Graph-local rebuild paths mine aliases, phrases, and terminology. This adds coverage without changing raw truth or native vector identity.",
    detail: "canonical rebuilds -> KB import -> domain enrichment",
    gradient: "from-purple-500 to-pink-500",
    icon: (
      <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25" />
      </svg>
    ),
  },
  {
    number: "05",
    title: "Retrieve",
    description:
      "Queries combine dense native vectors with 24-hop graph reasoning. FAIM traverses deep evidence chains to find grounded answers across disparate documents.",
    detail: "sparse + dense shortlist -> 24-hop expansion -> reranker v2",
    gradient: "from-pink-500 to-orange-500",
    icon: (
      <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
      </svg>
    ),
  },
  {
    number: "06",
    title: "Answer",
    description:
      "Top evidence is turned into a deterministic answer with full provenance. Cortex generates memory proposals for your review before any persistence.",
    detail: "span selection -> citation-first answer -> proposals review",
    gradient: "from-emerald-500 to-cyan-500",
    icon: (
      <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
      </svg>
    ),
  },
];

export default function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="py-28 px-4 bg-gradient-to-b from-[#070a18] to-slate-950"
    >
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <span className="text-purple-400 text-sm font-medium tracking-wider uppercase">
            Pipeline
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            From Raw Data to{" "}
            <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              Grounded Answers
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto">
            FAIM now covers the full path from raw data to grounded answers. The
            core invariants remain intact while retrieval and answer layers stay
            additive. The product surfaces that matter most are FAIM Cortex for
            grounded answers and Storage for extractor selection, provenance,
            and maintenance workflows.
          </p>
        </motion.div>

        <div className="relative">
          <div className="absolute left-6 md:left-8 top-0 bottom-0 w-px bg-gradient-to-b from-cyan-500/40 via-purple-500/40 to-emerald-500/40 hidden sm:block" />

          <div className="space-y-6">
            {PIPELINE_STEPS.map((step, index) => (
              <motion.div
                key={step.number}
                initial={{ opacity: 0, x: -30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-30px" }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="relative flex gap-6 md:gap-8 group"
              >
                <div className="relative z-10 shrink-0">
                  <div
                    className={`w-12 h-12 md:w-16 md:h-16 rounded-2xl bg-gradient-to-br ${step.gradient} flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform duration-300`}
                  >
                    {step.icon}
                  </div>
                </div>

                <div className="pb-8 flex-1">
                  <div className="flex items-baseline gap-3 mb-2">
                    <span className="text-slate-600 text-xs font-mono font-bold">
                      {step.number}
                    </span>
                    <h3 className="text-xl font-bold text-white">
                      {step.title}
                    </h3>
                  </div>
                  <p className="text-slate-400 text-sm leading-relaxed mb-3">
                    {step.description}
                  </p>
                  <p className="text-slate-600 text-xs font-mono">
                    {step.detail}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
