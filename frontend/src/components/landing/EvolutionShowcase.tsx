"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";

const EVOLUTION_PHASES = [
  {
    id: "diagnose",
    title: "Diagnose",
    subtitle: "Fractal diagnostics computed",
    color: "cyan",
    metrics: [
      { label: "D\u0302 (Fractal Dim)", value: "2.34", status: "normal" },
      { label: "H\u0302 (Entropy)", value: "0.67", status: "normal" },
      { label: "\u039B\u0302 (Pressure)", value: "0.72", status: "high" },
      { label: "Redundancy R", value: "0.54", status: "high" },
      { label: "Novelty N", value: "0.31", status: "normal" },
      { label: "Energy E", value: "1.41", status: "normal" },
    ],
    description: "Engine reads the graph's vital signs. High \u039B (0.72) and high redundancy (0.54) signal: this graph needs to evolve.",
  },
  {
    id: "adapt",
    title: "Adapt Threshold",
    subtitle: "Merge threshold lowered",
    color: "amber",
    metrics: [
      { label: "Base Threshold", value: "0.95", status: "normal" },
      { label: "R > 0.5?", value: "Yes", status: "high" },
      { label: "Adapted Threshold", value: "0.88", status: "active" },
      { label: "Prune Policy", value: "aggressive", status: "active" },
    ],
    description: "High redundancy (R=0.54) triggers aggressive mode. Merge threshold drops from 0.95 to 0.88 \u2014 more pairs become merge candidates.",
  },
  {
    id: "merge",
    title: "Merge",
    subtitle: "Near-duplicates merged",
    color: "purple",
    metrics: [
      { label: "Candidates Found", value: "12", status: "normal" },
      { label: "Merged Pairs", value: "5", status: "active" },
      { label: "Winner Selection", value: "SHA-256", status: "normal" },
      { label: "Nodes Removed", value: "5", status: "high" },
    ],
    description: "12 pairs above threshold. 5 merges executed. Each winner selected by lexicographic SHA-256 hash comparison \u2014 deterministic, provable.",
  },
  {
    id: "prune",
    title: "Prune",
    subtitle: "Dead nodes removed",
    color: "rose",
    metrics: [
      { label: "Candidates", value: "8", status: "normal" },
      { label: "Old + Low Touch", value: "3", status: "active" },
      { label: "Redundant Neighbors", value: "Yes", status: "normal" },
      { label: "Nodes Pruned", value: "3", status: "high" },
    ],
    description: "3 nodes are old, rarely accessed, and have highly similar neighbors. Safe to prune \u2014 no information lost, graph gets leaner.",
  },
  {
    id: "invent",
    title: "Self-Invent",
    subtitle: "Macro nodes created",
    color: "emerald",
    metrics: [
      { label: "Co-Activation Patterns", value: "4", status: "normal" },
      { label: "\u039B >= 0.3?", value: "Yes (0.72)", status: "active" },
      { label: "Macro Nodes Created", value: "2", status: "active" },
      { label: "Redundancy Reduced", value: "12%", status: "normal" },
    ],
    description: "4 node groups repeatedly co-activate across documents. 2 qualify for macro-node invention. New level-2 nodes created as semantic summaries. The graph just invented its own concepts.",
  },
  {
    id: "verify",
    title: "Re-Verify",
    subtitle: "All 8 invariants pass",
    color: "blue",
    metrics: [
      { label: "Inheritance \u2211=1", value: "\u2713", status: "pass" },
      { label: "Boundedness", value: "\u2713", status: "pass" },
      { label: "No Orphan Edges", value: "\u2713", status: "pass" },
      { label: "Energy \u2264 2.0", value: "\u2713 (1.38)", status: "pass" },
    ],
    description: "After all mutations, every invariant is re-checked. If any fails, the evolution is rejected. Graph version bumped. New graph_hash computed.",
  },
];

const colorMap: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  cyan: { bg: "bg-cyan-500/10", text: "text-cyan-400", border: "border-cyan-500/30", dot: "bg-cyan-400" },
  amber: { bg: "bg-amber-500/10", text: "text-amber-400", border: "border-amber-500/30", dot: "bg-amber-400" },
  purple: { bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/30", dot: "bg-purple-400" },
  rose: { bg: "bg-rose-500/10", text: "text-rose-400", border: "border-rose-500/30", dot: "bg-rose-400" },
  emerald: { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/30", dot: "bg-emerald-400" },
  blue: { bg: "bg-blue-500/10", text: "text-blue-400", border: "border-blue-500/30", dot: "bg-blue-400" },
};

const statusColors: Record<string, string> = {
  normal: "text-slate-400",
  high: "text-amber-400",
  active: "text-cyan-400",
  pass: "text-emerald-400",
};

export default function EvolutionShowcase() {
  const [activePhase, setActivePhase] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);

  useEffect(() => {
    if (!isPlaying) return;
    const timer = setInterval(() => {
      setActivePhase((prev) => (prev + 1) % EVOLUTION_PHASES.length);
    }, 3500);
    return () => clearInterval(timer);
  }, [isPlaying]);

  const phase = EVOLUTION_PHASES[activePhase];
  const c = colorMap[phase.color];

  return (
    <section id="evolution" className="py-28 px-4 bg-gradient-to-b from-[#070a18] to-slate-950 relative overflow-hidden">
      <div className="absolute inset-0 faim-grid" />

      <div className="max-w-6xl mx-auto relative">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-emerald-400 text-sm font-medium tracking-wider uppercase">
            Self-Evolution & Self-Invention
          </span>
          <h2 className="mt-4 text-4xl md:text-5xl font-bold text-white">
            The Graph That{" "}
            <span className="bg-gradient-to-r from-emerald-400 via-cyan-400 to-purple-400 bg-clip-text text-transparent">
              Thinks For Itself
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto">
            No human intervention. The engine monitors its own fractal diagnostics,
            adapts thresholds, merges redundancy, prunes dead weight, and invents new concepts.
          </p>
        </motion.div>

        {/* Phase Timeline */}
        <div className="flex items-center justify-center gap-2 mb-10 flex-wrap">
          {EVOLUTION_PHASES.map((p, i) => {
            const pc = colorMap[p.color];
            const isActive = i === activePhase;
            return (
              <button
                key={p.id}
                onClick={() => { setActivePhase(i); setIsPlaying(false); }}
                className={`flex items-center gap-2 px-4 py-2 rounded-full border text-xs font-medium transition-all duration-300 ${
                  isActive
                    ? `${pc.border} ${pc.bg} ${pc.text}`
                    : "border-slate-800/50 text-slate-500 hover:border-slate-700"
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${isActive ? pc.dot : "bg-slate-600"} ${
                  isActive ? "animate-pulse" : ""
                }`} />
                {p.title}
              </button>
            );
          })}

          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="ml-2 p-2 rounded-full border border-slate-800/50 text-slate-500 hover:text-white hover:border-slate-700 transition-all"
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10 9v6m4-6v6" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            )}
          </button>
        </div>

        {/* Active Phase Detail */}
        <AnimatePresence mode="wait">
          <motion.div
            key={phase.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.35 }}
            className="grid lg:grid-cols-2 gap-8"
          >
            {/* Left: Description */}
            <div className={`p-8 rounded-2xl border ${c.border} bg-gradient-to-b from-slate-900/60 to-slate-900/20`}>
              <div className="flex items-center gap-3 mb-4">
                <span className={`inline-flex items-center justify-center w-10 h-10 rounded-xl ${c.bg}`}>
                  <span className={`text-lg font-bold font-mono ${c.text}`}>
                    {String(activePhase + 1).padStart(2, "0")}
                  </span>
                </span>
                <div>
                  <h3 className="text-xl font-bold text-white">{phase.title}</h3>
                  <p className={`text-xs ${c.text}`}>{phase.subtitle}</p>
                </div>
              </div>

              <p className="text-slate-300 text-sm leading-relaxed mb-6">
                {phase.description}
              </p>

              {/* Visual: Evolution flow */}
              {phase.id === "invent" && (
                <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
                  <p className="text-[10px] text-slate-600 font-mono uppercase tracking-wider mb-3">Macro Node Structure</p>
                  <div className="text-xs font-mono text-slate-400 space-y-1">
                    <p>{`{`}</p>
                    <p className="pl-4"><span className="text-purple-400">&quot;kind&quot;</span>: <span className="text-emerald-400">&quot;macro&quot;</span>,</p>
                    <p className="pl-4"><span className="text-purple-400">&quot;level&quot;</span>: <span className="text-cyan-400">2</span>,</p>
                    <p className="pl-4"><span className="text-purple-400">&quot;v_native&quot;</span>: <span className="text-slate-500">normalized_mean(members)</span>,</p>
                    <p className="pl-4"><span className="text-purple-400">&quot;members&quot;</span>: <span className="text-cyan-400">5</span>,</p>
                    <p className="pl-4"><span className="text-purple-400">&quot;\u039B_at_invention&quot;</span>: <span className="text-amber-400">0.72</span>,</p>
                    <p className="pl-4"><span className="text-purple-400">&quot;redundancy_reduced&quot;</span>: <span className="text-emerald-400">0.12</span></p>
                    <p>{`}`}</p>
                  </div>
                </div>
              )}

              {phase.id === "verify" && (
                <div className="p-4 rounded-lg bg-slate-950 border border-emerald-500/20">
                  <p className="text-xs font-mono text-emerald-400 mb-2">Evolution Result</p>
                  <div className="text-xs font-mono text-slate-400 space-y-1">
                    <p>merges: <span className="text-white">5</span> | prunes: <span className="text-white">3</span> | inventions: <span className="text-white">2</span></p>
                    <p>graph_version: <span className="text-white">43</span> \u2192 <span className="text-cyan-400">44</span></p>
                    <p>graph_hash: <span className="text-cyan-400">sha256:b7f2e...</span></p>
                    <p>invariants: <span className="text-emerald-400">8/8 passed</span></p>
                  </div>
                </div>
              )}
            </div>

            {/* Right: Metrics */}
            <div className="p-8 rounded-2xl border border-slate-800 bg-slate-900/30">
              <h4 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-6">
                Live Metrics
              </h4>

              <div className="space-y-4">
                {phase.metrics.map((metric, i) => (
                  <motion.div
                    key={metric.label}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: i * 0.05 }}
                    className="flex items-center justify-between py-3 border-b border-slate-800/50 last:border-0"
                  >
                    <span className="text-slate-400 text-sm">{metric.label}</span>
                    <span className={`font-mono text-sm font-medium ${statusColors[metric.status]}`}>
                      {metric.value}
                    </span>
                  </motion.div>
                ))}
              </div>

              {/* Invention thresholds */}
              <div className="mt-8 p-4 rounded-lg bg-slate-950 border border-slate-800">
                <p className="text-[10px] text-slate-600 font-mono uppercase tracking-wider mb-2">Invention Thresholds</p>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div>
                    <p className="text-white font-mono text-sm font-bold">0.3</p>
                    <p className="text-slate-600 text-[10px]">\u039B threshold</p>
                  </div>
                  <div>
                    <p className="text-white font-mono text-sm font-bold">3x</p>
                    <p className="text-slate-600 text-[10px]">min co-activation</p>
                  </div>
                  <div>
                    <p className="text-white font-mono text-sm font-bold">1%</p>
                    <p className="text-slate-600 text-[10px]">min reduction</p>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}
