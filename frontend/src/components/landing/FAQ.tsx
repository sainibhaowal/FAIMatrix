"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

interface FAQItem {
  question: string;
  answer: string;
}

const FAQS: FAQItem[] = [
  {
    question: "How deep does reasoning go?",
    answer:
      "FAIM supports agent-controlled bounded multi-hop graph traversal via graph_max_hops (1–24, defaulting to 2). Simple lookups stay shallow, while external AI agents can request deeper hop walks with full provenance and citation metadata.",
  },
  {
    question: "How does the semantic router work?",
    answer:
      "FAIM prepares and scores queries deterministically without an LLM classifier, combining native vectors, built-in multilingual semantic embeddings, ConceptNet lexical broadening, and bounded multi-hop graph traversal. With fixed inputs and configuration, core retrieval scoring is repeatable.",
  },
  {
    question: "Is FAIMATRIX a vector database?",
    answer:
      "No. FAIMATRIX is a mathematical memory engine. Vector databases store and retrieve vectors. FAIM computes inheritance relationships, enforces mathematical invariants, runs fractal diagnostics, performs deterministic deduplication, and can self-evolve through explicit graph controls \u2014 all without ML. Vectors are one component, not the whole system.",
  },
  {
    question: "Do I need a GPU to run FAIM?",
    answer:
      "No GPU is required. The deterministic core runs on CPU, and built-in multilingual semantic embeddings also run locally on CPU. GPU acceleration is optional for higher-throughput workloads, never required.",
  },
  {
    question: "How is this different from using OpenAI embeddings + Pinecone?",
    answer:
      "Three practical differences: (1) FAIM\u2019s native vectors are computed locally and repeatably when the encoder configuration is fixed. (2) FAIM adds graph structure, lifecycle controls, evidence, and invariant checks around retrieval; managed vector services focus on indexed retrieval and are composed with application logic for these concerns. (3) FAIM can run without cloud APIs; using hosted providers such as OpenAI or Pinecone introduces external service dependencies.",
  },
  {
    question: 'What does "deterministic" actually mean here?',
    answer:
      "It means the core operations are designed to repeat when input data, graph state, configuration, dependency versions, and index settings are fixed. Approximate ANN search, OCR, and LLM/provider calls can vary, so we do not claim every end-to-end response is identical.",
  },
  {
    question: "Can I use FAIM with my existing LLM (GPT-4, Claude, etc.)?",
    answer:
      "Yes. FAIM is a Zero-LLM memory engine designed to plug directly into external AI agents and LLM apps. Connect Cursor, Claude, or VS Code in 1 click via Remote MCP (/mcp + OAuth 2.1 / PKCE), run offline with the faim-mcp CLI or Python SDK, or call REST endpoints with one-time scoped API keys from Dashboard → API Keys.",
  },
  {
    question: "What is the golden ratio doing in a memory engine?",
    answer:
      "The implementation uses s = 1/\u03C6 \u2248 0.618, the fixed point of s = 1/(1+s), as one of its scaling parameters. The engine checks its configured energy bound as an invariant; this is an internal stability rule, not a universal guarantee about retrieval quality.",
  },
  {
    question: "How does multi-tenant isolation work?",
    answer:
      "Requests are authenticated, scoped to a tenant, and constrained by database access paths. Protected fields use the configured encryption controls. Isolation must still be verified through deployment configuration and tenant-isolation attack tests; the landing page does not treat it as a blanket guarantee.",
  },
  {
    question: "Is FAIM suitable for production?",
    answer:
      "FAIM runs in Docker with PostgreSQL, Redis, and optional Qdrant acceleration. It includes SpeedBudget profiles, rate limiting, JWT + API-key authentication, scoped permissions, tenant controls, a write-behind queue, and explicit default-off autonomy controls. Latency and throughput depend on graph size, hardware, configuration, and workload; see the benchmark surface for measured runs.",
  },
];

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section id="faq" className="py-28 px-4 bg-slate-950">
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-slate-400 text-sm font-medium tracking-wider uppercase">
            FAQ
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            Common Questions
          </h2>
        </motion.div>

        {/* FAQ Items */}
        <div className="space-y-3">
          {FAQS.map((faq, i) => {
            const isOpen = openIndex === i;
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 15 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.05 }}
              >
                <button
                  onClick={() => setOpenIndex(isOpen ? null : i)}
                  className={`w-full text-left p-5 rounded-xl border transition-all duration-300 ${
                    isOpen
                      ? "border-slate-700 bg-slate-900/60"
                      : "border-slate-800/60 bg-slate-900/20 hover:border-slate-700 hover:bg-slate-900/40"
                  }`}
                >
                  <div className="flex items-center justify-between gap-4">
                    <h3 className="text-white font-medium text-sm md:text-base">
                      {faq.question}
                    </h3>
                    <motion.svg
                      animate={{ rotate: isOpen ? 180 : 0 }}
                      transition={{ duration: 0.25 }}
                      className="w-5 h-5 text-slate-500 shrink-0"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M19 9l-7 7-7-7"
                      />
                    </motion.svg>
                  </div>

                  <AnimatePresence initial={false}>
                    {isOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.25, ease: "easeOut" }}
                        className="overflow-hidden"
                      >
                        <p className="text-slate-400 text-sm leading-relaxed mt-4 pt-4 border-t border-slate-800">
                          {faq.answer}
                        </p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </button>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
