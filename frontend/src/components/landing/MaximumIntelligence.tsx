/**
 * Advanced Reasoning Engine Showcase
 *
 * FAIM Cortex goes beyond simple retrieval to deliver
 * deep reasoning, synthesis, and continuous improvement.
 */

"use client";

import { motion } from "framer-motion";
import {
  GitBranch,
  Split,
  RefreshCw,
  Globe,
  Activity,
  Clock,
  Monitor,
  Layers,
} from "lucide-react";

const CAPABILITIES = [
  {
    title: "Deep Causal Reasoning",
    icon: GitBranch,
    description:
      "Answers complex 'why' questions by following chains of evidence across your knowledge graph. Traces connections between facts to uncover root causes and relationships.",
    tag: "Multi-hop inference",
  },
  {
    title: "Intelligent Query Planning",
    icon: Split,
    description:
      "Automatically decomposes complex questions into optimal search strategies. Handles comparisons, trend analysis, and cross-document exploration with smart execution planning.",
    tag: "Adaptive planning",
  },
  {
    title: "Continuous Learning",
    icon: RefreshCw,
    description:
      "Improves answer quality over time by learning from user feedback. Tracks reasoning pattern success and automatically adjusts confidence thresholds for more reliable results.",
    tag: "Feedback-driven improvement",
  },
  {
    title: "FAIM-Native Semantic Power",
    icon: Globe,
    description:
      "Additive semantic signatures strengthen phrase, concept, alias, transliteration, morphology, relation, value, and temporal matching around the deterministic core. This improves fuzzy retrieval while keeping the system explainable and graph-native.",
    tag: "Native semantic channels",
  },
  {
    title: "Quality Intelligence",
    icon: Activity,
    description:
      "Built-in quality monitoring tracks user satisfaction, confidence distribution, and system performance. Provides actionable recommendations to improve knowledge coverage and accuracy.",
    tag: "Real-time health metrics",
  },
  {
    title: "Temporal Understanding",
    icon: Clock,
    description:
      "Reasons about sequences, timelines, and temporal relationships. Understands 'before', 'after', and 'during' to analyze trends, check deadlines, and build chronological narratives.",
    tag: "Time-aware reasoning",
  },
  {
    title: "Transparent Explanations",
    icon: Monitor,
    description:
      "Visualizes reasoning paths so you can see exactly how answers were derived. Interactive feedback interfaces let you rate and correct responses to guide future improvements.",
    tag: "Explainable AI",
  },
  {
    title: "Enterprise Integration",
    icon: Layers,
    description:
      "Production-ready APIs enable seamless integration into your workflows. Every capability is exposed through REST endpoints with full tenant isolation and security controls.",
    tag: "API-first architecture",
  },
];

const METRICS = [
  { label: "Reasoning Depth", value: "Bounded", suffix: " causal chains" },
  { label: "Learning", value: "Continuous", suffix: " from feedback" },
  { label: "Synthesis", value: "Cross-document", suffix: " insights" },
  { label: "Quality", value: "Real-time", suffix: " monitoring" },
];

export default function MaximumIntelligence() {
  return (
    <section className="py-24 px-4 bg-gradient-to-b from-slate-950 via-slate-900/50 to-slate-950 relative overflow-hidden">
      {/* Background Elements */}
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-cyan-500/20 to-transparent" />
      <div className="absolute top-1/4 -left-32 w-64 h-64 bg-cyan-500/5 blur-[120px] rounded-full" />
      <div className="absolute bottom-1/4 -right-32 w-64 h-64 bg-purple-500/5 blur-[120px] rounded-full" />

      <div className="max-w-7xl mx-auto relative z-10">
        {/* Header */}
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
            className="inline-block px-4 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-[10px] font-bold tracking-widest uppercase mb-4"
          >
            Advanced Reasoning Engine
          </motion.span>
          <h2 className="text-3xl md:text-5xl font-bold text-white tracking-tight leading-tight mb-6">
            From Retrieval to{" "}
            <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
              Deep Understanding
            </span>
          </h2>
          <p className="text-lg text-slate-400 max-w-3xl mx-auto leading-relaxed">
            FAIM Cortex goes beyond finding documents — it reasons across your
            knowledge, and delivers answers you can trust and verify. The
            runtime stays deterministic, semantic enrichment remains additive
            and inspectable, and any autonomy features stay explicit and
            graph-scoped.
          </p>
        </motion.div>

        {/* Metrics */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mb-16 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4"
        >
          {METRICS.map((metric, index) => (
            <motion.div
              key={metric.label}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 * index }}
              className="group relative min-h-[132px] overflow-hidden border border-slate-800 bg-[#0a0f19]/80 px-5 py-4 text-left transition-all hover:border-cyan-500/30 hover:bg-[#0d1420]"
            >
              <span className="absolute inset-y-0 left-0 w-px bg-cyan-400/70 transition-all group-hover:w-[2px]" />
              <div className="flex items-center justify-between gap-3">
                <div className="font-mono text-[9px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                  {metric.label}
                </div>
                <div className="font-mono text-[9px] tracking-[0.16em] text-slate-700">
                  {String(index + 1).padStart(2, "0")}
                </div>
              </div>
              <div className="mt-5 min-w-0">
                <div className="break-words text-xl font-semibold leading-tight tracking-[-0.025em] text-cyan-300 sm:text-2xl">
                  {metric.value}
                </div>
                <div className="mt-1 text-sm leading-5 text-slate-400">
                  {metric.suffix.trim()}
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Capabilities Grid */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {CAPABILITIES.map((capability, index) => {
            const Icon = capability.icon;
            return (
              <motion.div
                key={capability.title}
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.5, delay: index * 0.05 }}
                whileHover={{ y: -5, transition: { duration: 0.2 } }}
                className="group relative rounded-3xl border border-slate-800 bg-slate-900/40 p-6 hover:border-cyan-500/30 hover:bg-slate-900/60 transition-all duration-300"
              >
                {/* Icon */}
                <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center mb-4 group-hover:bg-cyan-500/20 transition-colors">
                  <Icon className="w-6 h-6 text-cyan-400" />
                </div>

                {/* Content */}
                <h3 className="text-lg font-bold text-white mb-2 group-hover:text-cyan-400 transition-colors">
                  {capability.title}
                </h3>
                <p className="text-sm text-slate-500 mb-4 leading-relaxed group-hover:text-slate-400 transition-colors">
                  {capability.description}
                </p>

                {/* Tag */}
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800/50 border border-slate-700 text-[10px] text-slate-400 group-hover:border-cyan-500/30 group-hover:text-cyan-400/80 transition-colors">
                  <span className="w-1 h-1 rounded-full bg-cyan-500/60" />
                  {capability.tag}
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Comparison */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mt-16 rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900/50 to-slate-900/30 p-8"
        >
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <span className="w-8 h-px bg-slate-500/40" />
                Basic Search
              </h3>
              <ul className="space-y-3 text-slate-400">
                {[
                  "Finds documents matching keywords",
                  "Returns isolated facts",
                  "Static relevance scoring",
                  "Same results every time",
                  "No understanding of relationships",
                ].map((item) => (
                  <li key={item} className="flex gap-3 text-sm">
                    <span className="text-slate-600 shrink-0">—</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <span className="w-8 h-px bg-cyan-500/40" />
                FAIM Cortex
              </h3>
              <ul className="space-y-3 text-slate-400">
                {[
                  "Follows chains of evidence across documents",
                  "Synthesizes unified answers with citations",
                  "Confidence adapts from user feedback",
                  "Improves with every interaction",
                  "Understands causality and temporal relationships",
                ].map((item) => (
                  <li key={item} className="flex gap-3 text-sm">
                    <span className="text-cyan-500 shrink-0">✓</span>
                    <span className="text-slate-300">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </motion.div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="mt-12 text-center"
        >
          <p className="text-slate-500 mb-4">
            Enterprise-ready • Deterministic & auditable • Self-improving •
            Production hardened
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            {[
              "Deep reasoning",
              "Cross-document synthesis",
              "Continuous learning",
              "Temporal analysis",
              "Quality monitoring",
              "Full explainability",
            ].map((tag) => (
              <span
                key={tag}
                className="px-3 py-1 rounded-full bg-slate-800/50 border border-slate-700 text-xs text-slate-400"
              >
                {tag}
              </span>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
