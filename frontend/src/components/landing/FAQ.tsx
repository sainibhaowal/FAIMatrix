"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const faqs = [
  {
    question: "What is FAIM Lab?",
    answer:
      "FAIM Lab (Fractal Antisymmetric Inheritance Memory) is an AI-powered knowledge management system that organizes your information into an intelligent, self-evolving knowledge graph. It learns from your data and helps you discover connections you never knew existed.",
  },
  {
    question: "How does the knowledge graph work?",
    answer:
      "When you add documents, notes, or text, FAIM automatically extracts key concepts and creates connections between related ideas. The graph evolves over time, becoming smarter and more connected as you add more knowledge.",
  },
  {
    question: "Is my data secure?",
    answer:
      "Absolutely. Your data is encrypted at rest and in transit. We offer self-hosted options for enterprises, and our cloud infrastructure is SOC 2 compliant. You maintain full ownership of your data.",
  },
  {
    question: "Can I integrate FAIM with other tools?",
    answer:
      "Yes! FAIM offers a REST API and webhooks for integration with your existing tools. Pro and Enterprise plans include direct integrations with Notion, Obsidian, and major document management systems.",
  },
  {
    question: "What file formats are supported?",
    answer:
      "FAIM supports PDF, DOCX, TXT, Markdown, and plain text. We also support direct paste from web pages and can process code files in most programming languages.",
  },
  {
    question: "How is this different from traditional search?",
    answer:
      "Traditional search finds exact matches. FAIM understands context and relationships. Ask a question in natural language and get answers that synthesize knowledge from multiple sources in your graph.",
  },
];

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section
      id="faq"
      className="py-24 px-4 bg-gradient-to-b from-slate-950 to-slate-900"
    >
      <div className="max-w-3xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <span className="text-purple-400 text-sm font-medium tracking-wide uppercase">
            FAQ
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            Frequently Asked Questions
          </h2>
        </motion.div>

        <div className="space-y-4">
          {faqs.map((faq, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.05 }}
              className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/50"
            >
              <button
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
                className="w-full px-6 py-5 flex items-center justify-between text-left hover:bg-slate-800/50 transition-colors"
              >
                <span className="text-white font-medium pr-4">
                  {faq.question}
                </span>
                <motion.div
                  animate={{ rotate: openIndex === index ? 180 : 0 }}
                  transition={{ duration: 0.2 }}
                  className="shrink-0"
                >
                  <svg
                    className="w-5 h-5 text-slate-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </motion.div>
              </button>

              <AnimatePresence>
                {openIndex === index && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <div className="px-6 pb-5 text-slate-400 leading-relaxed">
                      {faq.answer}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
