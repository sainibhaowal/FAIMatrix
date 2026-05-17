"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

interface FAQItem {
  question: string;
  answer: string;
}

const FAQS: FAQItem[] = [
  {
    question: "What is 24-Hop Reasoning?",
    answer:
      "Traditional systems use 1-hop retrieval (fetch and summarize). FAIM's 24-Hop Reasoning allows the Cortex engine to traverse up to 24 semantic layers of evidence, following logical chains across documents, events, and opposing views while maintaining 100% provenance and citation integrity for every single hop.",
  },
  {
    question: "How does the 1M+ Concept Registry work?",
    answer:
      "Unlike LLMs that 'think' for several seconds to classify intent, FAIM uses a deterministic registry of over 1,000,000 professional concepts. This allows the system to map your query to 8 core cognitive tasks in under 10ms with zero latency, zero drift, and zero hallucination risk.",
  },
  {
    question: "Is FAIMATRIX a vector database?",
    answer:
      "No. FAIMATRIX is a mathematical memory engine. Vector databases store and retrieve vectors. FAIM computes inheritance relationships, enforces mathematical invariants, runs fractal diagnostics, performs deterministic deduplication, and self-evolves \u2014 all without ML. Vectors are one component, not the whole system.",
  },
  {
    question: "Do I need a GPU to run FAIM?",
    answer:
      "No. The STRICT profile runs on 2 CPU cores and 1GB RAM with no GPU. This is verified in production via Docker resource limits. The core engine uses pure Python math \u2014 no PyTorch, no TensorFlow, no CUDA. GPU is optional for FAST/SCALE profiles but never required.",
  },
  {
    question: "How is this different from using OpenAI embeddings + Pinecone?",
    answer:
      "Three fundamental differences: (1) FAIM\u2019s 256-dim vectors are computed deterministically with no API call \u2014 same input always produces the same vector. (2) FAIM adds mathematical structure on top: inheritance fractions, antisymmetric merge, fractal physics, 8 invariants. Pinecone just stores and does similarity search. (3) FAIM works offline, air-gapped. Pinecone + OpenAI require cloud connectivity.",
  },
  {
    question: 'What does "deterministic" actually mean here?',
    answer:
      "It means: given the same input data and the same graph state, every operation produces exactly the same result. Same vectors, same inheritance fractions, same merge decisions (winner selected by SHA-256 hash comparison), same scores. Run it 10,000 times \u2014 identical output. This is mathematically enforced, not approximately reproducible.",
  },
  {
    question: "Can I use FAIM with my existing LLM (GPT-4, Claude, etc.)?",
    answer:
      "Yes. The application layer connects to any LLM for natural language queries and explanations. Generate API keys from the dashboard, connect from any framework (LangChain, LlamaIndex, or raw HTTP). The LLM translates between human language and FAIM\u2019s mathematical engine. But the engine itself runs independently \u2014 if the LLM goes down, FAIM keeps storing and retrieving.",
  },
  {
    question: "What is the golden ratio doing in a memory engine?",
    answer:
      "The scaling factor s = 1/\u03C6 \u2248 0.618 is the fixed point of the recurrence s = 1/(1+s). It guarantees self-similar energy scaling across hierarchy levels. Energy E = mean_L2_norm \u00D7 s must stay \u2264 2.0 \u2014 this is a mathematical stability bound. The golden ratio isn\u2019t decorative; it\u2019s the only value that maintains consistent scaling at every depth.",
  },
  {
    question: "How does multi-tenant isolation work?",
    answer:
      "Every tenant gets cryptographically isolated data. The middleware layer extracts tenant_id from every request and enforces it at the database level. Tenants cannot access each other\u2019s graphs, nodes, edges, or events. This is enforced by the auth middleware, not application logic \u2014 a tenant literally cannot construct a query that touches another tenant\u2019s data.",
  },
  {
    question: "Is FAIM suitable for production?",
    answer:
      "FAIM runs in Docker with PostgreSQL, Redis, and Qdrant. It has defined SpeedBudget profiles (STRICT through SCALE), rate limiting, JWT + API key authentication, scoped permissions, tenant isolation, and a write-behind queue. The STRICT profile targets p95 retrieve latency of 10ms at 1M nodes. All of this is in the current codebase \u2014 not a roadmap.",
  },
];

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section id="faq" className="py-28 px-4 bg-slate-950">
      <div className="max-w-3xl mx-auto">
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
