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
    formula:
      "Correlation-dimension via pairwise cosine across 8 \u03B5 thresholds",
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
    meaning:
      "Stability bound \u2014 if E > 2.0, system is mathematically unbounded",
    source: "fractal_physics.py",
  },
];

function AnimatedCounter({
  value,
  suffix = "",
}: {
  value: number;
  suffix?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true });

  return (
    <span ref={ref} className="tabular-nums">
      <motion.span
        initial={{ opacity: 0 }}
        animate={isInView ? { opacity: 1 } : {}}
        transition={{ duration: 0.6 }}
      >
        {isInView ? value : 0}
        {suffix}
      </motion.span>
    </span>
  );
}

export default function MathProof() {
  return (
    <section
      id="proof"
      className="py-28 px-4 bg-slate-950 relative overflow-hidden"
    >
      {/* Structural Geometry Background */}
      <div className="absolute inset-0 faim-grid opacity-20" />
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none overflow-hidden opacity-30">
        <svg className="absolute top-[-10%] right-[-10%] w-[300px] sm:w-[600px] h-[300px] sm:h-[600px] text-cyan-500/10">
          <motion.path
            d="M 150, 150 m -125, 0 a 125,125 0 1,0 250,0 a 125,125 0 1,0 -250,0"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.5"
            strokeDasharray="4 4"
            className="sm:hidden"
            animate={{ rotate: 360 }}
            transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
          />
          <motion.path
            d="M 300, 300 m -250, 0 a 250,250 0 1,0 500,0 a 250,250 0 1,0 -500,0"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.5"
            strokeDasharray="4 4"
            className="hidden sm:block"
            animate={{ rotate: 360 }}
            transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
          />
        </svg>
      </div>

      <div className="max-w-6xl mx-auto relative">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="text-center mb-20"
        >
          <motion.span
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            className="text-cyan-400 text-[10px] font-bold tracking-[0.3em] uppercase mb-4 block"
          >
            Mathematical Foundation
          </motion.span>
          <h2 className="text-3xl md:text-5xl font-bold text-white tracking-tight leading-tight">
            Invariant-Checked. <br className="hidden md:block" />
            <span className="bg-gradient-to-r from-cyan-400 to-emerald-400 bg-clip-text text-transparent">
              Every Engine Cycle.
            </span>
          </h2>
          <p className="mt-6 text-slate-400 max-w-2xl mx-auto text-lg leading-relaxed">
            8 mathematical invariants are checked on write operations. These
            are core consistency rules, not a universal guarantee of answer
            quality.
          </p>
        </motion.div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-20">
          {INVARIANTS.map((inv, i) => (
            <motion.div
              key={inv.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.05 }}
              whileHover={{ y: -5, transition: { duration: 0.2 } }}
              className="relative group p-6 rounded-2xl border border-slate-800 bg-slate-900/40 hover:border-slate-700 transition-all duration-300"
            >
              <div
                className={`w-12 h-12 rounded-xl ${inv.bg} flex items-center justify-center mb-4 relative overflow-hidden`}
              >
                <motion.div
                  className="absolute inset-0 bg-white/5"
                  animate={{ scale: [1, 1.2, 1], opacity: [0.1, 0.2, 0.1] }}
                  transition={{ duration: 3, repeat: Infinity }}
                />
                <span
                  className={`text-xl font-bold font-mono ${inv.color} relative z-10`}
                >
                  {inv.symbol}
                </span>
              </div>
              <h4 className="text-white text-sm font-bold mb-1 tracking-tight">
                {inv.name}
              </h4>
              <p className="text-slate-500 text-[10px] font-mono group-hover:text-slate-400 transition-colors">
                {inv.rule}
              </p>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="mb-12"
        >
          <div className="flex items-center gap-4 mb-12">
            <div className="h-px flex-1 bg-gradient-to-r from-transparent to-slate-800" />
            <h3 className="text-2xl font-bold text-white whitespace-nowrap">
              Fractal Physics{" "}
              <span className="text-slate-500 font-normal">
                &mdash; Measurable Reality
              </span>
            </h3>
            <div className="h-px flex-1 bg-gradient-to-l from-transparent to-slate-800" />
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {PHYSICS_METRICS.map((metric, i) => (
              <motion.div
                key={metric.name}
                initial={{ opacity: 0, x: i % 2 === 0 ? -20 : 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="p-8 rounded-3xl border border-slate-800 bg-slate-900/20 hover:border-slate-700 transition-all group relative overflow-hidden"
              >
                <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:opacity-[0.08] transition-opacity">
                  <span className="text-6xl font-bold text-white font-mono">
                    {i + 1}
                  </span>
                </div>
                <h4 className="text-white font-bold mb-3">{metric.name}</h4>
                <div className="px-3 py-1.5 rounded-lg bg-slate-950/80 border border-slate-800 inline-block mb-4">
                  <code className="text-cyan-400 text-xs font-mono">
                    {metric.formula}
                  </code>
                </div>
                <p className="text-slate-400 text-sm leading-relaxed mb-4">
                  {metric.meaning}
                </p>
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  <p className="text-slate-600 text-[10px] font-mono tracking-widest uppercase">
                    Source: {metric.source}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Golden Ratio Geometric Visualization */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="mt-16 p-6 sm:p-10 rounded-[1.5rem] sm:rounded-[2.5rem] border border-amber-500/20 bg-gradient-to-br from-amber-500/[0.05] via-slate-950 to-transparent relative overflow-hidden group"
        >
          <div className="absolute -right-20 -top-20 w-64 h-64 border border-amber-500/10 rounded-full animate-pulse pointer-events-none" />

          <div className="flex flex-col md:flex-row items-center gap-12 relative z-10">
            <div className="flex-1 text-center md:text-left">
              <span className="text-amber-500/80 text-[10px] font-bold uppercase tracking-[0.4em] mb-4 block">
                Stability Equilibrium
              </span>
              <p className="text-4xl sm:text-5xl md:text-7xl font-bold text-amber-400 font-mono mb-6 tracking-tighter break-words">
                s = 1/&phi; &approx; 0.618
              </p>
              <p className="text-slate-400 text-base max-w-xl leading-relaxed">
                The golden ratio reciprocal isn&apos;t decoration. It&apos;s the
                fixed point of{" "}
                <code className="text-amber-200/50">s = 1/(1+s)</code>,
                supporting self-similar scaling across hierarchy levels. The
                configured energy bound is checked as an engine invariant.
              </p>
            </div>

            <div className="w-48 h-48 md:w-64 md:h-64 relative shrink-0">
              {/* Simplified SVG Spiral representing phi */}
              <svg
                viewBox="0 0 100 100"
                className="w-full h-full text-amber-500/20"
              >
                <motion.path
                  d="M 50,50 m -40,0 a 40,40 0 1,0 80,0 a 40,40 0 1,0 -80,0"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="0.5"
                  animate={{ rotate: 360 }}
                  transition={{
                    duration: 10,
                    repeat: Infinity,
                    ease: "linear",
                  }}
                />
                <motion.path
                  d="M 50,50 m -25,0 a 25,25 0 1,0 50,0 a 25,25 0 1,0 -50,0"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1"
                  animate={{ rotate: -360 }}
                  transition={{
                    duration: 15,
                    repeat: Infinity,
                    ease: "linear",
                  }}
                />
                <circle
                  cx="50"
                  cy="50"
                  r="2"
                  fill="currentColor"
                  className="text-amber-500/50"
                />
              </svg>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
