"use client";

import { motion } from "framer-motion";

const PHASES = [
  {
    tag: "NOW",
    title: "Deterministic Core",
    desc: "Stage-4.1.1 production core with Hybrid Physics Recall, VP-Tree shortlisting, and Extractive Synthesis.",
    status: "Live",
    color: "cyan",
  },
  {
    tag: "Q3 2026",
    title: "Multimodal Perception",
    desc: "Graph-native reasoning for figures, tables, and spatial evidence across large-scale PDF corpora.",
    status: "Developing",
    color: "purple",
  },
  {
    tag: "Q4 2026",
    title: "Decentralized Sync",
    desc: "Multi-graph synchronization and evolution across edge nodes with zero-trust inheritance.",
    status: "Researching",
    color: "rose",
  },
];

export default function Roadmap() {
  return (
    <section className="py-28 px-4 bg-slate-950 relative border-t border-slate-900">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold text-white mb-2">The Roadmap.</h2>
          <p className="text-slate-500 text-sm">
            Building the most robust knowledge engine on the planet.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {PHASES.map((phase, i) => (
            <motion.div
              key={phase.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="relative p-8 rounded-2xl border border-slate-800 bg-slate-900/10 group overflow-hidden"
            >
              {/* Vertical line indicator */}
              <div
                className={`absolute top-0 left-0 w-1 h-full bg-${phase.color}-500/30 group-hover:bg-${phase.color}-500 transition-colors`}
              />

              <span
                className={`text-[10px] font-bold text-${phase.color}-400 uppercase tracking-widest block mb-4`}
              >
                {phase.tag} — {phase.status}
              </span>
              <h3 className="text-white font-bold mb-2">{phase.title}</h3>
              <p className="text-slate-500 text-xs leading-relaxed">
                {phase.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
