"use client";

import { motion, useInView } from "framer-motion";
import { useRef } from "react";

const INVARIANTS = [
  {
    symbol: "\u2211",
    name: "Inheritance Sum",
    rule: "Fractions = 1.0 \u00B1 10\u207B\u2079",
    color: "text-cyan-400",
    bg: "bg-cyan-500/10",
  },
  {
    symbol: "\u2200",
    name: "Boundedness",
    rule: "No NaN, No Inf, finite norms",
    color: "text-blue-400",
    bg: "bg-blue-500/10",
  },
  {
    symbol: "r",
    name: "Residual Range",
    rule: "0 \u2264 residual \u2264 1",
    color: "text-indigo-400",
    bg: "bg-indigo-500/10",
  },
  {
    symbol: "\u2205",
    name: "No Orphan Edges",
    rule: "All edges reference existing nodes",
    color: "text-purple-400",
    bg: "bg-purple-500/10",
  },
  {
    symbol: "D",
    name: "Fractal Dimension",
    rule: "0 \u2264 D\u0302 \u2264 10",
    color: "text-pink-400",
    bg: "bg-pink-500/10",
  },
  {
    symbol: "H",
    name: "Entropy",
    rule: "0 \u2264 H\u0302 \u2264 1",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
  },
  {
    symbol: "\u039B",
    name: "Evolution Pressure",
    rule: "0 \u2264 \u039B\u0302 \u2264 1",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
  },
  {
    symbol: "E",
    name: "Energy Bound",
    rule: "E \u2264 2.0 (golden ratio scaled)",
    color: "text-rose-400",
    bg: "bg-rose-500/10",
  },
];

const PHYSICS_METRICS = [
  {
    name: "Fractal Dimension (D\u0302)",
    formula: "Correlation-dimension via pairwise cosine across 8 \u03B5 thresholds",
    meaning: "How structurally complex is your knowledge graph",
    source: "fractal_physics.py",
  },
  {
    name: "Shannon Entropy (H\u0302)",
    formula: "Entropy of similarity histogram (20 bins over [-1, 1])",
    meaning: "How diverse is the information in your memory",
    source: "fractal_physics.py",
  },
  {
    name: "Evolution Pressure (\u039B\u0302)",
    formula: "0.50\u00B7N + 0.30\u00B7(1\u2212R) + 0.20\u00B7H",
    meaning: "Does the graph need to evolve right now",
    source: "fractal_physics.py",
  },
  {
    name: "Energy (E)",
    formula: "mean L2 norm \u00D7 s, where s = 1/\u03C6 \u2248 0.618",
    meaning: "Stability bound \u2014 if E > 2.0, system is mathematically unbounded",
    source: "fractal_physics.py",
  },
];

function AnimatedCounter({ value, suffix = "" }: { value: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true });

  return (
    <span ref={ref} className="tabular-nums">
      <motion.span
        initial={{ opacity: 0 }}
        animate={isInView ? { opacity: 1 } : {}}
        transition={{ duration: 0.6 }}
      >
        {isInView ? value : 0}{suffix}
      </motion.span>
    </span>
  );
}

export default function MathProof() {
  return (
    <section id="proof" className="py-28 px-4 bg-slate-950 relative overflow-hidden">
      <div className="absolute inset-0 faim-grid" />

      <div className="max-w-6xl mx-auto relative">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <span className="text-cyan-400 text-sm font-medium tracking-wider uppercase">
            Mathematical Foundation
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            Provably Correct.{" "}
            <span className="bg-gradient-to-r from-cyan-400 to-emerald-400 bg-clip-text text-transparent">
              Every Cycle.
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto text-lg">
            8 mathematical invariants verified on every write operation.
            Not &ldquo;best effort&rdquo; — mathematically enforced.
          </p>
        </motion.div>

        {/* 8 Invariants Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-20">
          {INVARIANTS.map((inv, i) => (
            <motion.div
              key={inv.name}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.06 }}
              className="relative group p-5 rounded-xl border border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/60 transition-all duration-300"
            >
              <div className={`w-10 h-10 rounded-lg ${inv.bg} flex items-center justify-center mb-3`}>
                <span className={`text-lg font-bold font-mono ${inv.color}`}>
                  {inv.symbol}
                </span>
              </div>
              <h4 className="text-white text-sm font-semibold mb-1">{inv.name}</h4>
              <p className="text-slate-500 text-xs font-mono">{inv.rule}</p>
            </motion.div>
          ))}
        </div>

        {/* Fractal Physics Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="mb-8"
        >
          <h3 className="text-2xl font-bold text-white text-center mb-12">
            Fractal Physics — The Graph Has a{" "}
            <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              Measurable Reality
            </span>
          </h3>

          <div className="grid md:grid-cols-2 gap-5">
            {PHYSICS_METRICS.map((metric, i) => (
              <motion.div
                key={metric.name}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="p-6 rounded-xl border border-slate-800 bg-slate-900/30 hover:border-slate-700 transition-all duration-300"
              >
                <h4 className="text-white font-semibold mb-2">{metric.name}</h4>
                <p className="text-cyan-400/80 text-xs font-mono mb-3">{metric.formula}</p>
                <p className="text-slate-400 text-sm">{metric.meaning}</p>
                <p className="text-slate-600 text-[10px] font-mono mt-3">
                  Source: {metric.source}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Golden Ratio Callout */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-12 p-8 rounded-2xl border border-amber-500/20 bg-gradient-to-b from-amber-500/[0.04] to-transparent text-center"
        >
          <p className="text-5xl font-bold text-amber-400/90 font-mono mb-3">
            s = 1/\u03C6 \u2248 0.618
          </p>
          <p className="text-slate-400 text-sm max-w-xl mx-auto leading-relaxed">
            The golden ratio reciprocal isn&apos;t decoration. It&apos;s the fixed point of{" "}
            <span className="text-white font-mono text-xs">s = 1/(1+s)</span>,
            guaranteeing self-similar scaling across hierarchy levels. Energy
            is bounded because the physics demands it.
          </p>
        </motion.div>
      </div>
    </section>
  );
}
