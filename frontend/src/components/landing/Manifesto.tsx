"use client";

import { motion } from "framer-motion";

const PILLARS = [
  {
    title: "Determinism is Mandatory",
    desc: "A query should not return different results because the index 'approximated' a neighbor. FAIM is built on VP-Trees and WAND for 100% stable, repeatable truth.",
    icon: "🎯",
  },
  {
    title: "Logic Over Vibes",
    desc: "Language is fuzzy; logic is not. FAIM prioritizes graph-native inheritance and categorical evidence over simple vector similarity 'vibes'.",
    icon: "⚖️",
  },
  {
    title: "Evidence-First Synthesis",
    desc: "We don't 'generate' answers; we synthesize them from extracted truth. Every response is grounded in spatial anchors and cited evidence blocks.",
    icon: "🔍",
  },
  {
    title: "Privacy by Design",
    desc: "Multi-tenancy isn't a feature; it's the core. Every node and edge is crypto-isolated via tenant_id scoping from the storage layer up.",
    icon: "🔐",
  },
];

export default function Manifesto() {
  return (
    <section className="py-28 px-4 bg-slate-950 relative">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-20"
        >
          <span className="text-cyan-400 text-sm font-medium tracking-widest uppercase">
            Our Convictions
          </span>
          <h2 className="mt-4 text-4xl font-bold text-white">
            The FAIM{" "}
            <span className="bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
              Manifesto.
            </span>
          </h2>
          <p className="mt-4 text-slate-400 max-w-2xl mx-auto">
            We are building the engine for teams who can&apos;t afford to guess. No
            hallucinations, no jitter, no context blindness.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-8">
          {PILLARS.map((pillar, i) => (
            <motion.div
              key={pillar.title}
              initial={{ opacity: 0, scale: 0.98 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.1 }}
              className="p-8 rounded-3xl border border-slate-800 bg-slate-900/10 hover:bg-slate-900/20 transition-all group"
            >
              <div className="text-3xl mb-4 group-hover:scale-110 transition-transform inline-block">
                {pillar.icon}
              </div>
              <h3 className="text-xl font-bold text-white mb-3">
                {pillar.title}
              </h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                {pillar.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
