"use client";

import { motion } from "framer-motion";

const SOURCES = ["Slack", "Drive", "Notion", "GitHub"];
const APPS = ["Your Dashboard", "Chatbot", "Legal App", "Search API"];

export default function IntegrationMap() {
  return (
    <section className="py-28 px-4 bg-slate-950 relative overflow-hidden">
      <div className="max-w-6xl mx-auto relative">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold text-white mb-4">
            Plugs into Your Ecosystem.
          </h2>
          <p className="text-slate-400 text-sm max-w-xl mx-auto">
            FAIM acts as the deterministic bridge between your raw data sources
            and your production AI applications.
          </p>
        </div>

        <div className="flex flex-col md:flex-row items-center justify-between gap-12 relative">
          {/* Connection Lines (Desktop) */}
          <div className="absolute top-1/2 left-0 w-full h-px bg-gradient-to-r from-transparent via-cyan-500/20 to-transparent hidden md:block" />

          {/* Left Side: Sources */}
          <div className="flex flex-wrap md:flex-col gap-4 z-10">
            {SOURCES.map((s, i) => (
              <motion.div
                key={s}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="px-4 py-2 rounded-full border border-slate-800 bg-slate-900/50 text-[10px] font-bold text-slate-400 uppercase tracking-widest whitespace-nowrap"
              >
                {s} Connector
              </motion.div>
            ))}
          </div>

          {/* Center: FAIM Core */}
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            whileInView={{ scale: 1, opacity: 1 }}
            viewport={{ once: true }}
            className="relative z-20 group"
          >
            <div className="absolute inset-0 bg-cyan-500/20 blur-3xl rounded-full group-hover:bg-cyan-500/30 transition-all" />
            <div className="relative w-32 h-32 md:w-48 md:h-48 rounded-full border-2 border-cyan-500/30 bg-slate-900 flex flex-col items-center justify-center text-center p-4">
              <span className="text-2xl md:text-4xl mb-1">🏗️</span>
              <span className="text-cyan-400 font-bold text-xs md:text-lg tracking-tighter uppercase">
                FAIM CORE
              </span>
              <span className="text-[8px] md:text-[10px] text-slate-500 font-mono mt-1">
                Deterministic Engine
              </span>
            </div>
          </motion.div>

          {/* Right Side: Apps */}
          <div className="flex flex-wrap md:flex-col gap-4 z-10 items-end">
            {APPS.map((a, i) => (
              <motion.div
                key={a}
                initial={{ opacity: 0, x: 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="px-4 py-2 rounded-full border border-cyan-500/20 bg-cyan-500/5 text-[10px] font-bold text-cyan-400 uppercase tracking-widest whitespace-nowrap"
              >
                {a}
              </motion.div>
            ))}
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.6 }}
          className="mt-20 text-center"
        >
          <p className="text-slate-600 text-[10px] font-mono uppercase tracking-[0.3em]">
            Memory Truth → Retrieval Logic → Answer Synthesis
          </p>
        </motion.div>
      </div>
    </section>
  );
}
